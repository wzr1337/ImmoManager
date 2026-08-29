from decimal import Decimal

import pytest

from calc_engine import co2kostaufg


@pytest.fixture
def tiers():
    return co2kostaufg.load_tiers(2026)


class TestLoadTiers:
    def test_loads_ten_tiers(self, tiers):
        assert len(tiers) == 10
        assert {t.tier_number for t in tiers} == set(range(1, 11))

    def test_missing_year_raises(self):
        with pytest.raises(FileNotFoundError):
            co2kostaufg.load_tiers(1999)

    def test_top_tier_is_open_ended(self, tiers):
        top = next(t for t in tiers if t.tier_number == 10)
        assert top.co2_per_sqm_max is None
        assert top.landlord_pct == Decimal(95)


class TestLookupTier:
    def test_boundary_edges(self, tiers):
        # Off-by-one at tier boundaries is the classic bug here.
        assert co2kostaufg.lookup_tier(Decimal("11.99"), tiers).tier_number == 1
        assert co2kostaufg.lookup_tier(Decimal("12.00"), tiers).tier_number == 2
        assert co2kostaufg.lookup_tier(Decimal("16.99"), tiers).tier_number == 2
        assert co2kostaufg.lookup_tier(Decimal("17.00"), tiers).tier_number == 3
        assert co2kostaufg.lookup_tier(Decimal("51.99"), tiers).tier_number == 9
        assert co2kostaufg.lookup_tier(Decimal("52.00"), tiers).tier_number == 10
        assert co2kostaufg.lookup_tier(Decimal("500"), tiers).tier_number == 10
        assert co2kostaufg.lookup_tier(Decimal("0"), tiers).tier_number == 1

    def test_manual_override_takes_precedence(self, tiers):
        tier = co2kostaufg.lookup_tier(Decimal("0"), tiers, manual_override=7)
        assert tier.tier_number == 7

    def test_manual_override_invalid_tier_raises(self, tiers):
        with pytest.raises(ValueError):
            co2kostaufg.lookup_tier(Decimal("0"), tiers, manual_override=99)


class TestSplitCo2Cost:
    def test_residential_uses_tier_split(self, tiers):
        tier = co2kostaufg.lookup_tier(Decimal("25"), tiers)  # tier 4 (22-27): 30/70
        landlord, tenant = co2kostaufg.split_co2_cost(Decimal("100.00"), "residential", tier)
        assert landlord == Decimal("30.00")
        assert tenant == Decimal("70.00")
        assert landlord + tenant == Decimal("100.00")

    def test_non_residential_flat_50_50_ignores_tier(self, tiers):
        landlord, tenant = co2kostaufg.split_co2_cost(Decimal("100.00"), "non_residential", None)
        assert landlord == Decimal("50.00")
        assert tenant == Decimal("50.00")

    def test_residential_requires_tier(self):
        with pytest.raises(ValueError):
            co2kostaufg.split_co2_cost(Decimal("100.00"), "residential", None)


class TestDeductLandlordCo2Share:
    def test_deducts_from_pool(self):
        assert co2kostaufg.deduct_landlord_co2_share(
            Decimal("1000.00"), Decimal("300.00")
        ) == Decimal("700.00")

    def test_zero_share_is_noop(self):
        # The Calberlah reference document's CO2 line is 0.00 -- doesn't disambiguate
        # the sign convention (docs/legal-requirements.md §1), but a zero share must
        # trivially leave the pool unchanged either way.
        assert co2kostaufg.deduct_landlord_co2_share(
            Decimal("2608.40"), Decimal("0.00")
        ) == Decimal("2608.40")

    def test_share_exceeding_pool_raises(self):
        with pytest.raises(ValueError):
            co2kostaufg.deduct_landlord_co2_share(Decimal("100.00"), Decimal("200.00"))
