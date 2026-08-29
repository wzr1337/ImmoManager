"""Presentation formatting only — the one place Decimal/date become display strings.
calc_engine stays formatting-free; templates stay logic-free."""

from __future__ import annotations

from datetime import date
from decimal import Decimal


def fmt_money(value: Decimal) -> str:
    # German convention: thousands '.', decimal ','. E.g. Decimal("1234.56") -> "1.234,56 €"
    sign = "-" if value < 0 else ""
    whole, _, frac = f"{abs(value):.2f}".partition(".")
    grouped = f"{int(whole):,}".replace(",", ".")
    return f"{sign}{grouped},{frac} €"


def fmt_number(value: Decimal, decimals: int = 2) -> str:
    whole, _, frac = f"{value:.{decimals}f}".partition(".")
    grouped = f"{int(whole):,}".replace(",", ".")
    return f"{grouped},{frac}" if decimals else grouped


def fmt_date(value: date) -> str:
    return value.strftime("%d.%m.%Y")
