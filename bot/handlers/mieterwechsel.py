"""Mieterwechsel (tenant change): closes out the outgoing tenant's contract and
opens a new one for the same unit. Contracts are never mutated to swap tenants --
always closed-then-replaced, so the property's full occupancy history stays intact
(this matters for vacancy handling and Belegeinsicht, see calc_engine/vacancy.py)."""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal, InvalidOperation

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    CallbackQueryHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

from bot.context import get_conn
from db.repositories import contract_repo, property_repo, tenant_repo
from models.tenant import Contract, Tenant

END_DATE, NEW_TENANT, START_DATE, ADVANCE, CONFIRM = range(5)


async def start_wechsel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    contract_id = int(query.data.split(":")[1])

    conn = get_conn(context)
    try:
        contract = contract_repo.get(conn, contract_id)
        if contract is None:
            await query.edit_message_text("Contract not found.")
            return ConversationHandler.END
        unit = property_repo.get_unit(conn, contract.unit_id)
    finally:
        conn.close()

    context.user_data["wechsel"] = {"old_contract_id": contract_id, "unit_id": unit.id}
    await query.edit_message_text(
        f"Mieterwechsel for {unit.label}.\n" "Move-out date of the current tenant? (YYYY-MM-DD)"
    )
    return END_DATE


async def receive_end_date(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        end_date = date.fromisoformat(update.message.text.strip())
    except ValueError:
        await update.message.reply_text("Invalid date. Format: YYYY-MM-DD")
        return END_DATE

    context.user_data["wechsel"]["end_date"] = end_date.isoformat()
    await update.message.reply_text(
        "New tenant details, one line, semicolon-separated:\n"
        "FirstName;LastName;Street;PostalCode;City\n\n"
        "Or send /cancel to abort."
    )
    return NEW_TENANT


async def receive_new_tenant(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    parts = [p.strip() for p in update.message.text.split(";")]
    if len(parts) != 5:
        await update.message.reply_text(
            "Expected 5 semicolon-separated fields: FirstName;LastName;Street;PostalCode;City"
        )
        return NEW_TENANT

    first_name, last_name, street, postal_code, city = parts
    context.user_data["wechsel"]["new_tenant"] = {
        "first_name": first_name,
        "last_name": last_name,
        "street": street,
        "postal_code": postal_code,
        "city": city,
    }

    end_date = date.fromisoformat(context.user_data["wechsel"]["end_date"])
    default_start = end_date + timedelta(days=1)
    await update.message.reply_text(
        f"Start date for the new contract? (YYYY-MM-DD, e.g. {default_start.isoformat()})"
    )
    return START_DATE


async def receive_start_date(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        start_date = date.fromisoformat(update.message.text.strip())
    except ValueError:
        await update.message.reply_text("Invalid date. Format: YYYY-MM-DD")
        return START_DATE

    context.user_data["wechsel"]["start_date"] = start_date.isoformat()
    await update.message.reply_text("Monthly Nebenkosten-Vorauszahlung in EUR? (e.g. 100.00)")
    return ADVANCE


async def receive_advance(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        advance = Decimal(update.message.text.strip().replace(",", "."))
    except InvalidOperation:
        await update.message.reply_text("Invalid amount. Example: 100.00")
        return ADVANCE

    context.user_data["wechsel"]["advance_cents"] = round(advance * 100)

    w = context.user_data["wechsel"]
    nt = w["new_tenant"]
    summary = (
        f"Confirm Mieterwechsel:\n"
        f"  Outgoing contract ends: {w['end_date']}\n"
        f"  New tenant: {nt['first_name']} {nt['last_name']}, {nt['street']}, "
        f"{nt['postal_code']} {nt['city']}\n"
        f"  New contract starts: {w['start_date']}\n"
        f"  Monthly advance: {advance:.2f} EUR"
    )
    keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("Confirm", callback_data="wechsel_confirm"),
                InlineKeyboardButton("Cancel", callback_data="wechsel_cancel"),
            ]
        ]
    )
    await update.message.reply_text(summary, reply_markup=keyboard)
    return CONFIRM


async def confirm_wechsel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    w = context.user_data.get("wechsel")

    if query.data == "wechsel_cancel" or w is None:
        await query.edit_message_text("Mieterwechsel cancelled.")
        context.user_data.pop("wechsel", None)
        return ConversationHandler.END

    conn = get_conn(context)
    try:
        nt = w["new_tenant"]
        tenant_id = tenant_repo.create(
            conn,
            Tenant(
                id=0,
                first_name=nt["first_name"],
                last_name=nt["last_name"],
                street=nt["street"],
                postal_code=nt["postal_code"],
                city=nt["city"],
            ),
        )
        contract_repo.create(
            conn,
            Contract(
                id=0,
                unit_id=w["unit_id"],
                tenant_id=tenant_id,
                start_date=date.fromisoformat(w["start_date"]),
                end_date=None,
                monthly_vorauszahlung_nebenkosten_cents=w["advance_cents"],
            ),
        )
        contract_repo.end_contract(conn, w["old_contract_id"], date.fromisoformat(w["end_date"]))
    finally:
        conn.close()

    await query.edit_message_text(
        f"Mieterwechsel complete: {nt['first_name']} {nt['last_name']} moved in."
    )
    context.user_data.pop("wechsel", None)
    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data.pop("wechsel", None)
    await update.message.reply_text("Mieterwechsel cancelled.")
    return ConversationHandler.END


mieterwechsel_conversation = ConversationHandler(
    entry_points=[CallbackQueryHandler(start_wechsel, pattern=r"^wechsel_start:\d+$")],
    states={
        END_DATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_end_date)],
        NEW_TENANT: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_new_tenant)],
        START_DATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_start_date)],
        ADVANCE: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_advance)],
        CONFIRM: [CallbackQueryHandler(confirm_wechsel, pattern=r"^wechsel_(confirm|cancel)$")],
    },
    fallbacks=[MessageHandler(filters.COMMAND & filters.Regex("^/cancel$"), cancel)],
)
