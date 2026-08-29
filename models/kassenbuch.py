from __future__ import annotations

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class KassenbuchEntry:
    """One line of the general cash ledger -- broader than cost_entries: every
    cash movement (capital/Kaufpreis, acquisition costs, deposit refunds, bank
    fees, cross-payer settlements), with who actually paid it, not just
    Abrechnung-relevant invoices. Some entries overlap in substance with a
    cost_entries row (e.g. a repair) -- that's intentional, they answer different
    questions ("what happened to the money" vs. "which Werbungskosten/BetrKV
    category"), not a data-integrity concern to reconcile automatically.

    amount_total_cents is stored (not computed at query time) so it always exactly
    matches what was entered, mirroring the source Kassenbuch's own "Summe" column."""

    id: int
    property_id: int
    entry_date: date
    position: str
    amount_patrick_cents: int
    amount_sven_cents: int
    amount_gemeinschaftskonto_cents: int
    amount_total_cents: int
    notes: str | None = None
