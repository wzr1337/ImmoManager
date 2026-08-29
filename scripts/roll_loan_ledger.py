"""Monthly loan ledger rollover: for every property with loan_terms configured,
projects any months missing since the latest recorded loan_payments entry up to
the current month, using the fixed rate/Tilgung from loan_terms. Each generated
row is clearly marked GESCHAETZT in its notes -- this is a projection, not a bank
statement. Replace an estimated entry with the real one (via `scripts.cli
add-loan-payment`, entering the correct date matches to overwrite by convention --
see deploy/INSTALL.md) once the actual Kontoauszug arrives; that's a manual step
for now (see docs/legal-requirements.md's general principle: don't guess where a
verifiable source exists).

Safe to run repeatedly (e.g. daily via systemd timer, see
deploy/systemd/immomanager-loan-rollover.*): does nothing if the latest entry
already covers the current month.

Usage: python -m scripts.roll_loan_ledger
"""

from __future__ import annotations

import calendar
import sys
from datetime import date
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config.settings import load_settings
from db.connection import connect
from db.repositories import financing_repo
from models.financing import LoanPayment

CENT = Decimal("0.01")


def _next_month(year: int, month: int) -> tuple[int, int]:
    return (year + 1, 1) if month == 12 else (year, month + 1)


def _month_end_day(year: int, month: int) -> int:
    return min(30, calendar.monthrange(year, month)[1])


def roll_property(conn, property_id: int, today: date) -> int:
    terms = financing_repo.get_terms(conn, property_id)
    if terms is None:
        return 0

    latest = financing_repo.get_latest_payment(conn, property_id)
    if latest is None:
        print(f"  property {property_id}: no existing ledger entry, skipping (needs a seed entry)")
        return 0

    year, month = latest.payment_date.year, latest.payment_date.month
    balance = Decimal(latest.balance_after_cents) / 100
    monthly_rate = terms.annual_interest_rate_pct / 100 / 12
    monthly_principal = Decimal(terms.monthly_principal_cents) / 100

    created = 0
    while True:
        year, month = _next_month(year, month)
        if (year, month) > (today.year, today.month):
            break

        interest = (balance * monthly_rate).quantize(CENT, rounding=ROUND_HALF_UP)
        principal = min(monthly_principal, balance)  # never amortize past zero
        balance = (balance - principal).quantize(CENT)
        payment_date = date(year, month, _month_end_day(year, month))

        financing_repo.create(
            conn,
            LoanPayment(
                id=0,
                property_id=property_id,
                payment_date=payment_date,
                interest_cents=int(interest * 100),
                principal_cents=int(principal * 100),
                balance_after_cents=int(balance * 100),
                lender=terms.lender,
                loan_account=terms.loan_account,
                notes=(
                    "GESCHAETZT (automatisch generiert durch monatlichen Rollover-Job) "
                    "- mit echtem Kontoauszug zu verifizieren"
                ),
            ),
        )
        print(
            f"  property {property_id}: added {payment_date} (Zinsen {interest}, Tilgung {principal})"
        )
        created += 1

    return created


def main() -> None:
    settings = load_settings()
    conn = connect(settings.db_path)
    today = date.today()
    try:
        terms = financing_repo.list_all_terms(conn)
        if not terms:
            print("No loan_terms configured -- nothing to roll. Use `scripts.cli set-loan-terms`.")
            return

        total_created = 0
        for t in terms:
            total_created += roll_property(conn, t.property_id, today)

        print(f"Done: {total_created} entr{'y' if total_created == 1 else 'ies'} added.")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
