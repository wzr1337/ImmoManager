from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal


@dataclass(frozen=True)
class PropertyWealthLine:
    property_id: int
    label: str
    purchase_price: Decimal | None
    liability: Decimal

    @property
    def net_equity(self) -> Decimal | None:
        """None (not 0) when purchase_price is unknown -- an unknown asset value
        must never silently read as "no equity", it should read as "incomplete"."""
        if self.purchase_price is None:
            return None
        return self.purchase_price - self.liability


@dataclass(frozen=True)
class WealthSummary:
    cash_balance: Decimal
    cash_as_of: date | None
    property_lines: list[PropertyWealthLine]

    @property
    def total_property_equity(self) -> Decimal:
        return sum(
            (line.net_equity for line in self.property_lines if line.net_equity is not None),
            Decimal(0),
        )

    @property
    def has_incomplete_property_data(self) -> bool:
        return any(line.purchase_price is None for line in self.property_lines)

    @property
    def total_wealth(self) -> Decimal:
        return self.cash_balance + self.total_property_equity


@dataclass(frozen=True)
class CashBalanceSnapshot:
    """A manually-entered point-in-time cash/checking balance -- there's no bank
    API integration, so this is only ever as fresh as the last time it was updated
    (see bot's /wealth command and scripts.cli set-cash-balance). The latest
    snapshot is what /wealth treats as "current"."""

    id: int
    balance_cents: int
    as_of_date: date
    notes: str | None = None
