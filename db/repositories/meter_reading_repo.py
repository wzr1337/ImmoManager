from __future__ import annotations

import sqlite3
from datetime import date
from decimal import Decimal

from models.meter_reading import MeterReading


def _row_to_model(row: sqlite3.Row) -> MeterReading:
    return MeterReading(
        id=row["id"],
        unit_id=row["unit_id"],
        meter_id=row["meter_id"],
        meter_type=row["meter_type"],
        reading_date=date.fromisoformat(row["reading_date"]),
        value=Decimal(str(row["value"])),
        billing_year=row["billing_year"],
        remote_read=bool(row["remote_read"]),
    )


def create(
    conn: sqlite3.Connection,
    *,
    unit_id: int,
    meter_id: str,
    meter_type: str,
    reading_date: date,
    value: Decimal,
    billing_year: int,
    remote_read: bool = False,
) -> int:
    cur = conn.execute(
        """
        INSERT INTO meter_readings (unit_id, meter_id, meter_type, reading_date, value, billing_year, remote_read)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            unit_id,
            meter_id,
            meter_type,
            reading_date.isoformat(),
            str(value),
            billing_year,
            int(remote_read),
        ),
    )
    conn.commit()
    return cur.lastrowid


def consumption_by_unit(
    conn: sqlite3.Connection, unit_ids: list[int], meter_type: str, billing_year: int
) -> dict[int, Decimal]:
    """Sums each unit's readings of the given type for the year (readings are stored
    as period consumption deltas, not raw meter counter values)."""
    if not unit_ids:
        return {}
    placeholders = ",".join("?" for _ in unit_ids)
    rows = conn.execute(
        f"""
        SELECT unit_id, SUM(value) AS total_value
        FROM meter_readings
        WHERE unit_id IN ({placeholders}) AND meter_type = ? AND billing_year = ?
        GROUP BY unit_id
        """,
        (*unit_ids, meter_type, billing_year),
    ).fetchall()
    return {r["unit_id"]: Decimal(str(r["total_value"])) for r in rows}


def list_for_unit_year(
    conn: sqlite3.Connection, unit_id: int, billing_year: int
) -> list[MeterReading]:
    rows = conn.execute(
        "SELECT * FROM meter_readings WHERE unit_id = ? AND billing_year = ? ORDER BY reading_date",
        (unit_id, billing_year),
    ).fetchall()
    return [_row_to_model(r) for r in rows]
