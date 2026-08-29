-- ImmoManager schema. Money columns are INTEGER cents (never REAL) — see CLAUDE.md.
-- Applied by scripts/init_db.py. Additive changes only go in db/migrations/.

PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS landlord_profile (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    name TEXT NOT NULL,
    street TEXT NOT NULL,
    house_number TEXT NOT NULL,
    postal_code TEXT NOT NULL,
    city TEXT NOT NULL,
    tax_id TEXT,
    bank_iban TEXT,
    bank_bic TEXT,
    bank_account_holder TEXT,
    contact_email TEXT,
    contact_phone TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS properties (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    label TEXT NOT NULL,
    street TEXT NOT NULL,
    house_number TEXT NOT NULL,
    postal_code TEXT NOT NULL,
    city TEXT NOT NULL,
    total_wohnflaeche_m2 NUMERIC NOT NULL,
    build_year INTEGER,
    pre1994_uninsulated INTEGER NOT NULL DEFAULT 0 CHECK (pre1994_uninsulated IN (0, 1)),
    heating_split_ratio_consumption_pct NUMERIC CHECK (
        heating_split_ratio_consumption_pct IS NULL
        OR (heating_split_ratio_consumption_pct BETWEEN 50 AND 70)
    ),
    heating_combined_system INTEGER NOT NULL DEFAULT 0 CHECK (heating_combined_system IN (0, 1)),
    heating_metering_remote_readable INTEGER NOT NULL DEFAULT 0
        CHECK (heating_metering_remote_readable IN (0, 1)),
    heating_metering_compliant INTEGER NOT NULL DEFAULT 1
        CHECK (heating_metering_compliant IN (0, 1)),
    co2_building_tier_override INTEGER CHECK (
        co2_building_tier_override IS NULL OR co2_building_tier_override BETWEEN 1 AND 10
    ),
    co2_override_reason TEXT,
    gradtagstabelle_ref TEXT NOT NULL DEFAULT 'default',
    -- Kaufpreis (acquisition cost), for the /wealth net-equity view -- not a
    -- current market value estimate. NULL where unknown/not entered.
    purchase_price_cents INTEGER,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS units (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    property_id INTEGER NOT NULL REFERENCES properties (id) ON DELETE RESTRICT,
    label TEXT NOT NULL,
    unit_type TEXT NOT NULL CHECK (unit_type IN ('apartment', 'garage')),
    wohnflaeche_m2 NUMERIC,
    heated INTEGER NOT NULL DEFAULT 0 CHECK (heated IN (0, 1)),
    -- WEG Miteigentumsanteil, expressed per mille (e.g. 7.92 for "7,92/1000" as
    -- stated in a Grundbuch/Teilungserklärung) -- the unit's fixed share of the
    -- whole building, independent of how many of the building's other units (not
    -- owned by this landlord) are tracked here. Only meaningful for a condo/WEG
    -- unit; NULL for a landlord-owned-outright building.
    miteigentumsanteil_promille NUMERIC,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_units_property ON units (property_id);

CREATE TABLE IF NOT EXISTS tenants (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    first_name TEXT NOT NULL,
    last_name TEXT NOT NULL,
    street TEXT NOT NULL,
    postal_code TEXT NOT NULL,
    city TEXT NOT NULL,
    email TEXT,
    phone TEXT,
    bank_iban TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS contracts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    unit_id INTEGER NOT NULL REFERENCES units (id) ON DELETE RESTRICT,
    tenant_id INTEGER NOT NULL REFERENCES tenants (id) ON DELETE RESTRICT,
    start_date TEXT NOT NULL,
    end_date TEXT,
    monthly_vorauszahlung_nebenkosten_cents INTEGER NOT NULL DEFAULT 0,
    monthly_vorauszahlung_heizkosten_cents INTEGER,
    persons_count INTEGER,
    -- Kaution (§ 551 BGB) -- out of scope for the Abrechnung math itself, but real
    -- money the landlord must track and account for at move-out. deposit_cents is
    -- what was received; deposit_returned_* is filled in when the tenancy ends,
    -- which may be less than deposit_cents if damages were deducted.
    deposit_cents INTEGER NOT NULL DEFAULT 0,
    deposit_returned_cents INTEGER,
    deposit_returned_date TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now')),
    CHECK (end_date IS NULL OR end_date >= start_date),
    CHECK (deposit_returned_cents IS NULL OR deposit_returned_cents <= deposit_cents)
);

CREATE INDEX IF NOT EXISTS idx_contracts_unit ON contracts (unit_id);
CREATE INDEX IF NOT EXISTS idx_contracts_tenant ON contracts (tenant_id);

-- § 556a BGB: contractual distribution key per cost type, overriding the
-- Wohnfläche default. One row per (contract, cost_type) the Mietvertrag specifies
-- a non-default key for; absence means "use the property/statement default".
CREATE TABLE IF NOT EXISTS contract_cost_type_keys (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    contract_id INTEGER NOT NULL REFERENCES contracts (id) ON DELETE RESTRICT,
    cost_type_code INTEGER NOT NULL CHECK (cost_type_code BETWEEN 1 AND 17),
    distribution_key TEXT NOT NULL CHECK (
        distribution_key IN ('wohnflaeche', 'personenzahl', 'verbrauch', 'stueck', 'mea', 'custom')
    ),
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE (contract_id, cost_type_code)
);

-- § 2 Nr. 17 BetrKV: "sonstige" costs are only apportionable if individually named
-- in the Mietvertrag. Cost entries with cost_type_code=17 should reference one of
-- these; the bot/CLI warns (does not block) when they don't.
CREATE TABLE IF NOT EXISTS property_sonstige_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    property_id INTEGER NOT NULL REFERENCES properties (id) ON DELETE RESTRICT,
    description TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS cost_entries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    property_id INTEGER NOT NULL REFERENCES properties (id) ON DELETE RESTRICT,
    -- 1-17 = apportionable § 2 BetrKV cost type (config/cost_types.py:BetrKVCostType);
    -- 101+ = non-apportionable (repairs, admin, ...) --
    -- config/cost_types.py:NichtUmlagefaehigCostType. is_apportionable mirrors
    -- which range cost_type_code is in, kept as its own column so a query never
    -- has to duplicate that range check.
    cost_type_code INTEGER NOT NULL CHECK (
        (cost_type_code BETWEEN 1 AND 17) OR (cost_type_code BETWEEN 101 AND 199)
    ),
    is_apportionable INTEGER NOT NULL DEFAULT 1 CHECK (is_apportionable IN (0, 1)),
    billing_year INTEGER NOT NULL,
    amount_cents INTEGER NOT NULL,
    vendor_name TEXT,
    invoice_date TEXT,
    description TEXT,
    source_file_path TEXT,
    entry_method TEXT NOT NULL CHECK (entry_method IN ('manual', 'telegram_ocr')),
    ocr_confidence NUMERIC,
    ocr_raw_response TEXT,
    entered_by TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_cost_entries_property_year
    ON cost_entries (property_id, billing_year);

CREATE TABLE IF NOT EXISTS meter_readings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    unit_id INTEGER NOT NULL REFERENCES units (id) ON DELETE RESTRICT,
    meter_id TEXT NOT NULL,
    meter_type TEXT NOT NULL CHECK (
        meter_type IN ('heating', 'hot_water', 'cold_water', 'electricity_common')
    ),
    reading_date TEXT NOT NULL,
    value NUMERIC NOT NULL,
    billing_year INTEGER NOT NULL,
    remote_read INTEGER NOT NULL DEFAULT 0 CHECK (remote_read IN (0, 1)),
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_meter_readings_unit_year ON meter_readings (unit_id, billing_year);

CREATE TABLE IF NOT EXISTS billing_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    property_id INTEGER NOT NULL REFERENCES properties (id) ON DELETE RESTRICT,
    billing_year INTEGER NOT NULL,
    period_start TEXT NOT NULL,
    period_end TEXT NOT NULL,
    deadline_date TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'draft' CHECK (
        status IN ('draft', 'calculated', 'generated', 'sent', 'closed')
    ),
    notes TEXT,
    generated_at TEXT,
    sent_at TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE (property_id, billing_year)
);

CREATE TABLE IF NOT EXISTS billing_run_statements (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    billing_run_id INTEGER NOT NULL REFERENCES billing_runs (id) ON DELETE RESTRICT,
    contract_id INTEGER NOT NULL REFERENCES contracts (id) ON DELETE RESTRICT,
    document_type TEXT NOT NULL CHECK (
        document_type IN ('betriebskosten', 'wasser', 'heizkosten')
    ),
    document_path TEXT,
    total_costs_cents INTEGER NOT NULL,
    advance_payments_cents INTEGER NOT NULL,
    balance_cents INTEGER NOT NULL,
    proration_days INTEGER,
    proration_total_days INTEGER,
    proration_gradtag_anteile INTEGER,
    proration_gradtag_total INTEGER,
    calculation_snapshot_json TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE (billing_run_id, contract_id, document_type)
);

CREATE INDEX IF NOT EXISTS idx_billing_run_statements_run
    ON billing_run_statements (billing_run_id);

-- Loan/financing ledger, sourced from Kontoauszüge. Never apportionable, never fed
-- to calc_engine -- purely landlord bookkeeping (interest is a Werbungskosten
-- deduction on Anlage V, Tilgung/principal is not, hence tracked as separate
-- columns rather than one lump cost_entries row). See models/financing.py.
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

-- Fixed terms for scripts/roll_loan_ledger.py's monthly projection -- one row per
-- loan (keyed by the property its ledger entries are recorded under).
CREATE TABLE IF NOT EXISTS loan_terms (
    property_id INTEGER PRIMARY KEY REFERENCES properties (id) ON DELETE RESTRICT,
    lender TEXT NOT NULL,
    loan_account TEXT NOT NULL,
    annual_interest_rate_pct NUMERIC NOT NULL,
    monthly_principal_cents INTEGER NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Proportional allocation of a loan across every property it actually financed
-- (see models/financing.py:LoanPropertyShare). share_promille is typically each
-- property's own unit's miteigentumsanteil_promille when the loan financed a
-- multi-unit condo purchase in one transaction.
CREATE TABLE IF NOT EXISTS loan_property_shares (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    loan_account TEXT NOT NULL,
    property_id INTEGER NOT NULL REFERENCES properties (id) ON DELETE RESTRICT,
    share_promille NUMERIC NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE (loan_account, property_id)
);

-- Manually-entered point-in-time cash/checking balance -- no bank API exists, so
-- this is only ever as fresh as the last update. The most recent row is "current"
-- for the /wealth command. See models/wealth.py.
CREATE TABLE IF NOT EXISTS cash_balance_snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    balance_cents INTEGER NOT NULL,
    as_of_date TEXT NOT NULL,
    notes TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_cash_balance_snapshots_date
    ON cash_balance_snapshots (as_of_date);
