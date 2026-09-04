-- Adds property_documents (uploaded papers: Hausverwaltung/WEG statements,
-- Grundsteuerbescheide, insurance, ...). Additive only, CREATE TABLE IF NOT
-- EXISTS -- naturally idempotent. See db/schema.sql / models/document.py.
CREATE TABLE IF NOT EXISTS property_documents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    property_id INTEGER NOT NULL REFERENCES properties (id) ON DELETE RESTRICT,
    unit_id INTEGER REFERENCES units (id) ON DELETE RESTRICT,
    category TEXT NOT NULL CHECK (
        category IN (
            'hausverwaltung', 'grundsteuer', 'versicherung', 'behoerde', 'sonstige'
        )
    ),
    title TEXT NOT NULL,
    billing_year INTEGER,
    file_path TEXT NOT NULL,
    notes TEXT,
    uploaded_by TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_property_documents_property
    ON property_documents (property_id, category);
