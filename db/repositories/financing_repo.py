from __future__ import annotations

import sqlite3
from datetime import date
from decimal import ROUND_HALF_UP, Decimal

from models.financing import LoanPayment, LoanPropertyShare, LoanTerms

CENT = Decimal("0.01")


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


def get_latest_payment(conn: sqlite3.Connection, property_id: int) -> LoanPayment | None:
    row = conn.execute(
        "SELECT * FROM loan_payments WHERE property_id = ? ORDER BY payment_date DESC LIMIT 1",
        (property_id,),
    ).fetchone()
    return _row_to_model(row) if row else None


def set_terms(conn: sqlite3.Connection, terms: LoanTerms) -> None:
    conn.execute(
        """
        INSERT INTO loan_terms
            (property_id, lender, loan_account, annual_interest_rate_pct, monthly_principal_cents)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT (property_id) DO UPDATE SET
            lender = excluded.lender, loan_account = excluded.loan_account,
            annual_interest_rate_pct = excluded.annual_interest_rate_pct,
            monthly_principal_cents = excluded.monthly_principal_cents,
            updated_at = datetime('now')
        """,
        (
            terms.property_id,
            terms.lender,
            terms.loan_account,
            str(terms.annual_interest_rate_pct),
            terms.monthly_principal_cents,
        ),
    )
    conn.commit()


def get_terms(conn: sqlite3.Connection, property_id: int) -> LoanTerms | None:
    row = conn.execute("SELECT * FROM loan_terms WHERE property_id = ?", (property_id,)).fetchone()
    if row is None:
        return None
    return LoanTerms(
        property_id=row["property_id"],
        lender=row["lender"],
        loan_account=row["loan_account"],
        annual_interest_rate_pct=Decimal(str(row["annual_interest_rate_pct"])),
        monthly_principal_cents=row["monthly_principal_cents"],
    )


def list_all_terms(conn: sqlite3.Connection) -> list[LoanTerms]:
    rows = conn.execute("SELECT * FROM loan_terms").fetchall()
    return [
        LoanTerms(
            property_id=r["property_id"],
            lender=r["lender"],
            loan_account=r["loan_account"],
            annual_interest_rate_pct=Decimal(str(r["annual_interest_rate_pct"])),
            monthly_principal_cents=r["monthly_principal_cents"],
        )
        for r in rows
    ]


def set_property_share(
    conn: sqlite3.Connection, loan_account: str, property_id: int, share_promille: Decimal
) -> None:
    conn.execute(
        """
        INSERT INTO loan_property_shares (loan_account, property_id, share_promille)
        VALUES (?, ?, ?)
        ON CONFLICT (loan_account, property_id) DO UPDATE SET share_promille = excluded.share_promille
        """,
        (loan_account, property_id, str(share_promille)),
    )
    conn.commit()


def get_property_shares(conn: sqlite3.Connection, loan_account: str) -> list[LoanPropertyShare]:
    rows = conn.execute(
        "SELECT * FROM loan_property_shares WHERE loan_account = ?", (loan_account,)
    ).fetchall()
    return [
        LoanPropertyShare(
            loan_account=r["loan_account"],
            property_id=r["property_id"],
            share_promille=Decimal(str(r["share_promille"])),
        )
        for r in rows
    ]


def _allocate_by_shares(shares: list[LoanPropertyShare], total: Decimal) -> dict[int, Decimal]:
    """Proportional split with cent-exact rounding reconciliation, same principle
    as calc_engine.apportionment.apportion_by_weights (kept separate rather than
    reused directly -- calc_engine must stay free of any DB-adjacent imports)."""
    total_promille = sum(s.share_promille for s in shares)
    if total_promille == 0:
        return {}

    allocations = {
        s.property_id: (total * s.share_promille / total_promille).quantize(
            CENT, rounding=ROUND_HALF_UP
        )
        for s in shares
    }
    residual = total.quantize(CENT) - sum(allocations.values())
    if residual != 0:
        largest = max(allocations, key=lambda p: allocations[p])
        allocations[largest] += residual
    return allocations


def allocate_interest_by_property(
    conn: sqlite3.Connection, loan_account: str, year: int
) -> dict[int, Decimal]:
    """Splits a loan_account's total interest for a year proportionally across
    every property in loan_property_shares, by share_promille -- regardless of
    which single property_id the underlying ledger rows are recorded under (see
    models/financing.py:LoanPropertyShare). Returns {} if no shares are configured."""
    shares = get_property_shares(conn, loan_account)
    if not shares:
        return {}

    row = conn.execute(
        """
        SELECT COALESCE(SUM(interest_cents), 0) AS total
        FROM loan_payments
        WHERE loan_account = ? AND payment_date >= ? AND payment_date <= ?
        """,
        (loan_account, f"{year}-01-01", f"{year}-12-31"),
    ).fetchone()
    return _allocate_by_shares(shares, Decimal(row["total"]) / 100)


def current_liability_by_property(conn: sqlite3.Connection) -> dict[int, Decimal]:
    """Current outstanding loan balance per property (EUR), for the /wealth
    command. For a loan with configured loan_property_shares (e.g. a flat + its
    garage bought together), the latest balance is split by share_promille across
    every property it financed; a loan with no shares configured attributes its
    full balance to the single property its loan_terms/ledger is recorded under."""
    result: dict[int, Decimal] = {}
    for terms in list_all_terms(conn):
        latest = get_latest_payment(conn, terms.property_id)
        if latest is None:
            continue
        balance = Decimal(latest.balance_after_cents) / 100

        shares = get_property_shares(conn, terms.loan_account)
        if shares:
            for property_id, amount in _allocate_by_shares(shares, balance).items():
                result[property_id] = result.get(property_id, Decimal(0)) + amount
        else:
            result[terms.property_id] = result.get(terms.property_id, Decimal(0)) + balance
    return result
