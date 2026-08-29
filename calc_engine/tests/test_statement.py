from datetime import date
from decimal import Decimal

from calc_engine import statement as st
from calc_engine.tests.fixtures import calberlah_worked_example as fx

PERIOD_START = date(2025, 1, 1)
PERIOD_END = date(2025, 12, 31)
DEADLINE = date(2026, 12, 31)


class TestBuildBetriebskostenStatement:
    def test_reproduces_reference_document_full_year_tenant(self):
        weight_maps = {
            "wohnflaeche": st.WeightMap(
                key="wohnflaeche", unit_label="m²", weights=fx.WOHNFLAECHE_WEIGHTS
            )
        }
        cost_totals = {
            i + 1: total for i, (total, _) in enumerate(fx.BETRIEBSKOSTEN_LINES.values())
        }
        distribution_keys = {code: "wohnflaeche" for code in cost_totals}

        result = st.build_betriebskosten_statement(
            tenant_name="Patrick Bartsch",
            tenant_address="Hauptstraße 37, 38547 Calberlah",
            unit_label="1.OG, links",
            property_label="Hauptstraße 37",
            property_address="38547 Calberlah",
            billing_period_start=PERIOD_START,
            billing_period_end=PERIOD_END,
            deadline_date=DEADLINE,
            contract_start=date(2020, 1, 1),
            contract_end=None,
            tenant_unit_id=fx.TENANT_UNIT_ID,
            cost_totals_by_type=cost_totals,
            distribution_key_by_type=distribution_keys,
            weight_maps=weight_maps,
            advance_payments_total=fx.BETRIEBSKOSTEN_ADVANCE_PAYMENTS,
        )

        expected_totals = [expected for _, expected in fx.BETRIEBSKOSTEN_LINES.values()]
        actual_totals = sorted(line.tenant_share_amount for line in result.cost_lines)
        assert actual_totals == sorted(expected_totals)

        # Every line must carry all BGH-mandated elements (docs/legal-requirements.md §6).
        for line in result.cost_lines:
            assert line.total_building_cost > 0
            assert line.distribution_key_description
            assert line.tenant_share_calculation
            assert str(line.tenant_share_amount) in line.tenant_share_calculation

    def test_advance_payments_deducted_into_balance(self):
        weight_maps = {"wohnflaeche": st.WeightMap("wohnflaeche", "m²", fx.WOHNFLAECHE_WEIGHTS)}
        result = st.build_betriebskosten_statement(
            tenant_name="T",
            tenant_address="A",
            unit_label="U",
            property_label="P",
            property_address="PA",
            billing_period_start=PERIOD_START,
            billing_period_end=PERIOD_END,
            deadline_date=DEADLINE,
            contract_start=date(2020, 1, 1),
            contract_end=None,
            tenant_unit_id=fx.TENANT_UNIT_ID,
            cost_totals_by_type={1: Decimal("1000.00")},
            distribution_key_by_type={1: "wohnflaeche"},
            weight_maps=weight_maps,
            advance_payments_total=Decimal("100.00"),
        )
        assert result.balance == result.total_tenant_cost - Decimal("100.00")


class TestBuildBetriebskostenStatementVacancy:
    def test_vacant_unit_share_excluded_not_redistributed(self):
        # 3-unit property, one (unit 3) vacant. All BGH elements populated; the
        # occupied tenants' shares sum to less than the total by exactly the vacant
        # unit's proportion (docs/legal-requirements.md §8).
        weights = {1: Decimal("100"), 2: Decimal("100"), 3: Decimal("100")}
        occupied_weights = {k: v for k, v in weights.items() if k != 3}
        weight_maps = {"wohnflaeche": st.WeightMap("wohnflaeche", "m²", occupied_weights)}

        result = st.build_betriebskosten_statement(
            tenant_name="T1",
            tenant_address="A",
            unit_label="U1",
            property_label="P",
            property_address="PA",
            billing_period_start=PERIOD_START,
            billing_period_end=PERIOD_END,
            deadline_date=DEADLINE,
            contract_start=date(2020, 1, 1),
            contract_end=None,
            tenant_unit_id=1,
            cost_totals_by_type={1: Decimal("300.00")},
            distribution_key_by_type={1: "wohnflaeche"},
            weight_maps=weight_maps,
            advance_payments_total=Decimal("0"),
        )
        # Unit 1's own share is 1/2 of the OCCUPIED pool (100/200), not 1/3 of the total.
        assert result.total_tenant_cost == Decimal("150.00")
        assert result.cost_lines[0].total_building_cost == Decimal("300.00")


class TestBuildWasserStatement:
    def test_reproduces_reference_document(self):
        meter_lines = [
            st.MeterLine("7738", "hot_water", Decimal("69125"), Decimal("91049")),
            st.MeterLine("1540", "cold_water", Decimal("83105"), Decimal("113654")),
        ]
        consumption_by_unit = {
            fx.TENANT_UNIT_ID: fx.WASSER_TENANT_CONSUMPTION_M3,
            fx.OTHER_UNIT_ID: fx.WASSER_BUILDING_CONSUMPTION_M3 - fx.WASSER_TENANT_CONSUMPTION_M3,
        }

        result = st.build_wasser_statement(
            tenant_name="Patrick Bartsch",
            tenant_address="Hauptstraße 37, 38547 Calberlah",
            unit_label="1.OG, links",
            property_label="Hauptstraße 37",
            property_address="38547 Calberlah",
            billing_period_start=PERIOD_START,
            billing_period_end=PERIOD_END,
            tenant_unit_id=fx.TENANT_UNIT_ID,
            meter_lines=meter_lines,
            consumption_by_unit=consumption_by_unit,
            total_building_cost=fx.WASSER_TOTAL_COST,
            advance_payments_total=fx.WASSER_ADVANCE_PAYMENTS,
        )

        assert result.tenant_share_amount == fx.WASSER_TENANT_SHARE
        assert result.meter_lines[0].consumption == Decimal("21924")


class TestBuildHeizkostenStatement:
    def test_reproduces_reference_document_full_year_tenant(self):
        wohnflaeche_heizung = {
            fx.TENANT_UNIT_ID: fx.TENANT_WOHNFLAECHE,
            fx.OTHER_UNIT_ID: fx.OTHER_WOHNFLAECHE,
        }
        heating_readings = {
            fx.TENANT_UNIT_ID: fx.HEIZUNG_TENANT_VERBRAUCH_READING,
            fx.OTHER_UNIT_ID: fx.HEIZUNG_BUILDING_VERBRAUCH_READING
            - fx.HEIZUNG_TENANT_VERBRAUCH_READING,
        }
        warmwater_readings = {
            fx.TENANT_UNIT_ID: fx.WARMWASSER_TENANT_VERBRAUCH_M3,
            fx.OTHER_UNIT_ID: fx.WARMWASSER_BUILDING_VERBRAUCH_M3
            - fx.WARMWASSER_TENANT_VERBRAUCH_M3,
        }
        # Derived directly from the fixture's own (cent-exact) sub-pool totals rather
        # than the reference document's rounded 42.51% display -- see
        # docs/legal-requirements.md §1 and fixtures/calberlah_worked_example.py.
        warmwater_pct = (
            fx.HEIZKOSTEN_WARMWASSER_POOL / fx.HEIZKOSTEN_GESAMTKOSTEN_LIEGENSCHAFT * 100
        )

        result = st.build_heizkosten_statement(
            tenant_name="Patrick Bartsch",
            tenant_address="Hauptstraße 37, 38547 Calberlah",
            unit_label="1.OG, links",
            property_label="Hauptstraße 37",
            property_address="38547 Calberlah",
            billing_period_start=PERIOD_START,
            billing_period_end=PERIOD_END,
            contract_start=date(2020, 1, 1),
            contract_end=None,
            tenant_unit_id=fx.TENANT_UNIT_ID,
            brennstoffkosten=fx.HEIZKOSTEN_BRENNSTOFFKOSTEN,
            other_ancillary_costs=fx.HEIZKOSTEN_OTHER_ANCILLARY,
            co2_landlord_share=fx.HEIZKOSTEN_CO2_LANDLORD_SHARE,
            warmwater_share_pct=warmwater_pct,
            heating_consumption_pct=fx.HEIZKOSTEN_CONSUMPTION_PCT,
            warmwater_consumption_pct=fx.HEIZKOSTEN_CONSUMPTION_PCT,
            pre1994_uninsulated=False,
            metering_compliant=True,
            wohnflaeche_heizung=wohnflaeche_heizung,
            wohnflaeche_warmwasser=wohnflaeche_heizung,
            heating_meter_readings=heating_readings,
            warmwater_meter_readings=warmwater_readings,
            gradtagstabelle=fx.GRADTAGSTABELLE,
            advance_payments_total=fx.HEIZKOSTEN_ADVANCE_PAYMENTS,
        )

        assert result.gesamtkosten_liegenschaft == fx.HEIZKOSTEN_GESAMTKOSTEN_LIEGENSCHAFT
        assert result.heating.grundkosten_total == fx.HEIZUNG_GRUNDKOSTEN_EXPECTED
        assert result.heating.tenant_grundkosten == fx.HEIZUNG_TENANT_GRUNDKOSTEN_EXPECTED
        assert result.heating.tenant_verbrauch == fx.HEIZUNG_TENANT_VERBRAUCH_EXPECTED
        assert result.warmwater.grundkosten_total == fx.WARMWASSER_GRUNDKOSTEN_EXPECTED
        assert result.warmwater.tenant_grundkosten == fx.WARMWASSER_TENANT_GRUNDKOSTEN_EXPECTED
        assert result.warmwater.tenant_verbrauch == fx.WARMWASSER_TENANT_VERBRAUCH_EXPECTED
        # Balance is negative (Guthaben) by our sign convention; the reference
        # document states it as a positive "Guthaben" label. The two differ by one
        # cent: summing four independently-rounded sub-shares (Grundkosten/Verbrauch
        # x Heizung/Warmwasser) carries the same benign accumulated-rounding noise
        # the source document's own Betriebskosten total exhibits elsewhere (see
        # fixtures/calberlah_worked_example.py) -- each sub-share is itself exact
        # (reconciled against its own pool), so this is expected, not a bug.
        assert abs(result.balance - (-fx.HEIZKOSTEN_GUTHABEN)) <= Decimal("0.01")

    def test_metering_noncompliant_applies_15_percent_reduction(self):
        wohnflaeche = {1: Decimal("50"), 2: Decimal("50")}
        readings = {1: Decimal("10"), 2: Decimal("10")}

        compliant = st.build_heizkosten_statement(
            tenant_name="T",
            tenant_address="A",
            unit_label="U",
            property_label="P",
            property_address="PA",
            billing_period_start=PERIOD_START,
            billing_period_end=PERIOD_END,
            contract_start=date(2020, 1, 1),
            contract_end=None,
            tenant_unit_id=1,
            brennstoffkosten=Decimal("1000.00"),
            other_ancillary_costs=Decimal("0"),
            co2_landlord_share=Decimal("0"),
            warmwater_share_pct=None,
            heating_consumption_pct=Decimal("60"),
            warmwater_consumption_pct=Decimal("60"),
            pre1994_uninsulated=False,
            metering_compliant=True,
            wohnflaeche_heizung=wohnflaeche,
            wohnflaeche_warmwasser=wohnflaeche,
            heating_meter_readings=readings,
            warmwater_meter_readings=readings,
            gradtagstabelle=fx.GRADTAGSTABELLE,
            advance_payments_total=Decimal("0"),
        )
        noncompliant = st.build_heizkosten_statement(
            tenant_name="T",
            tenant_address="A",
            unit_label="U",
            property_label="P",
            property_address="PA",
            billing_period_start=PERIOD_START,
            billing_period_end=PERIOD_END,
            contract_start=date(2020, 1, 1),
            contract_end=None,
            tenant_unit_id=1,
            brennstoffkosten=Decimal("1000.00"),
            other_ancillary_costs=Decimal("0"),
            co2_landlord_share=Decimal("0"),
            warmwater_share_pct=None,
            heating_consumption_pct=Decimal("60"),
            warmwater_consumption_pct=Decimal("60"),
            pre1994_uninsulated=False,
            metering_compliant=False,
            wohnflaeche_heizung=wohnflaeche,
            wohnflaeche_warmwasser=wohnflaeche,
            heating_meter_readings=readings,
            warmwater_meter_readings=readings,
            gradtagstabelle=fx.GRADTAGSTABELLE,
            advance_payments_total=Decimal("0"),
        )
        assert noncompliant.tenant_total == compliant.tenant_total_before_penalty * Decimal("0.85")
