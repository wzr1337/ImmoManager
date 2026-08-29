-- Adds WEG Miteigentumsanteil tracking to units. Additive only -- see db/schema.sql
-- for the column's meaning. Applied by scripts/init_db.py, which tolerates this
-- running again on a DB that already has the column (no migrations-applied
-- ledger table; fine at this project's scale -- see scripts/init_db.py).
ALTER TABLE units ADD COLUMN miteigentumsanteil_promille NUMERIC;
