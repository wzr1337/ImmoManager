from __future__ import annotations

import sqlite3
from datetime import date

from models.financing import LoanPayment


def _row_to_model(row: sqlite3.Row) -> LoanPayment:
    return LoanPayment(
        id=row["id"],
        property_id=row["property_id"],
        payment_date=date.fromisoformat(row["payment_date"]),
        interest_cents=row["interest_cents"],
        principal_cents=row["principal_cents"],
        balance_after_cents=row["balance_after_cents"],
        lender=row["lender"],
        loan_account=row["loan_account"],
        notes=row["notes"],
    )


def create(conn: sqlite3.Connection, payment: LoanPayment) -> int:
    cur = conn.execute(
        """
        INSERT INTO loan_payments
            (property_id, payment_date, interest_cents, principal_cents,
             balance_after_cents, lender, loan_account, notes)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            payment.property_id,
            payment.payment_date.isoformat(),
            payment.interest_cents,
            payment.principal_cents,
            payment.balance_after_cents,
            payment.lender,
            payment.loan_account,
            payment.notes,
        ),
    )
    conn.commit()
    return cur.lastrowid


def list_for_property(conn: sqlite3.Connection, property_id: int) -> list[LoanPayment]:
    rows = conn.execute(
        "SELECT * FROM loan_payments WHERE property_id = ? ORDER BY payment_date",
        (property_id,),
    ).fetchall()
    return [_row_to_model(r) for r in rows]


def annual_interest_total_cents(conn: sqlite3.Connection, property_id: int, year: int) -> int:
    """Sum of deductible interest (Werbungskosten) for a calendar year -- Tilgung
    (principal_cents) is intentionally excluded, it's not tax-deductible."""
    row = conn.execute(
        """
        SELECT COALESCE(SUM(interest_cents), 0) AS total
        FROM loan_payments
        WHERE property_id = ? AND payment_date >= ? AND payment_date <= ?
        """,
        (property_id, f"{year}-01-01", f"{year}-12-31"),
    ).fetchone()
    return row["total"]
