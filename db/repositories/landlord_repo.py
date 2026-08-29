from __future__ import annotations

import sqlite3

from models.landlord import LandlordProfile


def _row_to_model(row: sqlite3.Row) -> LandlordProfile:
    return LandlordProfile(
        name=row["name"],
        street=row["street"],
        house_number=row["house_number"],
        postal_code=row["postal_code"],
        city=row["city"],
        tax_id=row["tax_id"],
        bank_iban=row["bank_iban"],
        bank_bic=row["bank_bic"],
        bank_account_holder=row["bank_account_holder"],
        contact_email=row["contact_email"],
        contact_phone=row["contact_phone"],
    )


def get(conn: sqlite3.Connection) -> LandlordProfile | None:
    row = conn.execute("SELECT * FROM landlord_profile WHERE id = 1").fetchone()
    return _row_to_model(row) if row else None


def upsert(conn: sqlite3.Connection, profile: LandlordProfile) -> None:
    conn.execute(
        """
        INSERT INTO landlord_profile
            (id, name, street, house_number, postal_code, city, tax_id,
             bank_iban, bank_bic, bank_account_holder, contact_email, contact_phone, updated_at)
        VALUES (1, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
        ON CONFLICT (id) DO UPDATE SET
            name = excluded.name, street = excluded.street, house_number = excluded.house_number,
            postal_code = excluded.postal_code, city = excluded.city, tax_id = excluded.tax_id,
            bank_iban = excluded.bank_iban, bank_bic = excluded.bank_bic,
            bank_account_holder = excluded.bank_account_holder,
            contact_email = excluded.contact_email, contact_phone = excluded.contact_phone,
            updated_at = datetime('now')
        """,
        (
            profile.name,
            profile.street,
            profile.house_number,
            profile.postal_code,
            profile.city,
            profile.tax_id,
            profile.bank_iban,
            profile.bank_bic,
            profile.bank_account_holder,
            profile.contact_email,
            profile.contact_phone,
        ),
    )
    conn.commit()
