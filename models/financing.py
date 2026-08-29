from __future__ import annotations

from dataclasses import dataclass
from datetime import date


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
