"""Decimal <-> integer-cents conversion at the DB boundary. See CLAUDE.md: money is
always Decimal in application code, INTEGER cents in SQLite, never float."""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal

CENT = Decimal("0.01")


def to_cents(amount: Decimal) -> int:
    return int(amount.quantize(CENT, rounding=ROUND_HALF_UP) * 100)


def from_cents(cents: int) -> Decimal:
    return (Decimal(cents) / 100).quantize(CENT)
