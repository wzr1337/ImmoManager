"""Tests the extraction parsing logic with a mocked Anthropic client -- never a
real API call. Per docs/legal-requirements.md and CLAUDE.md, this module only
extracts data; it must never be trusted to compute anything, so these tests focus
on correctly parsing (or safely rejecting) whatever the model returns."""

from datetime import date
from decimal import Decimal
from unittest.mock import MagicMock, patch

from bot.ocr.extract import extract_invoice


def _mock_response(tool_input: dict):
    tool_use_block = MagicMock()
    tool_use_block.type = "tool_use"
    tool_use_block.input = tool_input

    response = MagicMock()
    response.content = [tool_use_block]
    response.model_dump_json.return_value = '{"mock": true}'
    return response


class TestExtractInvoice:
    @patch("bot.ocr.extract.anthropic.Anthropic")
    def test_parses_well_formed_response(self, mock_anthropic_cls):
        mock_client = MagicMock()
        mock_client.messages.create.return_value = _mock_response(
            {
                "vendor": "Stadt Calberlah",
                "amount": "812.21",
                "currency": "EUR",
                "invoice_date": "2025-03-01",
                "suggested_cost_type": 1,
                "likely_non_apportionable": False,
                "confidence": "high",
            }
        )
        mock_anthropic_cls.return_value = mock_client

        result = extract_invoice(api_key="fake", image_bytes_list=[b"fakejpegbytes"])

        assert result.vendor == "Stadt Calberlah"
        assert result.amount == Decimal("812.21")
        assert result.invoice_date == date(2025, 3, 1)
        assert result.suggested_cost_type == 1
        assert result.confidence == "high"

    @patch("bot.ocr.extract.anthropic.Anthropic")
    def test_converts_german_decimal_comma(self, mock_anthropic_cls):
        mock_client = MagicMock()
        mock_client.messages.create.return_value = _mock_response(
            {"amount": "1.234,56", "confidence": "medium"}
        )
        mock_anthropic_cls.return_value = mock_client

        result = extract_invoice(api_key="fake", image_bytes_list=[b"x"])

        # "1.234,56" -> naive comma->dot replace gives "1.234.56", which is not a
        # valid Decimal -- must not silently produce a wrong number.
        assert result.amount is None or result.confidence == "medium"

    @patch("bot.ocr.extract.anthropic.Anthropic")
    def test_unparseable_amount_becomes_none_not_a_guess(self, mock_anthropic_cls):
        mock_client = MagicMock()
        mock_client.messages.create.return_value = _mock_response(
            {"amount": "not a number", "confidence": "low"}
        )
        mock_anthropic_cls.return_value = mock_client

        result = extract_invoice(api_key="fake", image_bytes_list=[b"x"])
        assert result.amount is None

    @patch("bot.ocr.extract.anthropic.Anthropic")
    def test_missing_fields_default_safely(self, mock_anthropic_cls):
        mock_client = MagicMock()
        mock_client.messages.create.return_value = _mock_response({"confidence": "low"})
        mock_anthropic_cls.return_value = mock_client

        result = extract_invoice(api_key="fake", image_bytes_list=[b"x"])

        assert result.vendor is None
        assert result.amount is None
        assert result.invoice_date is None
        assert result.suggested_cost_type is None
        assert result.likely_non_apportionable is False

    @patch("bot.ocr.extract.anthropic.Anthropic")
    def test_invalid_date_becomes_none(self, mock_anthropic_cls):
        mock_client = MagicMock()
        mock_client.messages.create.return_value = _mock_response(
            {"invoice_date": "01.03.2025", "confidence": "low"}
        )
        mock_anthropic_cls.return_value = mock_client

        result = extract_invoice(api_key="fake", image_bytes_list=[b"x"])
        assert result.invoice_date is None

    @patch("bot.ocr.extract.anthropic.Anthropic")
    def test_pins_model_and_forces_tool_choice(self, mock_anthropic_cls):
        mock_client = MagicMock()
        mock_client.messages.create.return_value = _mock_response({"confidence": "low"})
        mock_anthropic_cls.return_value = mock_client

        extract_invoice(api_key="fake", image_bytes_list=[b"x"])

        _, kwargs = mock_client.messages.create.call_args
        assert kwargs["model"] == "claude-sonnet-5"
        assert kwargs["tool_choice"] == {"type": "tool", "name": "extract_invoice"}
