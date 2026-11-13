from decimal import Decimal

from bot.handlers.invoice_intake import resolve_line_item_codes
from bot.ocr.extract import LineItem


def test_unmapped_position_becomes_non_apportionable():
    items = (
        LineItem("Hausmeister", Decimal("157.65"), 14),
        LineItem("Verwaltergebuehr", Decimal("324.87"), None),
    )

    assert [code for _item, code in resolve_line_item_codes(items)] == [14, 105]
