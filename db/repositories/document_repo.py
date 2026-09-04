from __future__ import annotations

import sqlite3

from models.document import PropertyDocument


def _row_to_model(row: sqlite3.Row) -> PropertyDocument:
    return PropertyDocument(
        id=row["id"],
        property_id=row["property_id"],
        unit_id=row["unit_id"],
        category=row["category"],
        title=row["title"],
        billing_year=row["billing_year"],
        file_path=row["file_path"],
        notes=row["notes"],
        uploaded_by=row["uploaded_by"],
    )


def create(
    conn: sqlite3.Connection,
    *,
    property_id: int,
    category: str,
    title: str,
    file_path: str,
    unit_id: int | None = None,
    billing_year: int | None = None,
    notes: str | None = None,
    uploaded_by: str | None = None,
) -> int:
    cur = conn.execute(
        """
        INSERT INTO property_documents
            (property_id, unit_id, category, title, billing_year, file_path, notes, uploaded_by)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (property_id, unit_id, category, title, billing_year, file_path, notes, uploaded_by),
    )
    conn.commit()
    return cur.lastrowid


def list_for_property(
    conn: sqlite3.Connection, property_id: int, category: str | None = None
) -> list[PropertyDocument]:
    if category is None:
        rows = conn.execute(
            "SELECT * FROM property_documents WHERE property_id = ? ORDER BY category, created_at",
            (property_id,),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM property_documents WHERE property_id = ? AND category = ? "
            "ORDER BY created_at",
            (property_id, category),
        ).fetchall()
    return [_row_to_model(r) for r in rows]
