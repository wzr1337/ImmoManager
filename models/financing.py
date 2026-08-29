from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal


@dataclass(frozen=True)
class LoanTerms:
    """Fixed terms driving the monthly rollover job (scripts/roll_loan_ledger.py) --
    stored explicitly rather than inferred from the ledger's last entry, so a rate
    change or an atypical stub period in the history can't silently throw off
    future projections."""

    property_id: int
    lender: str
    loan_account: str
    annual_interest_rate_pct: Decimal
    monthly_principal_cents: int


@dataclass(frozen=True)
class LoanPropertyShare:
    """A loan_account may finance multiple properties bought together in one
    transaction (e.g. a flat + its garage). The ledger (LoanPayment) still lives
    under one nominal property_id -- this is what lets reporting allocate the
    interest/principal proportionally across every property the loan actually
    covers, by their Miteigentumsanteil, without splitting or duplicating the
    underlying bank-statement-sourced ledger rows."""

    loan_account: str
    property_id: int
    share_promille: Decimal


@dataclass(frozen=True)
class LoanPayment:
    """One Kontoauszug entry (or net of a same-period interest-charge +
    payment/Tilgung pair) for a property's financing. interest_cents is the
    portion relevant for Werbungskosten (tax-deductible); principal_cents (Tilgung)
    is not. balance_after_cents is the resulting loan balance, taken directly from
    the bank statement -- a straightforward cross-check that entries are complete
    and correctly split (principal reductions must sum to
    original_principal_cents - latest balance_after_cents)."""

    id: int
    property_id: int
    payment_date: date
    interest_cents: int
    principal_cents: int
    balance_after_cents: int
    lender: str | None = None
    loan_account: str | None = None
    notes: str | None = None
