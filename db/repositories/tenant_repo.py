from __future__ import annotations

import sqlite3

from models.tenant import Tenant


def _row_to_model(row: sqlite3.Row) -> Tenant:
    return Tenant(
        id=row["id"],
        first_name=row["first_name"],
        last_name=row["last_name"],
        street=row["street"],
        postal_code=row["postal_code"],
        city=row["city"],
        email=row["email"],
        phone=row["phone"],
        bank_iban=row["bank_iban"],
    )


def create(conn: sqlite3.Connection, tenant: Tenant) -> int:
    cur = conn.execute(
        """
        INSERT INTO tenants (first_name, last_name, street, postal_code, city, email, phone, bank_iban)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            tenant.first_name,
            tenant.last_name,
            tenant.street,
            tenant.postal_code,
            tenant.city,
            tenant.email,
            tenant.phone,
            tenant.bank_iban,
        ),
    )
    conn.commit()
    return cur.lastrowid


def get(conn: sqlite3.Connection, tenant_id: int) -> Tenant | None:
    row = conn.execute("SELECT * FROM tenants WHERE id = ?", (tenant_id,)).fetchone()
    return _row_to_model(row) if row else None


def list_all(conn: sqlite3.Connection) -> list[Tenant]:
    rows = conn.execute("SELECT * FROM tenants ORDER BY last_name, first_name").fetchall()
    return [_row_to_model(r) for r in rows]
