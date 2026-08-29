-- Adds Kaution (§ 551 BGB) tracking to contracts. Additive only -- see db/schema.sql
-- for field meaning. Applied by scripts/init_db.py (tolerates re-running).
ALTER TABLE contracts ADD COLUMN deposit_cents INTEGER NOT NULL DEFAULT 0;
ALTER TABLE contracts ADD COLUMN deposit_returned_cents INTEGER;
ALTER TABLE contracts ADD COLUMN deposit_returned_date TEXT;
