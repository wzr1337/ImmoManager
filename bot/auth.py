"""Chat-ID whitelist gate. This bot handles tenant financial/personal data, so it's
not optional -- refuses to start without TELEGRAM_ALLOWED_CHAT_IDS set, and silently
ignores (doesn't even reply to) any sender not on the list, rather than confirming
the bot's existence to them.

Enforced via a single gatekeeper handler registered in an early handler group
(see bot/main.py) rather than decorating every individual handler -- one choke
point is much harder to accidentally bypass than remembering a decorator on every
new handler added later."""

from __future__ import annotations

import logging

from telegram import Update
from telegram.ext import ApplicationHandlerStop, ContextTypes

logger = logging.getLogger(__name__)


class Whitelist:
    def __init__(self, allowed_chat_ids: frozenset[int]) -> None:
        if not allowed_chat_ids:
            raise ValueError(
                "TELEGRAM_ALLOWED_CHAT_IDS is empty -- refusing to start a bot with no "
                "whitelist. Set it in .env (comma-separated chat IDs)."
            )
        self._allowed = allowed_chat_ids

    def is_allowed(self, chat_id: int) -> bool:
        return chat_id in self._allowed

    def __len__(self) -> int:
        return len(self._allowed)


async def gatekeeper(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    whitelist: Whitelist = context.bot_data["whitelist"]
    chat_id = update.effective_chat.id if update.effective_chat else None
    if chat_id is None or not whitelist.is_allowed(chat_id):
        logger.warning("Rejected update from non-whitelisted chat_id=%s", chat_id)
        raise ApplicationHandlerStop
