from decimal import Decimal

from calc_engine.apportionment import apportion_by_weights
from calc_engine.vacancy import exclude_vacant


class TestExcludeVacant:
    def test_vacant_unit_removed_from_shares(self):
        shares = {1: Decimal("50"), 2: Decimal("50"), 3: Decimal("100")}
        occupied = exclude_vacant(shares, occupied_unit_ids={1, 2})
        assert occupied == {1: Decimal("50"), 2: Decimal("50")}

    def test_vacant_share_stays_with_landlord_not_redistributed(self):
        # 3 equal-sized units, one (unit 3) vacant. Apportion using the FULL weight
        # map (all 3 units) -- each unit's share is proportional to the whole
        # building's area, matching the standard Gesamtwohnfläche-based formula --
        # then drop the vacant unit's share. The occupied tenants' shares must NOT
        # sum to the full total; the vacant unit's 1/3 stays with the landlord.
        weights = {1: Decimal("100"), 2: Decimal("100"), 3: Decimal("100")}
        all_shares = apportion_by_weights(Decimal("300.00"), weights)
        billed_shares = exclude_vacant(all_shares, occupied_unit_ids={1, 2})

        assert sum(billed_shares.values()) == Decimal("200.00")
        assert sum(billed_shares.values()) < Decimal("300.00")
        assert billed_shares[1] == Decimal("100.00")
        assert billed_shares[2] == Decimal("100.00")

    def test_no_vacancies_all_shares_retained(self):
        shares = {1: Decimal("50"), 2: Decimal("50")}
        assert exclude_vacant(shares, occupied_unit_ids={1, 2}) == shares
