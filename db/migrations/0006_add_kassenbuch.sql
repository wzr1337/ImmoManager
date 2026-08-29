-- Adds the general cash ledger (Kassenbuch). Additive only, CREATE TABLE IF NOT
-- EXISTS -- naturally idempotent. See db/schema.sql / models/kassenbuch.py.
CREATE TABLE IF NOT EXISTS kassenbuch_entries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    property_id INTEGER NOT NULL REFERENCES properties (id) ON DELETE RESTRICT,
    entry_date TEXT NOT NULL,
    position TEXT NOT NULL,
    amount_patrick_cents INTEGER NOT NULL DEFAULT 0,
    amount_sven_cents INTEGER NOT NULL DEFAULT 0,
    amount_gemeinschaftskonto_cents INTEGER NOT NULL DEFAULT 0,
    amount_total_cents INTEGER NOT NULL,
    notes TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_kassenbuch_entries_property_date
    ON kassenbuch_entries (property_id, entry_date);
