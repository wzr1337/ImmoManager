from decimal import Decimal

import pytest

from calc_engine import heizkostenv
from calc_engine.tests.fixtures import calberlah_worked_example as fx


class TestSplitGrundkostenVerbrauch:
    def test_matches_reference_document_grundkosten(self):
        grundkosten, _ = heizkostenv.split_grundkosten_verbrauch(
            fx.HEIZKOSTEN_HEIZUNG_POOL, fx.HEIZKOSTEN_CONSUMPTION_PCT, pre1994_uninsulated=False
        )
        assert grundkosten == fx.HEIZUNG_GRUNDKOSTEN_EXPECTED

    def test_reconciled_split_sums_exactly_to_pool(self):
        # The source document's own two figures sum to one cent MORE than the pool
        # (rounding noise already present in the source, see fixtures docstring) --
        # our engine reconciles instead, so grundkosten + verbrauch always == pool.
        grundkosten, verbrauch = heizkostenv.split_grundkosten_verbrauch(
            fx.HEIZKOSTEN_HEIZUNG_POOL, fx.HEIZKOSTEN_CONSUMPTION_PCT, pre1994_uninsulated=False
        )
        assert grundkosten + verbrauch == fx.HEIZKOSTEN_HEIZUNG_POOL
        assert verbrauch == fx.HEIZUNG_VERBRAUCH_RECONCILED

    def test_rejects_ratio_outside_legal_band(self):
        with pytest.raises(ValueError):
            heizkostenv.split_grundkosten_verbrauch(
                Decimal("1000"), Decimal("40"), pre1994_uninsulated=False
            )
        with pytest.raises(ValueError):
            heizkostenv.split_grundkosten_verbrauch(
                Decimal("1000"), Decimal("80"), pre1994_uninsulated=False
            )

    def test_pre1994_uninsulated_forces_70_30_regardless_of_configured_ratio(self):
        grundkosten, verbrauch = heizkostenv.split_grundkosten_verbrauch(
            Decimal("1000.00"), Decimal("55"), pre1994_uninsulated=True
        )
        assert verbrauch == Decimal("700.00")
        assert grundkosten == Decimal("300.00")

    def test_boundary_values_50_and_70_accepted(self):
        heizkostenv.split_grundkosten_verbrauch(
            Decimal("1000"), Decimal("50"), pre1994_uninsulated=False
        )
        heizkostenv.split_grundkosten_verbrauch(
            Decimal("1000"), Decimal("70"), pre1994_uninsulated=False
        )


class TestApportionConsumptionPool:
    def test_matches_reference_document_heizung_verbrauch(self):
        shares = heizkostenv.apportion_consumption_pool(
            fx.HEIZUNG_VERBRAUCH_RECONCILED,
            {
                fx.TENANT_UNIT_ID: fx.HEIZUNG_TENANT_VERBRAUCH_READING,
                fx.OTHER_UNIT_ID: fx.HEIZUNG_BUILDING_VERBRAUCH_READING
                - fx.HEIZUNG_TENANT_VERBRAUCH_READING,
            },
        )
        assert shares[fx.TENANT_UNIT_ID] == fx.HEIZUNG_TENANT_VERBRAUCH_EXPECTED

    def test_matches_reference_document_warmwasser_verbrauch(self):
        warmwasser_grundkosten, warmwasser_verbrauch = heizkostenv.split_grundkosten_verbrauch(
            fx.HEIZKOSTEN_WARMWASSER_POOL, fx.HEIZKOSTEN_CONSUMPTION_PCT, pre1994_uninsulated=False
        )
        assert warmwasser_grundkosten == fx.WARMWASSER_GRUNDKOSTEN_EXPECTED

        shares = heizkostenv.apportion_consumption_pool(
            warmwasser_verbrauch,
            {
                fx.TENANT_UNIT_ID: fx.WARMWASSER_TENANT_VERBRAUCH_M3,
                fx.OTHER_UNIT_ID: fx.WARMWASSER_BUILDING_VERBRAUCH_M3
                - fx.WARMWASSER_TENANT_VERBRAUCH_M3,
            },
        )
        assert shares[fx.TENANT_UNIT_ID] == fx.WARMWASSER_TENANT_VERBRAUCH_EXPECTED


class TestMeteringPenalty:
    def test_compliant_metering_no_change(self):
        assert heizkostenv.apply_metering_penalty(
            Decimal("100.00"), metering_compliant=True
        ) == Decimal("100.00")

    def test_noncompliant_metering_reduces_by_15_percent(self):
        assert heizkostenv.apply_metering_penalty(
            Decimal("100.00"), metering_compliant=False
        ) == Decimal("85.00")


class TestSplitCombinedSystem:
    def test_sums_to_total(self):
        heating, warmwater = heizkostenv.split_combined_system(Decimal("4206.37"), Decimal("42.51"))
        assert heating + warmwater == Decimal("4206.37")

    def test_rejects_out_of_range_percentage(self):
        with pytest.raises(ValueError):
            heizkostenv.split_combined_system(Decimal("100"), Decimal("150"))
