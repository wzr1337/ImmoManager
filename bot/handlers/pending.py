"""`/pending`: lists invoice scans saved to disk but not yet linked to a
cost_entries row -- recovery aid after a crash or an abandoned conversation
(the file is always persisted before extraction/confirmation, so nothing is lost,
just possibly stuck in incoming/)."""

from __future__ import annotations

from telegram import Update
from telegram.ext import CommandHandler, ContextTypes

from bot.context import get_settings


async def cmd_pending(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    settings = get_settings(context)
    incoming_dir = settings.invoices_dir / "incoming"
    if not incoming_dir.exists():
        await update.message.reply_text("No pending invoices.")
        return

    files = sorted(incoming_dir.glob("*.jpg"))
    if not files:
        await update.message.reply_text("No pending invoices.")
        return

    lines = ["Pending (not yet assigned):"] + [f"  {f.name}" for f in files]
    lines.append("\nResend the photo, or use the CLI to enter these manually.")
    await update.message.reply_text("\n".join(lines))


PENDING_HANDLER = CommandHandler("pending", cmd_pending)
