-- Adds the loan/financing ledger. Additive only -- see db/schema.sql for the
-- table's meaning. CREATE TABLE IF NOT EXISTS is naturally idempotent (unlike the
-- ALTER TABLE ADD COLUMN migrations before it), so no special handling is needed
-- in scripts/init_db.py for this one.
CREATE TABLE IF NOT EXISTS loan_payments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    property_id INTEGER NOT NULL REFERENCES properties (id) ON DELETE RESTRICT,
    payment_date TEXT NOT NULL,
    interest_cents INTEGER NOT NULL DEFAULT 0,
    principal_cents INTEGER NOT NULL DEFAULT 0,
    balance_after_cents INTEGER NOT NULL,
    lender TEXT,
    loan_account TEXT,
    notes TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_loan_payments_property_date
    ON loan_payments (property_id, payment_date);
