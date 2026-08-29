from __future__ import annotations

import sqlite3
from datetime import date
from decimal import Decimal

from db.money import to_cents
from models.billing import BillingRun, BillingRunStatement


def _row_to_run(row: sqlite3.Row) -> BillingRun:
    return BillingRun(
        id=row["id"],
        property_id=row["property_id"],
        billing_year=row["billing_year"],
        period_start=date.fromisoformat(row["period_start"]),
        period_end=date.fromisoformat(row["period_end"]),
        deadline_date=date.fromisoformat(row["deadline_date"]),
        status=row["status"],
        notes=row["notes"],
    )


def create_run(
    conn: sqlite3.Connection,
    *,
    property_id: int,
    billing_year: int,
    period_start: date,
    period_end: date,
) -> int:
    # § 556 Abs. 3 BGB: statement must reach the tenant by Dec 31 of the year
    # following the billing period end, or the Nachzahlung claim is forfeited.
    deadline = date(period_end.year + 1, 12, 31)
    cur = conn.execute(
        """
        INSERT INTO billing_runs (property_id, billing_year, period_start, period_end, deadline_date)
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            property_id,
            billing_year,
            period_start.isoformat(),
            period_end.isoformat(),
            deadline.isoformat(),
        ),
    )
    conn.commit()
    return cur.lastrowid


def get_run(conn: sqlite3.Connection, run_id: int) -> BillingRun | None:
    row = conn.execute("SELECT * FROM billing_runs WHERE id = ?", (run_id,)).fetchone()
    return _row_to_run(row) if row else None


def set_run_status(conn: sqlite3.Connection, run_id: int, status: str) -> None:
    conn.execute(
        "UPDATE billing_runs SET status = ?, updated_at = datetime('now') WHERE id = ?",
        (status, run_id),
    )
    conn.commit()


def save_statement(
    conn: sqlite3.Connection,
    *,
    billing_run_id: int,
    contract_id: int,
    document_type: str,
    document_path: str | None,
    total_costs: Decimal,
    advance_payments: Decimal,
    balance: Decimal,
    calculation_snapshot_json: str,
    proration_days: int | None = None,
    proration_total_days: int | None = None,
) -> int:
    cur = conn.execute(
        """
        INSERT INTO billing_run_statements
            (billing_run_id, contract_id, document_type, document_path, total_costs_cents,
             advance_payments_cents, balance_cents, proration_days, proration_total_days,
             calculation_snapshot_json)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT (billing_run_id, contract_id, document_type) DO UPDATE SET
            document_path = excluded.document_path,
            total_costs_cents = excluded.total_costs_cents,
            advance_payments_cents = excluded.advance_payments_cents,
            balance_cents = excluded.balance_cents,
            proration_days = excluded.proration_days,
            proration_total_days = excluded.proration_total_days,
            calculation_snapshot_json = excluded.calculation_snapshot_json
        """,
        (
            billing_run_id,
            contract_id,
            document_type,
            document_path,
            to_cents(total_costs),
            to_cents(advance_payments),
            to_cents(balance),
            proration_days,
            proration_total_days,
            calculation_snapshot_json,
        ),
    )
    conn.commit()
    return cur.lastrowid


def list_statements_for_run(
    conn: sqlite3.Connection, billing_run_id: int
) -> list[BillingRunStatement]:
    rows = conn.execute(
        "SELECT * FROM billing_run_statements WHERE billing_run_id = ?", (billing_run_id,)
    ).fetchall()
    return [
        BillingRunStatement(
            id=r["id"],
            billing_run_id=r["billing_run_id"],
            contract_id=r["contract_id"],
            document_type=r["document_type"],
            document_path=r["document_path"],
            total_costs_cents=r["total_costs_cents"],
            advance_payments_cents=r["advance_payments_cents"],
            balance_cents=r["balance_cents"],
            calculation_snapshot_json=r["calculation_snapshot_json"],
            proration_days=r["proration_days"],
            proration_total_days=r["proration_total_days"],
        )
        for r in rows
    ]
