"""Numbers transcribed from a real, professionally-produced compliant
Betriebskosten-/Wasser-/Heizkostenabrechnung ("Immobilienservice Thiele", Calberlah,
billing period 01.01.2025-31.12.2025) — see docs/legal-requirements.md §1. This is a
stronger fixture than any synthetic example: numbers a real accountant already
produced and the user already trusts, not values derived by running the code under
test (CLAUDE.md testing policy).

Property: Gesamtwohnfläche 530 m², tenant unit Wohnfläche 93 m², full 12-month
tenancy (period_start == contract_start, period_end == contract_end == None).

A synthetic second unit absorbs the remainder of each pool's total weight/consumption
(the source document only discloses one tenant's line, not the whole building's
unit-by-unit breakdown) so apportion_by_weights has a complete weight map to split
across, exactly as it would for a real multi-unit property.
"""

from decimal import Decimal

TENANT_UNIT_ID = 1
OTHER_UNIT_ID = 2

TOTAL_WOHNFLAECHE = Decimal("530")
TENANT_WOHNFLAECHE = Decimal("93")
OTHER_WOHNFLAECHE = TOTAL_WOHNFLAECHE - TENANT_WOHNFLAECHE

WOHNFLAECHE_WEIGHTS = {TENANT_UNIT_ID: TENANT_WOHNFLAECHE, OTHER_UNIT_ID: OTHER_WOHNFLAECHE}

# Betriebskostenabrechnung lines: (total_building_cost, expected_tenant_share).
# Excludes line 1 (Wasserversorgung — its own sub-statement, see WASSER_* below) and
# line 9 (Rauchmelder — billed as a fixed per-device rate, not a Wohnfläche split;
# a distinct distribution key not covered by this fixture).
BETRIEBSKOSTEN_LINES = {
    "muellentsorgung": (Decimal("1147.40"), Decimal("201.34")),
    "hauswart": (Decimal("494.00"), Decimal("86.68")),
    "grundsteuer": (Decimal("812.21"), Decimal("142.52")),
    "versicherung_gebaeude": (Decimal("964.89"), Decimal("169.31")),
    "versicherung_haftpflicht": (Decimal("68.84"), Decimal("12.08")),
    "allgemeine_stromkosten": (Decimal("77.38"), Decimal("13.58")),
    "gartenpflege": (Decimal("966.89"), Decimal("169.66")),
    "winterdienst": (Decimal("688.99"), Decimal("120.90")),
    "schaedlingsbekaempfung": (Decimal("229.02"), Decimal("40.19")),
}

BETRIEBSKOSTEN_ADVANCE_PAYMENTS = Decimal("1200.00")  # 100.00 x 12 Monate
BETRIEBSKOSTEN_NACHZAHLUNG = Decimal("-7.28")  # actually a Guthaben in the source's sign convention

# Wasserkostenabrechnung
WASSER_TENANT_CONSUMPTION_M3 = Decimal("52.473")  # 21.924 WW + 30.549 KW
WASSER_BUILDING_CONSUMPTION_M3 = Decimal("576.083")
WASSER_TOTAL_COST = Decimal(
    "2256.35"
)  # 2115.17 Verbrauchskosten + 87.12 Abrechnung + 54.06 Zaehlermiete
WASSER_TENANT_SHARE = Decimal("205.52")
WASSER_ADVANCE_PAYMENTS = Decimal("0")  # folded into the main Betriebskosten advance payment here

# Heizkostenabrechnung — combined heating+hot-water system.
HEIZKOSTEN_BRENNSTOFFKOSTEN = Decimal("2608.40")
HEIZKOSTEN_CO2_LANDLORD_SHARE = Decimal(
    "0.00"
)  # source example happens to be 0 — see co2kostaufg caveat
HEIZKOSTEN_OTHER_ANCILLARY = (
    Decimal("180.56") + Decimal("247.40") + Decimal("78.97") + Decimal("524.60") + Decimal("566.44")
)  # Betriebsstrom + Wartung/Reinigung + Emissionsmessung + Miete Messgeraete + Kosten Verbrauchsabrechnung
HEIZKOSTEN_GESAMTKOSTEN_LIEGENSCHAFT = Decimal("4206.37")

# The source document's displayed 57.49%/42.51% combined-system split is itself
# rounded for display (derived from a submeter, see docs/legal-requirements.md §1);
# reversing it via the rounded percentage doesn't reproduce the sub-pool totals to
# the cent. We use the sub-pool totals directly, as the source document states them,
# rather than re-deriving them from the rounded percentage.
HEIZKOSTEN_HEIZUNG_POOL = Decimal("2418.19")
HEIZKOSTEN_WARMWASSER_POOL = Decimal("1788.18")

HEIZKOSTEN_CONSUMPTION_PCT = Decimal("70")  # this landlord chose the max allowed 70/30 split

HEIZUNG_GRUNDKOSTEN_EXPECTED = Decimal("725.46")  # building-wide total (30% of the pool)
HEIZUNG_TENANT_GRUNDKOSTEN_EXPECTED = Decimal(
    "127.30"
)  # after Wohnfläche apportionment + Gradtag proration
# NOTE: the source document shows Verbrauchskosten Heizung as 1.692,74 EUR, which
# together with its own Grundkosten figure sums to 2418.20 EUR -- one cent MORE than
# the 2418.19 EUR pool being split. That's rounding noise already present in the
# source (each figure rounded independently without a global reconciliation pass).
# Our apportion_by_weights reconciles the residual cent onto the larger share
# instead, so our result is internally exact (grundkosten + verbrauch == pool) even
# though it differs from the source's Verbrauchskosten figure by one cent.
HEIZUNG_VERBRAUCH_RECONCILED = Decimal("1692.73")

HEIZUNG_TENANT_VERBRAUCH_READING = Decimal("1204")  # "Einh." (Heizkostenverteiler units)
HEIZUNG_BUILDING_VERBRAUCH_READING = Decimal("13008")
HEIZUNG_TENANT_VERBRAUCH_EXPECTED = Decimal("156.68")

WARMWASSER_GRUNDKOSTEN_EXPECTED = Decimal(
    "536.45"
)  # building-wide total (30% of the warmwater pool)
WARMWASSER_TENANT_GRUNDKOSTEN_EXPECTED = Decimal(
    "94.13"
)  # after Wohnfläche apportionment + month proration
WARMWASSER_TENANT_VERBRAUCH_M3 = Decimal("21.924")
WARMWASSER_BUILDING_VERBRAUCH_M3 = Decimal("171.38")
WARMWASSER_TENANT_VERBRAUCH_EXPECTED = Decimal("160.13")

HEIZKOSTEN_ADVANCE_PAYMENTS = Decimal("840.00")  # 70.00 x 12 Monate
HEIZKOSTEN_GUTHABEN = Decimal("301.77")

# Gradtagstabelle (1000-point annual degree-day table) from the source document.
GRADTAGSTABELLE = {
    1: Decimal("170"),
    2: Decimal("150"),
    3: Decimal("130"),
    4: Decimal("80"),
    5: Decimal("40"),
    6: Decimal("13.33"),
    7: Decimal("13.33"),
    8: Decimal("13.33"),
    9: Decimal("30"),
    10: Decimal("80"),
    11: Decimal("120"),
    12: Decimal("160"),
}
