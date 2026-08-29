from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Literal

EntryMethod = Literal["manual", "telegram_ocr"]


@dataclass(frozen=True)
class CostEntry:
    id: int
    property_id: int
    cost_type_code: int
    is_apportionable: bool
    billing_year: int
    amount_cents: int
    vendor_name: str | None
    invoice_date: date | None
    description: str | None
    source_file_path: str | None
    entry_method: EntryMethod
    ocr_confidence: float | None = None
    entered_by: str | None = None


@dataclass(frozen=True)
class PropertySonstigeItem:
    id: int
    property_id: int
    description: str
