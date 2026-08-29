# Rechtsgrundlagen der Nebenkostenabrechnung (Betriebskostenabrechnung)

Engineering reference for the calculation engine and document generator. This is not
legal advice — for actual disputes, consult a Mietrecht lawyer or Haus & Grund. It is
accurate as of 2026-08; laws and thresholds (CO2 price corridor, metering deadlines)
change year to year, so cost-type parameters must be configurable per billing year,
not hardcoded.

## 1. Legal basis

- **§§ 556, 556a, 560 BGB** — landlord/tenant framework: what may be billed as
  "Betriebskosten", the default distribution key, the annual statement deadline.
- **BetrKV (Betriebskostenverordnung)** — defines which cost types are apportionable
  (§ 2 BetrKV, 17 positions) and how "Betriebskosten" is defined (§ 1 BetrKV).
- **HeizkostenV (Heizkostenverordnung)** — mandatory consumption-based billing rules
  for heating and hot water, overrides § 556a BGB for those two cost types.
- **CO2KostAufG (CO2-Kostenaufteilungsgesetz, since Jan 2023)** — splits the CO2
  carbon-pricing surcharge on heating fuel between landlord and tenant based on the
  building's energy efficiency.
- **§ 259 BGB** — general standard for an orderly accounting statement (Rechnungslegung),
  underlies the BGH "formal correctness" test below.

## 2. Apportionable cost types (§ 2 BetrKV — 17 positions)

1. Grundsteuer (property tax)
2. Wasserversorgung (water supply)
3. Entwässerung (wastewater/sewage)
4. Heizung (heating) — subject to HeizkostenV split rules
5. Warmwasser (hot water) — subject to HeizkostenV split rules
6. Verbundene Heizungs-/Warmwasserkosten (combined systems)
7. Aufzug (elevator)
8. Straßenreinigung / Müllabfuhr (street cleaning / refuse collection)
9. Gebäudereinigung / Ungezieferbekämpfung (building cleaning / pest control)
10. Gartenpflege (garden/grounds upkeep)
11. Beleuchtung (common-area lighting/electricity)
12. Schornsteinreinigung (chimney sweeping)
13. Sach-/Haftpflichtversicherung (building/liability insurance)
14. Hauswart (caretaker)
15. Gemeinschafts-Antenne / Kabel (cable/antenna — narrowing relevance since 2024
    Nebenkostenprivileg abolition for TV, verify current applicability per contract)
16. Einrichtungen für Wäschepflege (shared laundry facilities)
17. Sonstige Betriebskosten (catch-all — **must be individually named in the
    Mietvertrag** to be apportionable; a generic "other costs" clause is not enough)

Anything not on this list (repairs, administration/Verwaltungskosten, vacancy costs)
is **not** apportionable and stays with the landlord — the calc engine must reject or
flag non-listed cost types rather than silently include them.

**Data model implication:** every cost/invoice entry needs a `cost_type` enum mapped to
one of these 17 positions (plus a per-property list of which "sonstige" items are
contractually allowed), so the engine can validate apportionability at entry time
rather than at Abrechnung time.

## 3. Distribution key (Umlageschlüssel)

- Default (no contractual agreement): **Wohnfläche** (§ 556a Abs. 1 BGB) — proportional
  living-area share of the property.
- The Mietvertrag may specify a different key per cost type (e.g. Personenzahl for
  water, Verbrauch for individually metered items, MEA/Miteigentumsanteile).
- Heating/hot water: **HeizkostenV overrides** any contractual key (see §4).
- The key actually applied, per cost type, must come from the **contract**, not be
  assumed globally — the data model needs a per-contract (or per-property, with
  per-contract override) key configuration.

**Garages/Stellplätze:** typically billed separately from the apartment (own small
cost pool: possibly none, or shared lighting/cleaning of the garage area), using
their own area or per-unit key — do not fold garage costs into the apartment
Wohnfläche pool unless the contract says so.

## 4. Heating & hot water (HeizkostenV)

- **50–70%** of heating costs must be billed by **measured consumption**; the
  remaining **30–50%** by Wohnfläche. The landlord picks a fixed split within that
  band (e.g. 70/30) — configurable per property, not hardcoded to one ratio.
- Same 50–70/30–50 split rule for hot water, calculated separately from heating
  unless costs are technically inseparable (combined systems, § 9 HeizkostenV, then
  a stipulated apportionment method applies).
- **Mandatory exception:** buildings built before 1994 that were never insulated to
  WärmeschutzV standard, where the tenant cannot influence consumption, must use a
  fixed **70/30** split.
- **Metering is mandatory** for centrally heated multi-unit buildings; devices must
  be remotely readable ("fernablesbar") — a rolling deadline applies (end of 2026 per
  current guidance) with a **15% mandatory tenant cost reduction (Kürzungsrecht)**
  triggered automatically, without proof of harm, if metering/remote-readability or
  the split-ratio band is violated. The engine should support flagging this penalty
  as a line item when a property's metering status is marked non-compliant.
- **Data model implication:** per-property heating system config (split ratio,
  metering type, remote-readable yes/no, pre-1994/uninsulated flag) and per-unit
  meter readings (consumption values) as first-class records.

## 5. CO2 cost split (CO2KostAufG)

- Applies to the **CO2 carbon-pricing** portion of heating fuel costs (not the whole
  heating bill) for buildings using fossil fuel heating.
- **Residential buildings:** 10-tier model (Stufenmodell) from 100/0 to 5/95
  (landlord/tenant), keyed by the building's **CO2 emissions per m² of heated area**:
  `CO2_per_sqm = (fuel_consumption × emission_factor) / heated_area`. Poorer building
  energy efficiency → landlord bears a higher share. The 10 tier boundaries and the
  fuel emission factors are published/updated by the responsible ministry and must be
  a **configurable table** (per billing year), not hardcoded constants.
- **Non-residential buildings** (this may include stand-alone garages, if legally
  classified non-residential): simplified flat **50/50** split, no tier lookup —
  but note unheated garages typically have no heating fuel cost at all, so CO2KostAufG
  is moot for them in practice; only relevant if a garage/workshop is heated.
- CO2 certificate price is auctioned since 2026 within a corridor (currently
  ~€55–65/t) rather than fixed — the emission-factor/price table must be refreshed
  yearly, sourced from the fuel supplier's invoice or official published factors, not
  assumed constant across years.
- Denkmalschutz/legal-impossibility exception can shift the landlord down one tier —
  must be documented; the config should allow a manual tier override with a reason
  field for audit purposes.

## 6. Formal requirements for a valid Abrechnung (BGH case law under § 259 BGB)

A statement must let an average tenant, without external help, verify the amount
billed to them. BGH requires at minimum:

1. **Zusammenstellung der Gesamtkosten** — total cost per cost type for the whole
   billing unit (building/property), not just the tenant's share.
2. **Angabe und Erläuterung des Verteilerschlüssels** — the distribution key used per
   cost type, stated explicitly (not just the resulting number).
3. **Berechnung des Anteils des Mieters** — the arithmetic producing the tenant's
   share from (1) and (2) shown, not just the final figure.
4. **Abzug der geleisteten Vorauszahlungen** — advance payments (Nebenkostenvorauszahlungen)
   made during the period, deducted to arrive at Nachzahlung/Guthaben.

Missing any of these four makes the statement **formally invalid** — this is the
minimum table structure the generated Word document must always contain, per cost
type, per tenant.

## 7. Deadline (§ 556 Abs. 3 BGB) — Ausschlussfrist

- The Abrechnung must **reach the tenant by 31 December** of the year following the
  billing period end (e.g. billing period 2026 → must arrive by 2027-12-31).
- Missing the deadline, or the statement being formally defective in a way not later
  cured, **forfeits the landlord's right to claim a Nachzahlung** (but a tenant
  credit/Guthaben must still be refunded — the exclusion is one-sided).
- Exception: landlord not at fault for the delay (rare, narrowly applied).
- **Product implication:** the bot/scheduler should track and surface the
  per-property deadline (billing period end + 12 months) so the landlord is warned
  well before the cutoff, not just able to generate a statement on demand.

## 8. Other rules the data model and generator must support

- **Pro-rata for partial-period tenancies**: a tenant who moved in/out mid-year gets
  their cost share time-prorated (typically per day) over the days they occupied the
  unit within the billing period — contract start/end dates are required inputs, and
  the engine must compute per-day or per-month proration in code.
- **Vacancy (Leerstand)**: cost shares attributable to vacant units during the period
  are **not** redistributed onto other tenants — they stay with the landlord. The
  engine must exclude vacant-unit periods from the shared pool's tenant-side total,
  not silently divide "occupied Wohnfläche" costs across all units.
- **Belegeinsicht**: tenants have a statutory right to inspect the underlying invoices
  for a statement. Practical implication: every invoice scan/record needs to stay
  retrievable and linked to the specific Abrechnung line it fed, by property and
  billing year.
- **Required document contents beyond the 4 BGH minimums** (best practice, keeps
  statements audit-proof): landlord name/address, tenant name/address, property
  address, billing period start/end, unit identifier, Wohnfläche of unit vs. total
  building Wohnfläche, and — if HeizkostenV items are included — the consumption
  values and meter IDs feeding the calculation.

## Sources

- [Betriebskostenverordnung (BetrKV) Aktuelle Fassung 2026](https://deutschesmietrecht.de/betriebskostenverordnung/11-betriebskostenverordnung.html)
- [Betriebskostenabrechnung 2026: Pflichtangaben, Fristen & Praxisbeispiel](https://www.myinvest24.de/ratgeber/nebenkosten/betriebskostenabrechnung/)
- [Betriebskostenabrechnung 2026: Alle 17 Positionen + Checkliste](https://vermieter1.de/blog/betriebskostenabrechnung-handbuch-vermieter)
- [BGH: Formelle Anforderungen Betriebskostenabrechnung](https://www.jenckel-skrobek.de/aktuelles/bgh-formelle-anforderungen--295/)
- [Anforderungen an eine Betriebskostenabrechnung](https://www.steuertipps.de/altersvorsorge-rente-finanzen/anforderungen-an-eine-betriebskostenabrechnung)
- [Heizkostenverordnung (HeizkostenV), Gesetze im Internet](https://www.gesetze-im-internet.de/heizkostenv/BJNR002610981.html)
- [Heizkostenabrechnung: Aufteilung von Grundkosten und Verbrauchskosten](https://www.mietrecht.org/heizkosten/heizkostenabrechnung-aufteilung-von-grundkosten-und-verbrauchskosten/)
- [Heizkostenverordnung 2026: HeizKV richtig anwenden](https://www.vivi-immo.de/blog-detail/heizkostenverordnung-heizkv-richtig-aufteilen.html)
- [CO2-Kostenaufteilung 2026: Stufenmodell erklärt](https://www.mein-nebenkostenrechner.de/ratgeber/co2-kostenaufteilung-erklaert)
- [CO₂-Kostenaufteilung 2026: Wer zahlt wie viel?](https://www.vivi-immo.de/blog-detail/co2-kostenaufteilung-2026-vermieter-mieter.html)
- [CO2-Steuer WEG 2026: Aufteilung, Abrechnung, Stufenmodell](https://www.weg-wissen.de/co2-steuer-weg-2026-aufteilung-abrechnung-stufenmodell/)
