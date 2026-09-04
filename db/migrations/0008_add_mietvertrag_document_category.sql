-- Adds 'mietvertrag' to property_documents.category. SQLite can't ALTER a CHECK
-- constraint, so this rebuilds the table (standard SQLite pattern), preserving
-- existing rows. See db/schema.sql / models/document.py.
CREATE TABLE property_documents_new (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    property_id INTEGER NOT NULL REFERENCES properties (id) ON DELETE RESTRICT,
    unit_id INTEGER REFERENCES units (id) ON DELETE RESTRICT,
    category TEXT NOT NULL CHECK (
        category IN (
            'hausverwaltung', 'grundsteuer', 'versicherung', 'behoerde', 'mietvertrag', 'sonstige'
        )
    ),
    title TEXT NOT NULL,
    billing_year INTEGER,
    file_path TEXT NOT NULL,
    notes TEXT,
    uploaded_by TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

INSERT INTO property_documents_new SELECT * FROM property_documents;
DROP TABLE property_documents;
ALTER TABLE property_documents_new RENAME TO property_documents;

CREATE INDEX IF NOT EXISTS idx_property_documents_property
    ON property_documents (property_id, category);
