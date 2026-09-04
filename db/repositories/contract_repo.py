from __future__ import annotations

import sqlite3
from datetime import date

from models.tenant import Contract, ContractCostTypeKey


def _row_to_model(row: sqlite3.Row) -> Contract:
    return Contract(
        id=row["id"],
        unit_id=row["unit_id"],
        tenant_id=row["tenant_id"],
        start_date=date.fromisoformat(row["start_date"]),
        end_date=date.fromisoformat(row["end_date"]) if row["end_date"] else None,
        monthly_vorauszahlung_nebenkosten_cents=row["monthly_vorauszahlung_nebenkosten_cents"],
        monthly_vorauszahlung_heizkosten_cents=row["monthly_vorauszahlung_heizkosten_cents"],
        persons_count=row["persons_count"],
        deposit_cents=row["deposit_cents"],
        deposit_returned_cents=row["deposit_returned_cents"],
        deposit_returned_date=(
            date.fromisoformat(row["deposit_returned_date"])
            if row["deposit_returned_date"]
            else None
        ),
    )


def create(conn: sqlite3.Connection, contract: Contract) -> int:
    cur = conn.execute(
        """
        INSERT INTO contracts
            (unit_id, tenant_id, start_date, end_date,
             monthly_vorauszahlung_nebenkosten_cents, monthly_vorauszahlung_heizkosten_cents,
             persons_count, deposit_cents)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            contract.unit_id,
            contract.tenant_id,
            contract.start_date.isoformat(),
            contract.end_date.isoformat() if contract.end_date else None,
            contract.monthly_vorauszahlung_nebenkosten_cents,
            contract.monthly_vorauszahlung_heizkosten_cents,
            contract.persons_count,
            contract.deposit_cents,
        ),
    )
    conn.commit()
    return cur.lastrowid


def get(conn: sqlite3.Connection, contract_id: int) -> Contract | None:
    row = conn.execute("SELECT * FROM contracts WHERE id = ?", (contract_id,)).fetchone()
    return _row_to_model(row) if row else None


def list_for_property(conn: sqlite3.Connection, property_id: int) -> list[Contract]:
    rows = conn.execute(
        """
        SELECT contracts.* FROM contracts
        JOIN units ON units.id = contracts.unit_id
        WHERE units.property_id = ?
        ORDER BY contracts.start_date
        """,
        (property_id,),
    ).fetchall()
    return [_row_to_model(r) for r in rows]


def list_for_tenant(conn: sqlite3.Connection, tenant_id: int) -> list[Contract]:
    rows = conn.execute(
        "SELECT * FROM contracts WHERE tenant_id = ? ORDER BY start_date DESC", (tenant_id,)
    ).fetchall()
    return [_row_to_model(r) for r in rows]


def end_contract(conn: sqlite3.Connection, contract_id: int, end_date: date) -> None:
    """Mieterwechsel step 1: close out the outgoing tenant's contract. The incoming
    tenant then gets a new contract row via create() -- contracts are never mutated
    to change tenant, only closed and replaced, so history stays intact."""
    conn.execute(
        "UPDATE contracts SET end_date = ?, updated_at = datetime('now') WHERE id = ?",
        (end_date.isoformat(), contract_id),
    )
    conn.commit()


def set_deposit(conn: sqlite3.Connection, contract_id: int, deposit_cents: int) -> None:
    """Backfills/corrects the Kaution amount held for a contract."""
    conn.execute(
        "UPDATE contracts SET deposit_cents = ?, updated_at = datetime('now') WHERE id = ?",
        (deposit_cents, contract_id),
    )
    conn.commit()


def return_deposit(
    conn: sqlite3.Connection, contract_id: int, returned_cents: int, returned_date: date
) -> None:
    """Records the Kaution being paid back at move-out -- returned_cents may be
    less than the held deposit_cents if damages were deducted (schema CHECK
    enforces returned <= held)."""
    conn.execute(
        """
        UPDATE contracts
        SET deposit_returned_cents = ?, deposit_returned_date = ?, updated_at = datetime('now')
        WHERE id = ?
        """,
        (returned_cents, returned_date.isoformat(), contract_id),
    )
    conn.commit()


def active_for_unit_in_period(
    conn: sqlite3.Connection, unit_id: int, period_start: date, period_end: date
) -> list[Contract]:
    """Contracts on this unit that overlap [period_start, period_end] at all."""
    rows = conn.execute(
        """
        SELECT * FROM contracts
        WHERE unit_id = ?
          AND start_date <= ?
          AND (end_date IS NULL OR end_date >= ?)
        ORDER BY start_date
        """,
        (unit_id, period_end.isoformat(), period_start.isoformat()),
    ).fetchall()
    return [_row_to_model(r) for r in rows]


def set_cost_type_key(
    conn: sqlite3.Connection, contract_id: int, cost_type_code: int, distribution_key: str
) -> None:
    conn.execute(
        """
        INSERT INTO contract_cost_type_keys (contract_id, cost_type_code, distribution_key)
        VALUES (?, ?, ?)
        ON CONFLICT (contract_id, cost_type_code) DO UPDATE SET distribution_key = excluded.distribution_key
        """,
        (contract_id, cost_type_code, distribution_key),
    )
    conn.commit()


def get_cost_type_keys(conn: sqlite3.Connection, contract_id: int) -> list[ContractCostTypeKey]:
    rows = conn.execute(
        "SELECT * FROM contract_cost_type_keys WHERE contract_id = ?", (contract_id,)
    ).fetchall()
    return [
        ContractCostTypeKey(
            contract_id=r["contract_id"],
            cost_type_code=r["cost_type_code"],
            distribution_key=r["distribution_key"],
        )
        for r in rows
    ]


def set_cost_type_allowlist(
    conn: sqlite3.Connection, contract_id: int, cost_type_codes: list[int]
) -> None:
    """Replace-all: the Mietvertrag's full named list is entered each time, not
    added to incrementally -- avoids stale codes lingering after a lease amendment."""
    conn.execute("DELETE FROM contract_cost_type_allowlist WHERE contract_id = ?", (contract_id,))
    conn.executemany(
        "INSERT INTO contract_cost_type_allowlist (contract_id, cost_type_code) VALUES (?, ?)",
        [(contract_id, code) for code in cost_type_codes],
    )
    conn.commit()


def get_cost_type_allowlist(conn: sqlite3.Connection, contract_id: int) -> list[int]:
    rows = conn.execute(
        "SELECT cost_type_code FROM contract_cost_type_allowlist "
        "WHERE contract_id = ? ORDER BY cost_type_code",
        (contract_id,),
    ).fetchall()
    return [r["cost_type_code"] for r in rows]
