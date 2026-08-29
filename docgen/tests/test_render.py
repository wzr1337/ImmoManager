from datetime import date
from pathlib import Path

from calc_engine import statement as st
from calc_engine.tests.fixtures import calberlah_worked_example as fx
from docgen import context_builder, render
from models.landlord import LandlordProfile

TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"
PERIOD_START = date(2025, 1, 1)
PERIOD_END = date(2025, 12, 31)
DEADLINE = date(2026, 12, 31)

LANDLORD = LandlordProfile(
    name="Wigand Thiele",
    street="Musterweg",
    house_number="1",
    postal_code="38547",
    city="Calberlah",
)


def _betriebskosten_statement():
    weight_maps = {"wohnflaeche": st.WeightMap("wohnflaeche", "m²", fx.WOHNFLAECHE_WEIGHTS)}
    cost_totals = {i + 1: total for i, (total, _) in enumerate(fx.BETRIEBSKOSTEN_LINES.values())}
    return st.build_betriebskosten_statement(
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
        distribution_key_by_type={code: "wohnflaeche" for code in cost_totals},
        weight_maps=weight_maps,
        advance_payments_total=fx.BETRIEBSKOSTEN_ADVANCE_PAYMENTS,
    )


class TestRenderBetriebskosten:
    def test_renders_without_unresolved_placeholders(self, tmp_path):
        context = context_builder.betriebskosten_context(_betriebskosten_statement(), LANDLORD)
        output = render.render_statement(
            template_path=TEMPLATES_DIR / "betriebskostenabrechnung.docx",
            context=context,
            output_dir=tmp_path,
            property_slug="hauptstr-37",
            unit_label="1.OG links",
            tenant_lastname="Bartsch",
            billing_year=2025,
            document_type="betriebskosten",
        )
        assert output.exists()

    def test_garage_variant_renders(self, tmp_path):
        context = context_builder.betriebskosten_context(_betriebskosten_statement(), LANDLORD)
        output = render.render_statement(
            template_path=TEMPLATES_DIR / "betriebskostenabrechnung_garage.docx",
            context=context,
            output_dir=tmp_path,
            property_slug="hauptstr-37",
            unit_label="Garage 1",
            tenant_lastname="Bartsch",
            billing_year=2025,
            document_type="betriebskosten",
        )
        assert output.exists()


class TestRenderWasser:
    def test_renders_without_unresolved_placeholders(self, tmp_path):
        meter_lines = [
            st.MeterLine("7738", "hot_water", fx_dec("69125"), fx_dec("91049")),
            st.MeterLine("1540", "cold_water", fx_dec("83105"), fx_dec("113654")),
        ]
        consumption_by_unit = {
            fx.TENANT_UNIT_ID: fx.WASSER_TENANT_CONSUMPTION_M3,
            fx.OTHER_UNIT_ID: fx.WASSER_BUILDING_CONSUMPTION_M3 - fx.WASSER_TENANT_CONSUMPTION_M3,
        }
        statement = st.build_wasser_statement(
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
        context = context_builder.wasser_context(statement, LANDLORD)
        output = render.render_statement(
            template_path=TEMPLATES_DIR / "wasserkostenabrechnung.docx",
            context=context,
            output_dir=tmp_path,
            property_slug="hauptstr-37",
            unit_label="1.OG links",
            tenant_lastname="Bartsch",
            billing_year=2025,
            document_type="wasser",
        )
        assert output.exists()


class TestRenderHeizkosten:
    def test_renders_without_unresolved_placeholders(self, tmp_path):
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
        warmwater_pct = (
            fx.HEIZKOSTEN_WARMWASSER_POOL / fx.HEIZKOSTEN_GESAMTKOSTEN_LIEGENSCHAFT * 100
        )

        statement = st.build_heizkosten_statement(
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
        context = context_builder.heizkosten_context(statement, LANDLORD)
        output = render.render_statement(
            template_path=TEMPLATES_DIR / "heizkostenabrechnung.docx",
            context=context,
            output_dir=tmp_path,
            property_slug="hauptstr-37",
            unit_label="1.OG links",
            tenant_lastname="Bartsch",
            billing_year=2025,
            document_type="heizkosten",
        )
        assert output.exists()

    def test_noncompliant_metering_still_renders(self, tmp_path):
        wohnflaeche = {1: fx_dec("50"), 2: fx_dec("50")}
        readings = {1: fx_dec("10"), 2: fx_dec("10")}
        statement = st.build_heizkosten_statement(
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
            brennstoffkosten=fx_dec("1000.00"),
            other_ancillary_costs=fx_dec("0"),
            co2_landlord_share=fx_dec("0"),
            warmwater_share_pct=None,
            heating_consumption_pct=fx_dec("60"),
            warmwater_consumption_pct=fx_dec("60"),
            pre1994_uninsulated=False,
            metering_compliant=False,
            wohnflaeche_heizung=wohnflaeche,
            wohnflaeche_warmwasser=wohnflaeche,
            heating_meter_readings=readings,
            warmwater_meter_readings=readings,
            gradtagstabelle=fx.GRADTAGSTABELLE,
            advance_payments_total=fx_dec("0"),
        )
        context = context_builder.heizkosten_context(statement, LANDLORD)
        output = render.render_statement(
            template_path=TEMPLATES_DIR / "heizkostenabrechnung.docx",
            context=context,
            output_dir=tmp_path,
            property_slug="p",
            unit_label="U",
            tenant_lastname="T",
            billing_year=2025,
            document_type="heizkosten",
        )
        assert output.exists()


def fx_dec(s: str):
    from decimal import Decimal

    return Decimal(s)
