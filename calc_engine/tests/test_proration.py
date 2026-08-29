from datetime import date
from decimal import Decimal

import pytest

from calc_engine import proration
from calc_engine.tests.fixtures import calberlah_worked_example as fx

PERIOD_START = date(2025, 1, 1)
PERIOD_END = date(2025, 12, 31)


class TestOccupiedDays:
    def test_full_year_tenant(self):
        occupied, total = proration.occupied_days(PERIOD_START, PERIOD_END, date(2025, 1, 1), None)
        assert occupied == total == 365

    def test_mid_period_move_in(self):
        occupied, total = proration.occupied_days(PERIOD_START, PERIOD_END, date(2025, 7, 1), None)
        assert total == 365
        assert occupied == 184  # Jul 1 - Dec 31 inclusive

    def test_mid_period_move_out(self):
        occupied, _total = proration.occupied_days(
            PERIOD_START, PERIOD_END, date(2024, 6, 1), date(2025, 3, 31)
        )
        assert occupied == 90  # Jan 1 - Mar 31 inclusive

    def test_zero_day_edge_case_contract_ends_before_period(self):
        occupied, total = proration.occupied_days(
            PERIOD_START, PERIOD_END, date(2024, 1, 1), date(2024, 12, 31)
        )
        assert occupied == 0
        assert total == 365

    def test_leap_year(self):
        _occupied, total = proration.occupied_days(
            date(2028, 1, 1), date(2028, 12, 31), date(2028, 1, 1), None
        )
        assert total == 366  # 2028 is a leap year


class TestProrateFlat:
    def test_full_period_yields_full_share(self):
        assert proration.prorate_flat(Decimal("1200.00"), 365, 365) == Decimal("1200.00")

    def test_half_period(self):
        assert proration.prorate_flat(Decimal("1000.00"), 50, 100) == Decimal("500.00")

    def test_zero_total_days_raises(self):
        with pytest.raises(ValueError):
            proration.prorate_flat(Decimal("100.00"), 0, 0)


class TestGradtagAnteile:
    def test_full_year_tenant_anteile_equals_total(self):
        tenant_anteile, total_anteile = proration.gradtag_anteile(
            PERIOD_START, PERIOD_END, date(2025, 1, 1), None, fx.GRADTAGSTABELLE
        )
        assert tenant_anteile == total_anteile

    def test_partial_year_move_out_end_of_june(self):
        tenant_anteile, total_anteile = proration.gradtag_anteile(
            PERIOD_START, PERIOD_END, date(2025, 1, 1), date(2025, 6, 30), fx.GRADTAGSTABELLE
        )
        assert tenant_anteile == Decimal("583.33")
        assert tenant_anteile < total_anteile

    def test_vacant_second_half_of_year_gets_zero(self):
        tenant_anteile, _ = proration.gradtag_anteile(
            PERIOD_START, PERIOD_END, date(2024, 1, 1), date(2024, 12, 31), fx.GRADTAGSTABELLE
        )
        assert tenant_anteile == Decimal("0")


class TestProrateGradtag:
    def test_full_anteile_yields_full_share(self):
        assert proration.prorate_gradtag(
            Decimal("127.30"), Decimal("1000"), Decimal("1000")
        ) == Decimal("127.30")

    def test_zero_total_anteile_raises(self):
        with pytest.raises(ValueError):
            proration.prorate_gradtag(Decimal("100.00"), Decimal("0"), Decimal("0"))


class TestOccupiedMonths:
    def test_full_year(self):
        occupied, total = proration.occupied_months(
            PERIOD_START, PERIOD_END, date(2025, 1, 1), None
        )
        assert occupied == total == 12

    def test_six_months(self):
        occupied, total = proration.occupied_months(
            PERIOD_START, PERIOD_END, date(2025, 1, 1), date(2025, 6, 30)
        )
        assert occupied == 6
        assert total == 12
