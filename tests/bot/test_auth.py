from unittest.mock import MagicMock

import pytest
from telegram.ext import ApplicationHandlerStop

from bot.auth import Whitelist, gatekeeper


class TestWhitelist:
    def test_rejects_empty_whitelist(self):
        with pytest.raises(ValueError):
            Whitelist(frozenset())

    def test_is_allowed(self):
        wl = Whitelist(frozenset({111, 222}))
        assert wl.is_allowed(111) is True
        assert wl.is_allowed(999) is False

    def test_len(self):
        assert len(Whitelist(frozenset({111, 222}))) == 2


class TestGatekeeper:
    @pytest.mark.asyncio
    async def test_allowed_chat_passes_through(self):
        whitelist = Whitelist(frozenset({660967207}))
        update = MagicMock()
        update.effective_chat.id = 660967207
        context = MagicMock()
        context.bot_data = {"whitelist": whitelist}

        await gatekeeper(update, context)  # must not raise

    @pytest.mark.asyncio
    async def test_disallowed_chat_stops_propagation(self):
        whitelist = Whitelist(frozenset({660967207}))
        update = MagicMock()
        update.effective_chat.id = 999999999
        context = MagicMock()
        context.bot_data = {"whitelist": whitelist}

        with pytest.raises(ApplicationHandlerStop):
            await gatekeeper(update, context)

    @pytest.mark.asyncio
    async def test_no_effective_chat_stops_propagation(self):
        whitelist = Whitelist(frozenset({660967207}))
        update = MagicMock()
        update.effective_chat = None
        context = MagicMock()
        context.bot_data = {"whitelist": whitelist}

        with pytest.raises(ApplicationHandlerStop):
            await gatekeeper(update, context)
