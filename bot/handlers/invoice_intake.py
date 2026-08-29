"""Photo -> OCR extraction -> property/cost-type confirmation -> saved cost_entries
row. The file is always persisted to disk before any API call so a crash or API
failure never loses the scan (docs in the module plan). media_group albums
(multi-page invoices) are buffered briefly so exactly one extraction call covers
the whole invoice, per CLAUDE.md's "one extraction call per invoice"."""

from __future__ import annotations

import asyncio
import uuid
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

from bot.context import get_conn, get_settings
from bot.ocr.extract import ExtractionResult, extract_invoice
from config.cost_types import all_cost_type_choices, is_apportionable_code
from db.repositories import invoice_repo, property_repo

CHOOSE_PROPERTY, CHOOSE_COST_TYPE, CONFIRM, EDIT_AMOUNT = range(4)

_MEDIA_GROUP_DEBOUNCE_SECONDS = 1.5


async def on_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    settings = get_settings(context)
    photo = update.message.photo[-1]  # largest size
    file = await photo.get_file()

    incoming_dir = settings.invoices_dir / "incoming"
    incoming_dir.mkdir(parents=True, exist_ok=True)
    file_path = incoming_dir / f"{uuid.uuid4()}.jpg"
    await file.download_to_drive(str(file_path))

    media_group_id = update.message.media_group_id
    if media_group_id is None:
        return await _process_invoice(update, context, [file_path])

    # Buffer pages sharing a media_group_id; process once, after a short debounce.
    key = f"media_group:{media_group_id}"
    pages = context.chat_data.setdefault(key, [])
    pages.append(file_path)

    if len(pages) == 1:
        await asyncio.sleep(_MEDIA_GROUP_DEBOUNCE_SECONDS)
        collected = context.chat_data.pop(key, pages)
        return await _process_invoice(update, context, collected)
    return ConversationHandler.END  # this update's pages already queued by the first handler


async def _process_invoice(
    update: Update, context: ContextTypes.DEFAULT_TYPE, file_paths: list
) -> int:
    settings = get_settings(context)
    if not settings.anthropic_api_key:
        await update.message.reply_text(
            "ANTHROPIC_API_KEY not configured -- can't extract invoice data. "
            "Ask the landlord to set it up, or use the CLI to enter this invoice manually."
        )
        return ConversationHandler.END

    status_msg = await update.message.reply_text("Reading invoice...")
    try:
        result = extract_invoice(
            api_key=settings.anthropic_api_key,
            image_bytes_list=[p.read_bytes() for p in file_paths],
        )
    # Any failure here (timeout, API error, bad response shape) should degrade to
    # Retry/Enter-manually, not crash the bot -- a broad catch is deliberate at this
    # external-API boundary.
    except Exception:  # noqa: BLE001
        keyboard = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton("Retry", callback_data="ocr_retry"),
                    InlineKeyboardButton("Enter manually", callback_data="ocr_manual"),
                ]
            ]
        )
        context.user_data["invoice"] = {"file_paths": [str(p) for p in file_paths]}
        await status_msg.edit_text("Extraction failed.", reply_markup=keyboard)
        return CONFIRM

    context.user_data["invoice"] = {
        "file_paths": [str(p) for p in file_paths],
        "vendor": result.vendor,
        "amount": str(result.amount) if result.amount is not None else None,
        "invoice_date": result.invoice_date.isoformat() if result.invoice_date else None,
        "suggested_cost_type": result.suggested_cost_type,
        "likely_non_apportionable": result.likely_non_apportionable,
        "confidence": result.confidence,
        "raw_response_json": result.raw_response_json,
    }

    summary = _format_extraction(result)
    await status_msg.edit_text(f"{summary}\n\nWhich property?")
    return await _show_property_choices(update, context)


def _format_extraction(result: ExtractionResult) -> str:
    lines = ["Extracted:"]
    lines.append(f"  Vendor: {result.vendor or '(unclear)'}")
    lines.append(f"  Amount: {result.amount if result.amount is not None else '(unclear)'}")
    lines.append(
        f"  Date: {result.invoice_date.isoformat() if result.invoice_date else '(unclear)'}"
    )
    lines.append(f"  Confidence: {result.confidence}")
    if result.likely_non_apportionable:
        lines.append("  Note: looks like a repair/admin cost, likely not apportionable.")
    return "\n".join(lines)


async def _show_property_choices(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    conn = get_conn(context)
    try:
        properties = property_repo.list_all(conn)
    finally:
        conn.close()

    if not properties:
        await update.effective_message.reply_text(
            "No properties recorded yet -- add one via the CLI first."
        )
        return ConversationHandler.END

    buttons = [[InlineKeyboardButton(p.label, callback_data=f"invprop:{p.id}")] for p in properties]
    await update.effective_message.reply_text(
        "Select property:", reply_markup=InlineKeyboardMarkup(buttons)
    )
    return CHOOSE_PROPERTY


async def receive_property(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    property_id = int(query.data.split(":")[1])
    context.user_data["invoice"]["property_id"] = property_id

    suggested = context.user_data["invoice"].get("suggested_cost_type")
    likely_non_apportionable = context.user_data["invoice"].get("likely_non_apportionable")

    buttons = []
    for code, label, apportionable in all_cost_type_choices():
        marker = ""
        if code == suggested or (likely_non_apportionable and not apportionable):
            marker = " *"
        buttons.append([InlineKeyboardButton(f"{label}{marker}", callback_data=f"invcost:{code}")])

    await query.edit_message_text(
        "Select cost type (* = suggested):", reply_markup=InlineKeyboardMarkup(buttons)
    )
    return CHOOSE_COST_TYPE


async def receive_cost_type(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    cost_type = int(query.data.split(":")[1])
    context.user_data["invoice"]["cost_type"] = cost_type
    return await _show_confirmation(query, context)


async def _show_confirmation(query, context: ContextTypes.DEFAULT_TYPE) -> int:
    inv = context.user_data["invoice"]
    kind = "apportionable" if is_apportionable_code(inv["cost_type"]) else "NON-apportionable"
    lines = [
        "Confirm:",
        f"  Vendor: {inv.get('vendor') or '(none)'}",
        f"  Amount: {inv.get('amount') or '(missing)'}",
        f"  Date: {inv.get('invoice_date') or '(missing)'}",
        f"  Cost type: {inv['cost_type']} ({kind})",
    ]
    buttons = [
        [
            InlineKeyboardButton("Confirm", callback_data="inv_confirm"),
            InlineKeyboardButton("Edit amount", callback_data="inv_edit_amount"),
            InlineKeyboardButton("Cancel", callback_data="inv_cancel"),
        ]
    ]
    await query.edit_message_text("\n".join(lines), reply_markup=InlineKeyboardMarkup(buttons))
    return CONFIRM


async def on_confirm_action(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    if query.data == "inv_cancel":
        context.user_data.pop("invoice", None)
        await query.edit_message_text("Cancelled.")
        return ConversationHandler.END

    if query.data == "inv_edit_amount":
        await query.edit_message_text("Send the correct amount (e.g. 812.21):")
        return EDIT_AMOUNT

    if query.data == "ocr_manual":
        await query.edit_message_text(
            "Manual entry: use `python -m scripts.cli add-invoice` for now."
        )
        context.user_data.pop("invoice", None)
        return ConversationHandler.END

    if query.data == "ocr_retry":
        inv = context.user_data.get("invoice", {})
        file_paths = [Path(p) for p in inv.get("file_paths", [])]
        if not file_paths:
            await query.edit_message_text("Nothing to retry.")
            return ConversationHandler.END
        return await _process_invoice(update, context, file_paths)

    if query.data == "inv_confirm":
        return await _save_invoice(query, context)

    return CONFIRM


async def receive_amount_edit(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        amount = Decimal(update.message.text.strip().replace(",", "."))
    except InvalidOperation:
        await update.message.reply_text("Invalid amount. Example: 812.21")
        return EDIT_AMOUNT

    context.user_data["invoice"]["amount"] = str(amount)
    lines = [
        "Confirm:",
        f"  Amount: {amount}",
        f"  Cost type: {context.user_data['invoice']['cost_type']}",
    ]
    buttons = [
        [
            InlineKeyboardButton("Confirm", callback_data="inv_confirm"),
            InlineKeyboardButton("Cancel", callback_data="inv_cancel"),
        ]
    ]
    await update.message.reply_text("\n".join(lines), reply_markup=InlineKeyboardMarkup(buttons))
    return CONFIRM


async def _save_invoice(query, context: ContextTypes.DEFAULT_TYPE) -> int:
    inv = context.user_data["invoice"]
    settings = get_settings(context)

    if not inv.get("amount"):
        await query.edit_message_text("Amount is missing -- can't save. Use Edit amount first.")
        return CONFIRM

    property_id = inv["property_id"]
    billing_year = (
        date.fromisoformat(inv["invoice_date"]).year
        if inv.get("invoice_date")
        else date.today().year
    )

    final_dir = settings.invoices_dir / str(property_id) / str(billing_year)
    final_dir.mkdir(parents=True, exist_ok=True)
    saved_paths = []
    for raw_path in inv["file_paths"]:
        src = Path(raw_path)
        dst = final_dir / src.name
        if src.exists():
            src.rename(dst)
        saved_paths.append(str(dst))

    conn = get_conn(context)
    try:
        invoice_repo.create(
            conn,
            property_id=property_id,
            cost_type_code=inv["cost_type"],
            billing_year=billing_year,
            amount=Decimal(inv["amount"]),
            vendor_name=inv.get("vendor"),
            invoice_date=(
                date.fromisoformat(inv["invoice_date"]) if inv.get("invoice_date") else None
            ),
            description=None,
            source_file_path=saved_paths[0] if saved_paths else None,
            entry_method="telegram_ocr",
            ocr_confidence={"high": 1.0, "medium": 0.6, "low": 0.3}.get(inv.get("confidence"), 0.3),
            ocr_raw_response=inv.get("raw_response_json"),
            entered_by=str(query.from_user.id),
        )
        totals = invoice_repo.totals_by_cost_type(conn, property_id, billing_year)
    finally:
        conn.close()

    running_total = totals.get(inv["cost_type"], Decimal(0))
    await query.edit_message_text(
        f"Saved. Running total for this cost type in {billing_year}: {running_total:.2f} EUR"
    )
    context.user_data.pop("invoice", None)
    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data.pop("invoice", None)
    await update.message.reply_text("Cancelled.")
    return ConversationHandler.END


invoice_conversation = ConversationHandler(
    entry_points=[MessageHandler(filters.PHOTO, on_photo)],
    states={
        CHOOSE_PROPERTY: [CallbackQueryHandler(receive_property, pattern=r"^invprop:\d+$")],
        CHOOSE_COST_TYPE: [CallbackQueryHandler(receive_cost_type, pattern=r"^invcost:\d+$")],
        CONFIRM: [
            CallbackQueryHandler(
                on_confirm_action,
                pattern=r"^(inv_confirm|inv_edit_amount|inv_cancel|ocr_retry|ocr_manual)$",
            )
        ],
        EDIT_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_amount_edit)],
    },
    fallbacks=[CommandHandler("cancel", cancel)],
)
