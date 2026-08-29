from __future__ import annotations

import sqlite3
from datetime import date
from decimal import Decimal

from config.cost_types import is_apportionable_code
from db.money import from_cents, to_cents
from models.invoice import CostEntry


def _row_to_model(row: sqlite3.Row) -> CostEntry:
    return CostEntry(
        id=row["id"],
        property_id=row["property_id"],
        cost_type_code=row["cost_type_code"],
        is_apportionable=bool(row["is_apportionable"]),
        billing_year=row["billing_year"],
        amount_cents=row["amount_cents"],
        vendor_name=row["vendor_name"],
        invoice_date=date.fromisoformat(row["invoice_date"]) if row["invoice_date"] else None,
        description=row["description"],
        source_file_path=row["source_file_path"],
        entry_method=row["entry_method"],
        ocr_confidence=row["ocr_confidence"],
        entered_by=row["entered_by"],
    )


def create(
    conn: sqlite3.Connection,
    *,
    property_id: int,
    cost_type_code: int,
    billing_year: int,
    amount: Decimal,
    vendor_name: str | None,
    invoice_date: date | None,
    description: str | None,
    source_file_path: str | None,
    entry_method: str,
    ocr_confidence: float | None = None,
    ocr_raw_response: str | None = None,
    entered_by: str | None = None,
) -> int:
    cur = conn.execute(
        """
        INSERT INTO cost_entries
            (property_id, cost_type_code, is_apportionable, billing_year, amount_cents,
             vendor_name, invoice_date, description, source_file_path, entry_method,
             ocr_confidence, ocr_raw_response, entered_by)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            property_id,
            cost_type_code,
            int(is_apportionable_code(cost_type_code)),
            billing_year,
            to_cents(amount),
            vendor_name,
            invoice_date.isoformat() if invoice_date else None,
            description,
            source_file_path,
            entry_method,
            ocr_confidence,
            ocr_raw_response,
            entered_by,
        ),
    )
    conn.commit()
    return cur.lastrowid


def totals_by_cost_type(
    conn: sqlite3.Connection, property_id: int, billing_year: int
) -> dict[int, Decimal]:
    """Apportionable cost types only (is_apportionable=1) -- this feeds
    calc_engine's cost_totals_by_type, and a repair or admin invoice must never
    enter the tenant-billed pool (docs/legal-requirements.md §2). Use
    list_non_apportionable_for_property_year for the landlord's own tracking."""
    rows = conn.execute(
        """
        SELECT cost_type_code, SUM(amount_cents) AS total_cents
        FROM cost_entries
        WHERE property_id = ? AND billing_year = ? AND is_apportionable = 1
        GROUP BY cost_type_code
        """,
        (property_id, billing_year),
    ).fetchall()
    return {r["cost_type_code"]: from_cents(r["total_cents"]) for r in rows}


def list_non_apportionable_for_property_year(
    conn: sqlite3.Connection, property_id: int, billing_year: int
) -> list[CostEntry]:
    """Nicht umlagefähige Kosten (repairs, admin, ...) recorded for the landlord's
    own bookkeeping -- never included in a tenant Abrechnung."""
    rows = conn.execute(
        """
        SELECT * FROM cost_entries
        WHERE property_id = ? AND billing_year = ? AND is_apportionable = 0
        ORDER BY invoice_date
        """,
        (property_id, billing_year),
    ).fetchall()
    return [_row_to_model(r) for r in rows]


def list_for_property_year(
    conn: sqlite3.Connection, property_id: int, billing_year: int
) -> list[CostEntry]:
    rows = conn.execute(
        "SELECT * FROM cost_entries WHERE property_id = ? AND billing_year = ? ORDER BY invoice_date",
        (property_id, billing_year),
    ).fetchall()
    return [_row_to_model(r) for r in rows]
