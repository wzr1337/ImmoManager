-- Adds WEG-Verwalter contact info and Grundsteuer reference numbers to
-- properties. Additive only, tolerated as re-runnable by scripts/init_db.py
-- (duplicate column name is caught and skipped). See db/schema.sql.
ALTER TABLE properties ADD COLUMN verwalter_name TEXT;
ALTER TABLE properties ADD COLUMN verwalter_contact_person TEXT;
ALTER TABLE properties ADD COLUMN verwalter_email TEXT;
ALTER TABLE properties ADD COLUMN verwalter_phone TEXT;
ALTER TABLE properties ADD COLUMN verwalter_address TEXT;
ALTER TABLE properties ADD COLUMN weg_name TEXT;
ALTER TABLE properties ADD COLUMN grundsteuer_objektnummer TEXT;
ALTER TABLE properties ADD COLUMN grundsteuer_debitorennummer TEXT;
ALTER TABLE properties ADD COLUMN grundsteuer_kassenzeichen TEXT;
