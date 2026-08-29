from decimal import Decimal

import pytest

from calc_engine.apportionment import apportion_by_weights
from calc_engine.tests.fixtures import calberlah_worked_example as fx


class TestRoundingInvariant:
    """The single highest-value test in the suite: sum(shares) must equal total
    exactly, to the cent, regardless of how individual shares round."""

    @pytest.mark.parametrize(
        "total,weights",
        [
            (Decimal("100.00"), {1: Decimal("1"), 2: Decimal("1"), 3: Decimal("1")}),
            (Decimal("100.00"), {1: Decimal("1"), 2: Decimal("2")}),
            (Decimal("1207.28"), {1: Decimal("93"), 2: Decimal("437")}),
            (Decimal("0.01"), {1: Decimal("1"), 2: Decimal("1"), 3: Decimal("1")}),
            (Decimal("999999.99"), {i: Decimal(i) for i in range(1, 13)}),
            (Decimal("2418.19"), {1: Decimal("30"), 2: Decimal("70")}),
        ],
    )
    def test_sum_matches_total_exactly(self, total, weights):
        shares = apportion_by_weights(total, weights)
        assert sum(shares.values()) == total

    def test_zero_weight_recipient_gets_zero(self):
        shares = apportion_by_weights(Decimal("100.00"), {1: Decimal("1"), 2: Decimal("0")})
        assert shares[2] == Decimal("0.00")
        assert shares[1] == Decimal("100.00")

    def test_negative_weight_rejected(self):
        with pytest.raises(ValueError):
            apportion_by_weights(Decimal("100.00"), {1: Decimal("-1"), 2: Decimal("1")})

    def test_all_zero_weights_rejected(self):
        with pytest.raises(ValueError):
            apportion_by_weights(Decimal("100.00"), {1: Decimal("0"), 2: Decimal("0")})

    def test_empty_weights_returns_empty(self):
        assert apportion_by_weights(Decimal("100.00"), {}) == {}


class TestCalberlahBetriebskosten:
    """Every line reproduces the real reference document's tenant share exactly."""

    @pytest.mark.parametrize("name", list(fx.BETRIEBSKOSTEN_LINES.keys()))
    def test_line_matches_reference_document(self, name):
        total_cost, expected_tenant_share = fx.BETRIEBSKOSTEN_LINES[name]
        shares = apportion_by_weights(total_cost, fx.WOHNFLAECHE_WEIGHTS)
        assert shares[fx.TENANT_UNIT_ID] == expected_tenant_share
