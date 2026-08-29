# ImmoManager

Management software for German rental properties (apartments and garages): tenants,
contracts, and legally compliant per-property, per-tenant Nebenkostenabrechnung
(operating cost statements).

A Telegram bot accepts scanned invoices, extracts the relevant data (vendor, amount,
date, cost type), and lets the landlord assign them to a property. All Abrechnung
math runs in deterministic code — LLM calls are used only for invoice OCR/extraction,
never for the financial calculation itself. Statements are generated as Word (.docx)
documents with cost-breakdown tables per the BGH formal-correctness requirements.

Runs on a Raspberry Pi with SQLite + local file storage, with periodic encrypted
cloud backup.

## Status

Planning phase — see [docs/legal-requirements.md](docs/legal-requirements.md) for the
legal research underpinning the calculation engine design. Architecture plan pending
approval before implementation starts.

## Documentation

- [docs/legal-requirements.md](docs/legal-requirements.md) — Betriebskostenabrechnung
  legal requirements (BetrKV, HeizkostenV, CO2KostAufG, § 556 BGB) driving the data
  model and calc engine.
- `CLAUDE.md` — coding guidelines for this repository.
