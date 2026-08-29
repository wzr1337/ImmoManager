"""Assembles the three per-tenant statement documents from calc_engine primitives.

Pure data-in/data-out — no DB or filesystem I/O. The caller (db/repositories + a
future scripts/run_billing.py) is responsible for gathering cost entries, meter
readings, and contract dates from SQLite and handing them to these builders.

Each CostTypeLine carries all four BGH formal-correctness elements
(docs/legal-requirements.md §6): total building cost, the distribution key used,
the arithmetic producing the tenant's share, and (at the statement level) the
advance payments deducted. tenant_share_calculation is always built as an f-string
from the exact same Decimal values feeding tenant_share_amount, so the two can never
drift apart.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from calc_engine import co2kostaufg, heizkostenv, proration
from calc_engine.apportionment import apportion_by_weights
from config.cost_types import label_for


@dataclass(frozen=True)
class WeightMap:
    """A distribution key's per-unit weights for one property, covering EVERY unit
    (occupied or vacant) — this is the denominator the standard formula uses
    regardless of occupancy. Vacancy is handled by dropping a unit's *computed
    share* afterwards (see calc_engine/vacancy.py), never by removing its weight
    beforehand, which would incorrectly redistribute its cost onto other tenants."""

    key: str  # 'wohnflaeche' | 'personenzahl' | 'stueck' | 'verbrauch' | 'mea' | 'custom'
    unit_label: str  # display unit, e.g. "m²", "Personen", "Stück"
    weights: dict[int, Decimal]  # unit_id -> weight


@dataclass(frozen=True)
class CostTypeLine:
    cost_type_code: int
    cost_type_name: str
    total_building_cost: Decimal
    distribution_key_description: str
    tenant_share_calculation: str
    tenant_share_amount: Decimal


@dataclass(frozen=True)
class BetriebskostenStatement:
    tenant_name: str
    tenant_address: str
    unit_label: str
    property_label: str
    property_address: str
    billing_period_start: date
    billing_period_end: date
    deadline_date: date
    cost_lines: list[CostTypeLine]
    total_tenant_cost: Decimal
    advance_payments_total: Decimal
    balance: Decimal  # positive = Nachzahlung, negative = Guthaben


def build_betriebskosten_statement(
    *,
    tenant_name: str,
    tenant_address: str,
    unit_label: str,
    property_label: str,
    property_address: str,
    billing_period_start: date,
    billing_period_end: date,
    deadline_date: date,
    contract_start: date,
    contract_end: date | None,
    tenant_unit_id: int,
    cost_totals_by_type: dict[int, Decimal],  # cost_type_code -> total_building_cost for the year
    distribution_key_by_type: dict[
        int, str
    ],  # cost_type_code -> resolved key (contract override or property default)
    weight_maps: dict[str, WeightMap],  # distribution key -> WeightMap
    advance_payments_total: Decimal,
) -> BetriebskostenStatement:
    occupied, total_period_days = proration.occupied_days(
        billing_period_start, billing_period_end, contract_start, contract_end
    )

    lines: list[CostTypeLine] = []
    for cost_type_code, total_cost in cost_totals_by_type.items():
        key = distribution_key_by_type[cost_type_code]
        weight_map = weight_maps[key]
        full_period_shares = apportion_by_weights(total_cost, weight_map.weights)
        tenant_full_share = full_period_shares[tenant_unit_id]
        tenant_share = proration.prorate_flat(tenant_full_share, occupied, total_period_days)

        total_weight = sum(weight_map.weights.values())
        tenant_weight = weight_map.weights[tenant_unit_id]
        calculation = (
            f"{total_cost:.2f} € : {total_weight} {weight_map.unit_label} "
            f"x {tenant_weight} {weight_map.unit_label} : {total_period_days} Tage "
            f"x {occupied} Tage = {tenant_share:.2f} €"
        )

        lines.append(
            CostTypeLine(
                cost_type_code=cost_type_code,
                cost_type_name=label_for(cost_type_code),
                total_building_cost=total_cost,
                distribution_key_description=f"{weight_map.key} ({weight_map.unit_label})",
                tenant_share_calculation=calculation,
                tenant_share_amount=tenant_share,
            )
        )

    total_tenant_cost = sum((line.tenant_share_amount for line in lines), Decimal(0))
    balance = total_tenant_cost - advance_payments_total

    return BetriebskostenStatement(
        tenant_name=tenant_name,
        tenant_address=tenant_address,
        unit_label=unit_label,
        property_label=property_label,
        property_address=property_address,
        billing_period_start=billing_period_start,
        billing_period_end=billing_period_end,
        deadline_date=deadline_date,
        cost_lines=lines,
        total_tenant_cost=total_tenant_cost,
        advance_payments_total=advance_payments_total,
        balance=balance,
    )


@dataclass(frozen=True)
class MeterLine:
    meter_id: str
    meter_type: str
    reading_old: Decimal
    reading_new: Decimal

    @property
    def consumption(self) -> Decimal:
        return self.reading_new - self.reading_old


@dataclass(frozen=True)
class WasserStatement:
    tenant_name: str
    tenant_address: str
    unit_label: str
    property_label: str
    property_address: str
    billing_period_start: date
    billing_period_end: date
    meter_lines: list[MeterLine]
    tenant_consumption_total: Decimal
    building_consumption_total: Decimal
    total_building_cost: Decimal
    tenant_share_calculation: str
    tenant_share_amount: Decimal
    advance_payments_total: Decimal
    balance: Decimal


def build_wasser_statement(
    *,
    tenant_name: str,
    tenant_address: str,
    unit_label: str,
    property_label: str,
    property_address: str,
    billing_period_start: date,
    billing_period_end: date,
    tenant_unit_id: int,
    meter_lines: list[MeterLine],
    consumption_by_unit: dict[int, Decimal],  # unit_id -> combined kalt+warm m3 for the year
    total_building_cost: Decimal,  # Gesamtverbrauchskosten + Abrechnungskosten + Zaehlermiete
    advance_payments_total: Decimal,
) -> WasserStatement:
    shares = apportion_by_weights(total_building_cost, consumption_by_unit)
    tenant_share = shares[tenant_unit_id]
    building_total = sum(consumption_by_unit.values())
    tenant_consumption = consumption_by_unit[tenant_unit_id]

    calculation = (
        f"{total_building_cost:.2f} € : {building_total} m³ "
        f"x {tenant_consumption} m³ = {tenant_share:.2f} €"
    )

    return WasserStatement(
        tenant_name=tenant_name,
        tenant_address=tenant_address,
        unit_label=unit_label,
        property_label=property_label,
        property_address=property_address,
        billing_period_start=billing_period_start,
        billing_period_end=billing_period_end,
        meter_lines=meter_lines,
        tenant_consumption_total=tenant_consumption,
        building_consumption_total=building_total,
        total_building_cost=total_building_cost,
        tenant_share_calculation=calculation,
        tenant_share_amount=tenant_share,
        advance_payments_total=advance_payments_total,
        balance=tenant_share - advance_payments_total,
    )


@dataclass(frozen=True)
class HeizkostenPoolResult:
    grundkosten_total: Decimal
    verbrauch_total: Decimal
    tenant_grundkosten: Decimal
    tenant_verbrauch: Decimal
    grundkosten_calculation: str
    verbrauch_calculation: str


@dataclass(frozen=True)
class HeizkostenStatement:
    tenant_name: str
    tenant_address: str
    unit_label: str
    property_label: str
    property_address: str
    billing_period_start: date
    billing_period_end: date
    gesamtkosten_liegenschaft: Decimal
    co2_landlord_share: Decimal
    heating: HeizkostenPoolResult
    warmwater: HeizkostenPoolResult | None
    metering_compliant: bool
    tenant_total_before_penalty: Decimal
    tenant_total: Decimal
    advance_payments_total: Decimal
    balance: Decimal


def build_heizkosten_statement(
    *,
    tenant_name: str,
    tenant_address: str,
    unit_label: str,
    property_label: str,
    property_address: str,
    billing_period_start: date,
    billing_period_end: date,
    contract_start: date,
    contract_end: date | None,
    tenant_unit_id: int,
    brennstoffkosten: Decimal,
    other_ancillary_costs: Decimal,
    co2_landlord_share: Decimal,
    warmwater_share_pct: Decimal | None,  # None => separately metered, no combined-system split
    heating_consumption_pct: Decimal,
    warmwater_consumption_pct: Decimal,
    pre1994_uninsulated: bool,
    metering_compliant: bool,
    wohnflaeche_heizung: dict[int, Decimal],
    wohnflaeche_warmwasser: dict[int, Decimal],
    heating_meter_readings: dict[int, Decimal],
    warmwater_meter_readings: dict[int, Decimal],
    gradtagstabelle: dict[int, Decimal],
    advance_payments_total: Decimal,
) -> HeizkostenStatement:
    gesamtkosten_liegenschaft = (
        co2kostaufg.deduct_landlord_co2_share(brennstoffkosten, co2_landlord_share)
        + other_ancillary_costs
    )

    if warmwater_share_pct is not None:
        heizkosten_pool, warmwasser_pool = heizkostenv.split_combined_system(
            gesamtkosten_liegenschaft, warmwater_share_pct
        )
    else:
        heizkosten_pool, warmwasser_pool = gesamtkosten_liegenschaft, None

    tenant_anteile, total_anteile = proration.gradtag_anteile(
        billing_period_start, billing_period_end, contract_start, contract_end, gradtagstabelle
    )

    heating_result = _build_pool_result(
        pool=heizkosten_pool,
        consumption_pct=heating_consumption_pct,
        pre1994_uninsulated=pre1994_uninsulated,
        wohnflaeche=wohnflaeche_heizung,
        meter_readings=heating_meter_readings,
        tenant_unit_id=tenant_unit_id,
        prorate=lambda full_share: proration.prorate_gradtag(
            full_share, tenant_anteile, total_anteile
        ),
        grundkosten_unit_label=f"1000 A. ({tenant_anteile:g} von {total_anteile:g} Anteilen)",
    )

    warmwater_result: HeizkostenPoolResult | None = None
    if warmwasser_pool is not None:
        occupied_m, total_m = proration.occupied_months(
            billing_period_start, billing_period_end, contract_start, contract_end
        )
        warmwater_result = _build_pool_result(
            pool=warmwasser_pool,
            consumption_pct=warmwater_consumption_pct,
            pre1994_uninsulated=False,
            wohnflaeche=wohnflaeche_warmwasser,
            meter_readings=warmwater_meter_readings,
            tenant_unit_id=tenant_unit_id,
            prorate=lambda full_share: proration.prorate_flat(full_share, occupied_m, total_m),
            grundkosten_unit_label=f"{total_m} Monate x {occupied_m} Monate",
        )

    tenant_total_before_penalty = (
        heating_result.tenant_grundkosten + heating_result.tenant_verbrauch
    )
    if warmwater_result is not None:
        tenant_total_before_penalty += (
            warmwater_result.tenant_grundkosten + warmwater_result.tenant_verbrauch
        )

    tenant_total = heizkostenv.apply_metering_penalty(
        tenant_total_before_penalty, metering_compliant
    )

    return HeizkostenStatement(
        tenant_name=tenant_name,
        tenant_address=tenant_address,
        unit_label=unit_label,
        property_label=property_label,
        property_address=property_address,
        billing_period_start=billing_period_start,
        billing_period_end=billing_period_end,
        gesamtkosten_liegenschaft=gesamtkosten_liegenschaft,
        co2_landlord_share=co2_landlord_share,
        heating=heating_result,
        warmwater=warmwater_result,
        metering_compliant=metering_compliant,
        tenant_total_before_penalty=tenant_total_before_penalty,
        tenant_total=tenant_total,
        advance_payments_total=advance_payments_total,
        balance=tenant_total - advance_payments_total,
    )


def _build_pool_result(
    *,
    pool: Decimal,
    consumption_pct: Decimal,
    pre1994_uninsulated: bool,
    wohnflaeche: dict[int, Decimal],
    meter_readings: dict[int, Decimal],
    tenant_unit_id: int,
    prorate,
    grundkosten_unit_label: str,
) -> HeizkostenPoolResult:
    grundkosten_total, verbrauch_total = heizkostenv.split_grundkosten_verbrauch(
        pool, consumption_pct, pre1994_uninsulated
    )

    grundkosten_full_shares = apportion_by_weights(grundkosten_total, wohnflaeche)
    tenant_grundkosten_full = grundkosten_full_shares[tenant_unit_id]
    tenant_grundkosten = prorate(tenant_grundkosten_full)

    verbrauch_shares = heizkostenv.apportion_consumption_pool(verbrauch_total, meter_readings)
    tenant_verbrauch = verbrauch_shares[tenant_unit_id]

    total_wohnflaeche = sum(wohnflaeche.values())
    tenant_wohnflaeche = wohnflaeche[tenant_unit_id]
    total_verbrauch = sum(meter_readings.values())
    tenant_verbrauch_reading = meter_readings[tenant_unit_id]

    grundkosten_calc = (
        f"{grundkosten_total:.2f} € : {total_wohnflaeche} m² x {tenant_wohnflaeche} m² "
        f"; {grundkosten_unit_label} = {tenant_grundkosten:.2f} €"
    )
    verbrauch_calc = (
        f"{verbrauch_total:.2f} € : {total_verbrauch} Einh. x {tenant_verbrauch_reading} Einh. "
        f"= {tenant_verbrauch:.2f} €"
    )

    return HeizkostenPoolResult(
        grundkosten_total=grundkosten_total,
        verbrauch_total=verbrauch_total,
        tenant_grundkosten=tenant_grundkosten,
        tenant_verbrauch=tenant_verbrauch,
        grundkosten_calculation=grundkosten_calc,
        verbrauch_calculation=verbrauch_calc,
    )
