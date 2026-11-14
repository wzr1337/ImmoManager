"""Entrypoint: python -m bot.main

Long-polling, not a webhook -- this Pi is behind home NAT with no public inbound
endpoint (matches the sibling linkedin-bot.service already running on the same
host). See deploy/systemd/immomanager-bot.service for how this runs in production.
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from telegram import Update
from telegram.error import NetworkError
from telegram.ext import Application, ApplicationBuilder, ContextTypes, TypeHandler

from bot.auth import Whitelist, gatekeeper
from bot.handlers.commands import CALLBACK_HANDLERS, COMMAND_HANDLERS
from bot.handlers.invoice_intake import invoice_conversation
from bot.handlers.mieterwechsel import mieterwechsel_conversation
from bot.handlers.pending import PENDING_HANDLER
from bot.handlers.wealth import (
    WEALTH_CALLBACK_HANDLER,
    WEALTH_COMMAND_HANDLER,
    update_cash_conversation,
)
from config.settings import load_settings

logging.basicConfig(format="%(asctime)s %(levelname)s %(name)s: %(message)s", level=logging.INFO)
# httpx logs the full request URL at INFO -- for the Telegram Bot API, the bot
# token IS the URL path (https://api.telegram.org/bot<TOKEN>/...), so leaving this
# at INFO leaks the token into every log line. CLAUDE.md: never log API keys.
logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)


async def on_error(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    # Telegram regularly answers getUpdates with 502 Bad Gateway; the library retries,
    # so a one-line warning is enough. Anything else is a real handler failure.
    if isinstance(context.error, NetworkError):
        logger.warning("Telegram network error: %s", context.error)
        return
    logger.error("Unhandled error in handler", exc_info=context.error)
    if isinstance(update, Update) and update.effective_message:
        await update.effective_message.reply_text("Something went wrong. See the bot log.")


def build_application() -> Application:
    settings = load_settings()

    if not settings.telegram_bot_token:
        raise SystemExit("TELEGRAM_BOT_TOKEN not set in .env")
    whitelist = Whitelist(settings.telegram_allowed_chat_ids)  # raises if empty

    application = ApplicationBuilder().token(settings.telegram_bot_token).build()
    application.bot_data["settings"] = settings
    application.bot_data["whitelist"] = whitelist

    # Group -1 runs before every other handler group; ApplicationHandlerStop in the
    # gatekeeper prevents any of the real handlers below from ever seeing an update
    # from a non-whitelisted chat.
    application.add_handler(TypeHandler(Update, gatekeeper), group=-1)
    application.add_error_handler(on_error)

    for handler in COMMAND_HANDLERS:
        application.add_handler(handler)
    for handler in CALLBACK_HANDLERS:
        application.add_handler(handler)
    application.add_handler(PENDING_HANDLER)
    application.add_handler(WEALTH_COMMAND_HANDLER)
    application.add_handler(WEALTH_CALLBACK_HANDLER)
    application.add_handler(update_cash_conversation)
    application.add_handler(mieterwechsel_conversation)
    application.add_handler(invoice_conversation)

    return application


def main() -> None:
    application = build_application()
    whitelist: Whitelist = application.bot_data["whitelist"]
    logger.info("Starting ImmoManager bot (whitelist size=%d)", len(whitelist))
    application.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
