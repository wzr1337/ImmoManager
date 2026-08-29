"""Top-level /wealth: cash balance (manually tracked -- no bank API exists) +
net property equity (purchase price minus current loan liability, allocated
across co-financed properties by Miteigentumsanteil). The cash figure can only
ever be as fresh as the last update, so this also offers a quick "update cash
balance" flow rather than requiring the CLI."""

from __future__ import annotations

from datetime import date
from decimal import Decimal, InvalidOperation

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

from bot.context import get_conn
from db.repositories import wealth_repo
from docgen.format import format_wealth_summary

WAITING_AMOUNT = 0

_UPDATE_CASH_BUTTON = InlineKeyboardMarkup(
    [[InlineKeyboardButton("Bankguthaben aktualisieren", callback_data="wealth_update_cash")]]
)


async def cmd_wealth(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    conn = get_conn(context)
    try:
        summary = wealth_repo.compute_wealth_summary(conn)
    finally:
        conn.close()

    await update.message.reply_text(
        format_wealth_summary(summary), reply_markup=_UPDATE_CASH_BUTTON
    )


async def on_wealth_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    conn = get_conn(context)
    try:
        summary = wealth_repo.compute_wealth_summary(conn)
    finally:
        conn.close()

    await query.edit_message_text(format_wealth_summary(summary), reply_markup=_UPDATE_CASH_BUTTON)


async def start_update_cash(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("Aktuelles Bankguthaben? (z.B. 12345.67)")
    return WAITING_AMOUNT


async def receive_cash_amount(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        balance = Decimal(update.message.text.strip().replace(",", "."))
    except InvalidOperation:
        await update.message.reply_text("Ungültiger Betrag. Beispiel: 12345.67")
        return WAITING_AMOUNT

    conn = get_conn(context)
    try:
        wealth_repo.add_cash_snapshot(conn, round(balance * 100), date.today())
        summary = wealth_repo.compute_wealth_summary(conn)
    finally:
        conn.close()

    await update.message.reply_text(f"Gespeichert.\n\n{format_wealth_summary(summary)}")
    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Abgebrochen.")
    return ConversationHandler.END


WEALTH_COMMAND_HANDLER = CommandHandler("wealth", cmd_wealth)
WEALTH_CALLBACK_HANDLER = CallbackQueryHandler(on_wealth_callback, pattern=r"^wealth$")

update_cash_conversation = ConversationHandler(
    entry_points=[CallbackQueryHandler(start_update_cash, pattern=r"^wealth_update_cash$")],
    states={
        WAITING_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_cash_amount)],
    },
    fallbacks=[CommandHandler("cancel", cancel)],
)
