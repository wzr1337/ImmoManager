from __future__ import annotations

import sqlite3
from datetime import date

from models.kassenbuch import KassenbuchEntry


def _row_to_model(row: sqlite3.Row) -> KassenbuchEntry:
    return KassenbuchEntry(
        id=row["id"],
        property_id=row["property_id"],
        entry_date=date.fromisoformat(row["entry_date"]),
        position=row["position"],
        amount_patrick_cents=row["amount_patrick_cents"],
        amount_sven_cents=row["amount_sven_cents"],
        amount_gemeinschaftskonto_cents=row["amount_gemeinschaftskonto_cents"],
        amount_total_cents=row["amount_total_cents"],
        notes=row["notes"],
    )


def create(
    conn: sqlite3.Connection,
    *,
    property_id: int,
    entry_date: date,
    position: str,
    amount_patrick_cents: int = 0,
    amount_sven_cents: int = 0,
    amount_gemeinschaftskonto_cents: int = 0,
    notes: str | None = None,
) -> int:
    amount_total_cents = amount_patrick_cents + amount_sven_cents + amount_gemeinschaftskonto_cents
    cur = conn.execute(
        """
        INSERT INTO kassenbuch_entries
            (property_id, entry_date, position, amount_patrick_cents, amount_sven_cents,
             amount_gemeinschaftskonto_cents, amount_total_cents, notes)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            property_id,
            entry_date.isoformat(),
            position,
            amount_patrick_cents,
            amount_sven_cents,
            amount_gemeinschaftskonto_cents,
            amount_total_cents,
            notes,
        ),
    )
    conn.commit()
    return cur.lastrowid


def list_for_property(conn: sqlite3.Connection, property_id: int) -> list[KassenbuchEntry]:
    rows = conn.execute(
        "SELECT * FROM kassenbuch_entries WHERE property_id = ? ORDER BY entry_date, id",
        (property_id,),
    ).fetchall()
    return [_row_to_model(r) for r in rows]


def running_balance_cents(conn: sqlite3.Connection, property_id: int) -> int:
    row = conn.execute(
        "SELECT COALESCE(SUM(amount_total_cents), 0) AS total FROM kassenbuch_entries WHERE property_id = ?",
        (property_id,),
    ).fetchone()
    return row["total"]
