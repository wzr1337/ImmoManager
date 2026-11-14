import logging
from unittest.mock import AsyncMock, MagicMock

from telegram import Update
from telegram.error import BadRequest, NetworkError

from bot.main import on_error


async def test_network_error_is_a_one_line_warning(caplog):
    context = MagicMock(error=NetworkError("Bad Gateway"))

    with caplog.at_level(logging.WARNING):
        await on_error(None, context)

    assert [r.levelname for r in caplog.records] == ["WARNING"]
    assert caplog.records[0].exc_info is None


async def test_handler_failure_is_logged_and_the_user_is_told(caplog):
    update = MagicMock(spec=Update)
    update.effective_message.reply_text = AsyncMock()
    context = MagicMock(error=BadRequest("boom"))

    with caplog.at_level(logging.ERROR):
        await on_error(update, context)

    assert caplog.records[0].exc_info is not None
    update.effective_message.reply_text.assert_awaited_once()
