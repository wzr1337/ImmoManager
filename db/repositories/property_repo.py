from __future__ import annotations

import sqlite3
from decimal import Decimal

from models.property import Property, Unit


def _row_to_property(row: sqlite3.Row) -> Property:
    return Property(
        id=row["id"],
        label=row["label"],
        street=row["street"],
        house_number=row["house_number"],
        postal_code=row["postal_code"],
        city=row["city"],
        total_wohnflaeche_m2=Decimal(str(row["total_wohnflaeche_m2"])),
        build_year=row["build_year"],
        pre1994_uninsulated=bool(row["pre1994_uninsulated"]),
        heating_split_ratio_consumption_pct=(
            Decimal(str(row["heating_split_ratio_consumption_pct"]))
            if row["heating_split_ratio_consumption_pct"] is not None
            else None
        ),
        heating_combined_system=bool(row["heating_combined_system"]),
        heating_metering_remote_readable=bool(row["heating_metering_remote_readable"]),
        heating_metering_compliant=bool(row["heating_metering_compliant"]),
        co2_building_tier_override=row["co2_building_tier_override"],
        co2_override_reason=row["co2_override_reason"],
        gradtagstabelle_ref=row["gradtagstabelle_ref"],
    )


def _row_to_unit(row: sqlite3.Row) -> Unit:
    return Unit(
        id=row["id"],
        property_id=row["property_id"],
        label=row["label"],
        unit_type=row["unit_type"],
        wohnflaeche_m2=(
            Decimal(str(row["wohnflaeche_m2"])) if row["wohnflaeche_m2"] is not None else None
        ),
        heated=bool(row["heated"]),
    )


def create(conn: sqlite3.Connection, property_: Property) -> int:
    cur = conn.execute(
        """
        INSERT INTO properties
            (label, street, house_number, postal_code, city, total_wohnflaeche_m2,
             build_year, pre1994_uninsulated, heating_split_ratio_consumption_pct,
             heating_combined_system, heating_metering_remote_readable,
             heating_metering_compliant, co2_building_tier_override, co2_override_reason,
             gradtagstabelle_ref)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            property_.label,
            property_.street,
            property_.house_number,
            property_.postal_code,
            property_.city,
            str(property_.total_wohnflaeche_m2),
            property_.build_year,
            int(property_.pre1994_uninsulated),
            (
                str(property_.heating_split_ratio_consumption_pct)
                if property_.heating_split_ratio_consumption_pct is not None
                else None
            ),
            int(property_.heating_combined_system),
            int(property_.heating_metering_remote_readable),
            int(property_.heating_metering_compliant),
            property_.co2_building_tier_override,
            property_.co2_override_reason,
            property_.gradtagstabelle_ref,
        ),
    )
    conn.commit()
    return cur.lastrowid


def get(conn: sqlite3.Connection, property_id: int) -> Property | None:
    row = conn.execute("SELECT * FROM properties WHERE id = ?", (property_id,)).fetchone()
    return _row_to_property(row) if row else None


def list_all(conn: sqlite3.Connection) -> list[Property]:
    rows = conn.execute("SELECT * FROM properties ORDER BY label").fetchall()
    return [_row_to_property(r) for r in rows]


def add_unit(conn: sqlite3.Connection, unit: Unit) -> int:
    cur = conn.execute(
        """
        INSERT INTO units (property_id, label, unit_type, wohnflaeche_m2, heated)
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            unit.property_id,
            unit.label,
            unit.unit_type,
            str(unit.wohnflaeche_m2) if unit.wohnflaeche_m2 is not None else None,
            int(unit.heated),
        ),
    )
    conn.commit()
    return cur.lastrowid


def list_units(conn: sqlite3.Connection, property_id: int) -> list[Unit]:
    rows = conn.execute(
        "SELECT * FROM units WHERE property_id = ? ORDER BY label", (property_id,)
    ).fetchall()
    return [_row_to_unit(r) for r in rows]


def add_sonstige_item(conn: sqlite3.Connection, property_id: int, description: str) -> int:
    cur = conn.execute(
        "INSERT INTO property_sonstige_items (property_id, description) VALUES (?, ?)",
        (property_id, description),
    )
    conn.commit()
    return cur.lastrowid


def list_sonstige_items(conn: sqlite3.Connection, property_id: int) -> list[str]:
    rows = conn.execute(
        "SELECT description FROM property_sonstige_items WHERE property_id = ?", (property_id,)
    ).fetchall()
    return [r["description"] for r in rows]
