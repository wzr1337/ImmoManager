from __future__ import annotations

import sqlite3
from datetime import date
from decimal import Decimal

from db.repositories import financing_repo, property_repo
from models.wealth import CashBalanceSnapshot, PropertyWealthLine, WealthSummary


def add_cash_snapshot(
    conn: sqlite3.Connection, balance_cents: int, as_of_date: date, notes: str | None = None
) -> int:
    cur = conn.execute(
        "INSERT INTO cash_balance_snapshots (balance_cents, as_of_date, notes) VALUES (?, ?, ?)",
        (balance_cents, as_of_date.isoformat(), notes),
    )
    conn.commit()
    return cur.lastrowid


def get_latest_cash_snapshot(conn: sqlite3.Connection) -> CashBalanceSnapshot | None:
    row = conn.execute(
        "SELECT * FROM cash_balance_snapshots ORDER BY as_of_date DESC, id DESC LIMIT 1"
    ).fetchone()
    if row is None:
        return None
    return CashBalanceSnapshot(
        id=row["id"],
        balance_cents=row["balance_cents"],
        as_of_date=date.fromisoformat(row["as_of_date"]),
        notes=row["notes"],
    )


def compute_wealth_summary(conn: sqlite3.Connection) -> WealthSummary:
    """Cash (manually tracked, see add_cash_snapshot) + net property equity
    (purchase price minus current outstanding loan liability, the latter allocated
    across co-financed properties by Miteigentumsanteil -- see
    financing_repo.current_liability_by_property)."""
    cash = get_latest_cash_snapshot(conn)
    liabilities = financing_repo.current_liability_by_property(conn)

    lines = [
        PropertyWealthLine(
            property_id=p.id,
            label=p.label,
            purchase_price=(
                Decimal(p.purchase_price_cents) / 100
                if p.purchase_price_cents is not None
                else None
            ),
            liability=liabilities.get(p.id, Decimal(0)),
        )
        for p in property_repo.list_all(conn)
    ]

    return WealthSummary(
        cash_balance=Decimal(cash.balance_cents) / 100 if cash else Decimal(0),
        cash_as_of=cash.as_of_date if cash else None,
        property_lines=lines,
    )
