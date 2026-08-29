-- Adds loan_terms (drives scripts/roll_loan_ledger.py's monthly projection) and
-- loan_property_shares (proportional allocation across co-financed properties).
-- Additive only, both CREATE TABLE IF NOT EXISTS -- naturally idempotent.
CREATE TABLE IF NOT EXISTS loan_terms (
    property_id INTEGER PRIMARY KEY REFERENCES properties (id) ON DELETE RESTRICT,
    lender TEXT NOT NULL,
    loan_account TEXT NOT NULL,
    annual_interest_rate_pct NUMERIC NOT NULL,
    monthly_principal_cents INTEGER NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS loan_property_shares (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    loan_account TEXT NOT NULL,
    property_id INTEGER NOT NULL REFERENCES properties (id) ON DELETE RESTRICT,
    share_promille NUMERIC NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE (loan_account, property_id)
);
