-- Adds contract_cost_type_allowlist -- per-contract allow-list of which BetrKV
-- cost types the Mietvertrag actually names as chargeable. Additive only,
-- CREATE TABLE IF NOT EXISTS -- naturally idempotent. See db/schema.sql /
-- scripts/run_billing.py.
CREATE TABLE IF NOT EXISTS contract_cost_type_allowlist (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    contract_id INTEGER NOT NULL REFERENCES contracts (id) ON DELETE RESTRICT,
    cost_type_code INTEGER NOT NULL CHECK (cost_type_code BETWEEN 1 AND 17),
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE (contract_id, cost_type_code)
);
