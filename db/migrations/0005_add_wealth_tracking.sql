-- Adds properties.purchase_price_cents and cash_balance_snapshots for the
-- /wealth command. See db/schema.sql for field meaning.
ALTER TABLE properties ADD COLUMN purchase_price_cents INTEGER;

CREATE TABLE IF NOT EXISTS cash_balance_snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    balance_cents INTEGER NOT NULL,
    as_of_date TEXT NOT NULL,
    notes TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_cash_balance_snapshots_date
    ON cash_balance_snapshots (as_of_date);
