from datetime import date
from decimal import Decimal

from calc_engine import rent_increase as ri


def _check(**overrides):
    args = {
        "zugang": date(2026, 10, 31),
        "current_rent": Decimal("500.00"),
        "new_rent": Decimal("515.00"),
        "last_increase_effective": None,
        "rent_three_years_before": Decimal("500.00"),
        "kappungsgrenze_pct": Decimal("20"),
        "vergleichsmiete": None,
    }
    return ri.check_rent_increase(**{**args, **overrides})


class TestEffectiveDate:
    def test_zugang_on_last_day_of_october_takes_effect_on_first_of_january(self):
        assert ri.earliest_effective_date(date(2026, 10, 31)) == date(2027, 1, 1)

    def test_zugang_mid_november_misses_first_of_january(self):
        assert ri.earliest_effective_date(date(2026, 11, 13)) == date(2027, 2, 1)

    def test_zugang_on_first_of_month(self):
        assert ri.earliest_effective_date(date(2026, 12, 1)) == date(2027, 3, 1)


class TestZustimmungsfrist:
    def test_ends_with_the_month_after_next(self):
        assert ri.zustimmungsfrist_end(date(2026, 11, 13)) == date(2027, 1, 31)

    def test_february_end_is_not_a_leap_year(self):
        assert ri.zustimmungsfrist_end(date(2026, 12, 5)) == date(2027, 2, 28)


class TestIncreaseByPercent:
    def test_three_percent_of_round_rent(self):
        assert ri.increase_by_percent(Decimal("700.00"), Decimal("3")) == Decimal("721.00")

    def test_rounds_half_up_to_cents(self):
        assert ri.increase_by_percent(Decimal("733.33"), Decimal("3")) == Decimal("755.33")


class TestSperrfrist:
    def test_fifteen_months_after_last_increase_is_enough(self):
        result = _check(last_increase_effective=date(2025, 10, 1))
        assert result.effective_date == date(2027, 1, 1)
        assert result.is_valid

    def test_fourteen_months_is_too_early(self):
        result = _check(last_increase_effective=date(2025, 11, 1))
        assert any("15 Monate" in v for v in result.violations)

    def test_request_within_one_year_of_last_increase(self):
        result = _check(zugang=date(2026, 11, 13), last_increase_effective=date(2025, 11, 20))
        assert any("ein Jahr" in v for v in result.violations)


class TestKappungsgrenze:
    def test_exactly_twenty_percent_is_allowed(self):
        assert _check(new_rent=Decimal("600.00")).is_valid

    def test_one_cent_over_twenty_percent_is_rejected(self):
        result = _check(new_rent=Decimal("600.01"))
        assert any("Kappungsgrenze" in v for v in result.violations)

    def test_fifteen_percent_area(self):
        result = _check(new_rent=Decimal("580.00"), kappungsgrenze_pct=Decimal("15"))
        assert any("575.00" in v for v in result.violations)


class TestVergleichsmiete:
    def test_above_vergleichsmiete_is_rejected(self):
        result = _check(vergleichsmiete=Decimal("510.00"))
        assert any("Vergleichsmiete" in v for v in result.violations)

    def test_at_vergleichsmiete_is_allowed(self):
        assert _check(vergleichsmiete=Decimal("515.00")).is_valid

    def test_increase_percentage_is_reported(self):
        assert _check().increase_pct == Decimal("3.00")
