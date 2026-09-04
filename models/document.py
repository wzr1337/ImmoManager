from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

DocumentCategory = Literal["hausverwaltung", "grundsteuer", "versicherung", "behoerde", "sonstige"]


@dataclass(frozen=True)
class PropertyDocument:
    id: int
    property_id: int
    category: DocumentCategory
    title: str
    file_path: str
    unit_id: int | None = None
    billing_year: int | None = None
    notes: str | None = None
    uploaded_by: str | None = None
