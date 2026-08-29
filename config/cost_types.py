"""§ 2 BetrKV apportionable cost types. See docs/legal-requirements.md §2."""

from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum


class BetrKVCostType(IntEnum):
    GRUNDSTEUER = 1
    WASSERVERSORGUNG = 2
    ENTWAESSERUNG = 3
    HEIZUNG = 4
    WARMWASSER = 5
    HEIZUNG_WARMWASSER_VERBUNDEN = 6
    AUFZUG = 7
    STRASSENREINIGUNG_MUELLABFUHR = 8
    GEBAEUDEREINIGUNG_UNGEZIEFERBEKAEMPFUNG = 9
    GARTENPFLEGE = 10
    BELEUCHTUNG = 11
    SCHORNSTEINREINIGUNG = 12
    SACH_HAFTPFLICHTVERSICHERUNG = 13
    HAUSWART = 14
    GEMEINSCHAFTS_ANTENNE_KABEL = 15
    WAESCHEPFLEGE = 16
    SONSTIGE_BETRIEBSKOSTEN = 17


@dataclass(frozen=True)
class CostTypeMeta:
    code: BetrKVCostType
    label_de: str
    # Heating/hot water cost types are billed via their own HeizkostenV-compliant
    # statement (calc_engine/heizkostenv.py), never via the generic apportionment
    # used for the other 15 positions.
    is_heating_related: bool = False
    # § 2 Nr. 17 BetrKV: "sonstige" costs are only apportionable if individually
    # named in the Mietvertrag (see property_sonstige_items table).
    requires_contract_naming: bool = False


COST_TYPES: dict[BetrKVCostType, CostTypeMeta] = {
    BetrKVCostType.GRUNDSTEUER: CostTypeMeta(BetrKVCostType.GRUNDSTEUER, "Grundsteuer"),
    BetrKVCostType.WASSERVERSORGUNG: CostTypeMeta(
        BetrKVCostType.WASSERVERSORGUNG, "Wasserversorgung"
    ),
    BetrKVCostType.ENTWAESSERUNG: CostTypeMeta(BetrKVCostType.ENTWAESSERUNG, "Entwässerung"),
    BetrKVCostType.HEIZUNG: CostTypeMeta(
        BetrKVCostType.HEIZUNG, "Heizung", is_heating_related=True
    ),
    BetrKVCostType.WARMWASSER: CostTypeMeta(
        BetrKVCostType.WARMWASSER, "Warmwasser", is_heating_related=True
    ),
    BetrKVCostType.HEIZUNG_WARMWASSER_VERBUNDEN: CostTypeMeta(
        BetrKVCostType.HEIZUNG_WARMWASSER_VERBUNDEN,
        "Heizung und Warmwasser (verbundene Anlage)",
        is_heating_related=True,
    ),
    BetrKVCostType.AUFZUG: CostTypeMeta(BetrKVCostType.AUFZUG, "Aufzug"),
    BetrKVCostType.STRASSENREINIGUNG_MUELLABFUHR: CostTypeMeta(
        BetrKVCostType.STRASSENREINIGUNG_MUELLABFUHR, "Straßenreinigung / Müllabfuhr"
    ),
    BetrKVCostType.GEBAEUDEREINIGUNG_UNGEZIEFERBEKAEMPFUNG: CostTypeMeta(
        BetrKVCostType.GEBAEUDEREINIGUNG_UNGEZIEFERBEKAEMPFUNG,
        "Gebäudereinigung / Ungezieferbekämpfung",
    ),
    BetrKVCostType.GARTENPFLEGE: CostTypeMeta(BetrKVCostType.GARTENPFLEGE, "Gartenpflege"),
    BetrKVCostType.BELEUCHTUNG: CostTypeMeta(BetrKVCostType.BELEUCHTUNG, "Beleuchtung"),
    BetrKVCostType.SCHORNSTEINREINIGUNG: CostTypeMeta(
        BetrKVCostType.SCHORNSTEINREINIGUNG, "Schornsteinreinigung"
    ),
    BetrKVCostType.SACH_HAFTPFLICHTVERSICHERUNG: CostTypeMeta(
        BetrKVCostType.SACH_HAFTPFLICHTVERSICHERUNG, "Sach- und Haftpflichtversicherung"
    ),
    BetrKVCostType.HAUSWART: CostTypeMeta(BetrKVCostType.HAUSWART, "Hauswart"),
    BetrKVCostType.GEMEINSCHAFTS_ANTENNE_KABEL: CostTypeMeta(
        BetrKVCostType.GEMEINSCHAFTS_ANTENNE_KABEL, "Gemeinschafts-Antenne / Kabel"
    ),
    BetrKVCostType.WAESCHEPFLEGE: CostTypeMeta(
        BetrKVCostType.WAESCHEPFLEGE, "Einrichtungen für die Wäschepflege"
    ),
    BetrKVCostType.SONSTIGE_BETRIEBSKOSTEN: CostTypeMeta(
        BetrKVCostType.SONSTIGE_BETRIEBSKOSTEN,
        "Sonstige Betriebskosten",
        requires_contract_naming=True,
    ),
}


def label_for(code: int) -> str:
    if is_apportionable_code(code):
        return COST_TYPES[BetrKVCostType(code)].label_de
    return NON_APPORTIONABLE_COST_TYPES[NichtUmlagefaehigCostType(code)].label_de


# Costs that must NOT enter a tenant's Abrechnung -- they stay with the landlord
# regardless of any distribution key (docs/legal-requirements.md §2: "Anything not
# on [the 17-position] list ... is not apportionable and stays with the landlord").
# Tracked for the landlord's own bookkeeping (expense records, tax purposes), never
# summed into calc_engine's cost_totals_by_type. Numbered from 101 to keep the code
# space visually distinct from the 1-17 BetrKV catalog at a glance.
class NichtUmlagefaehigCostType(IntEnum):
    INSTANDHALTUNG_REPARATUR = 101
    VERWALTUNGSKOSTEN = 102
    MODERNISIERUNG = 103
    LEERSTANDSKOSTEN = 104
    SONSTIGE_NICHT_UMLAGEFAEHIG = 105
    FINANZIERUNGSKOSTEN = 106
    BEWIRTUNGSKOSTEN = 107


NON_APPORTIONABLE_COST_TYPES: dict[NichtUmlagefaehigCostType, CostTypeMeta] = {
    NichtUmlagefaehigCostType.INSTANDHALTUNG_REPARATUR: CostTypeMeta(
        NichtUmlagefaehigCostType.INSTANDHALTUNG_REPARATUR, "Instandhaltung / Reparatur"
    ),
    NichtUmlagefaehigCostType.VERWALTUNGSKOSTEN: CostTypeMeta(
        NichtUmlagefaehigCostType.VERWALTUNGSKOSTEN, "Verwaltungskosten"
    ),
    NichtUmlagefaehigCostType.MODERNISIERUNG: CostTypeMeta(
        NichtUmlagefaehigCostType.MODERNISIERUNG, "Modernisierung"
    ),
    NichtUmlagefaehigCostType.LEERSTANDSKOSTEN: CostTypeMeta(
        NichtUmlagefaehigCostType.LEERSTANDSKOSTEN, "Leerstandskosten"
    ),
    NichtUmlagefaehigCostType.SONSTIGE_NICHT_UMLAGEFAEHIG: CostTypeMeta(
        NichtUmlagefaehigCostType.SONSTIGE_NICHT_UMLAGEFAEHIG, "Sonstige nicht umlagefähige Kosten"
    ),
    NichtUmlagefaehigCostType.FINANZIERUNGSKOSTEN: CostTypeMeta(
        NichtUmlagefaehigCostType.FINANZIERUNGSKOSTEN, "Finanzierungskosten (Zinsen)"
    ),
    NichtUmlagefaehigCostType.BEWIRTUNGSKOSTEN: CostTypeMeta(
        NichtUmlagefaehigCostType.BEWIRTUNGSKOSTEN, "Bewirtungskosten"
    ),
}


def is_apportionable_code(code: int) -> bool:
    return 1 <= code <= 17


def all_cost_type_choices() -> list[tuple[int, str, bool]]:
    """Returns (code, label, is_apportionable) for every known cost type — the
    combined list a UI (CLI or bot) should offer when categorizing an invoice."""
    choices = [(c.value, meta.label_de, True) for c, meta in COST_TYPES.items()]
    choices += [(c.value, meta.label_de, False) for c, meta in NON_APPORTIONABLE_COST_TYPES.items()]
    return choices
