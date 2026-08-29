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
    return COST_TYPES[BetrKVCostType(code)].label_de
