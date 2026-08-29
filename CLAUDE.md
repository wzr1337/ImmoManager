# ImmoManager — Coding Guidelines

Management software for Nebenkostenabrechnung across multiple rented apartments and
garages. Runs on a Raspberry Pi with SQLite + local file storage.

## Core principles

- **All Abrechnung math runs in plain Python code, never in an LLM call.** The only
  legitimate LLM use in this codebase is invoice OCR/data extraction (vendor, amount,
  date, cost type) from a scanned document. If you find yourself asking an LLM to add,
  divide, or apportion money, that's a bug — write a function instead.
- **Minimize LLM calls.** One extraction call per invoice, not per property, not per
  tenant, not per statement. Batch where possible.
- **No comments explaining what the code does** — names should do that. Comments only
  for non-obvious *why*: a legal requirement driving a specific formula (cite the
  paragraph, e.g. `# § 556a BGB: Wohnfläche is the default key absent contract terms`),
  a workaround, a subtle invariant.
- Don't add abstractions, config flags, or error handling for scenarios that can't
  happen. Trust internal code; validate only at real boundaries (Telegram input,
  invoice OCR output, imported invoice files).
- No emojis in code, commit messages, or bot-facing text unless the user asks for one.

## Style (Python)

- Python 3.11+, type hints on all function signatures, `dataclasses` or `pydantic`
  models for domain objects (Property, Tenant, Contract, Invoice, MeterReading).
- `black`-formatted, `ruff`-linted. Keep modules focused — a module doing "too much"
  is a sign to split it, but don't split for its own sake.
- Money values: use `Decimal`, never `float`, anywhere a Euro amount is computed or
  stored — floating point rounding errors are unacceptable in a legal cost statement.
- Dates: use `date`/`datetime` with explicit timezone awareness where relevant
  (billing deadlines are calendar dates, not instants).

## Secrets & data handling

- Real secrets (Telegram bot token, Anthropic API key) live in `.env` locally, never
  committed. `.env.example` documents variable names only.
- Tenant personal data (names, addresses, bank details) is third-party personal data
  under GDPR, not just the landlord's own — treat the SQLite DB and invoice scan
  storage as sensitive. Backups must be encrypted at rest.
- Never log full invoice contents, tenant bank details, or API keys — mask/redact.

## Testing

- Tests must exercise the real calculation code path, never assert against a
  hand-copied "expected" value that was derived the same way as the code under test —
  use independently worked examples (e.g. from the legal-requirements doc's worked
  cases) as fixtures.
- The calc engine (cost apportionment, HeizkostenV split, CO2KostAufG tiers,
  pro-ration, formal-requirements assembly) needs the heaviest test coverage in the
  repo — it is the part a mistake in is a legal/financial error, not a UX bug.

## Commits

- Conventional format: `type: subject` (`feat`, `fix`, `docs`, `refactor`, `test`,
  `chore`), body explains *why* when it's not obvious from the subject.

## Reference

See [docs/legal-requirements.md](docs/legal-requirements.md) for the legal rules the
calc engine must implement — read it before touching `calc_engine/` or anything
generating an Abrechnung document.
