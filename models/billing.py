from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Literal

BillingRunStatus = Literal["draft", "calculated", "generated", "sent", "closed"]
DocumentType = Literal["betriebskosten", "wasser", "heizkosten"]


@dataclass(frozen=True)
class BillingRun:
    id: int
    property_id: int
    billing_year: int
    period_start: date
    period_end: date
    deadline_date: date
    status: BillingRunStatus = "draft"
    notes: str | None = None


@dataclass(frozen=True)
class BillingRunStatement:
    id: int
    billing_run_id: int
    contract_id: int
    document_type: DocumentType
    document_path: str | None
    total_costs_cents: int
    advance_payments_cents: int
    balance_cents: int
    calculation_snapshot_json: str
    proration_days: int | None = None
    proration_total_days: int | None = None
    proration_gradtag_anteile: Decimal | None = None
    proration_gradtag_total: Decimal | None = None
