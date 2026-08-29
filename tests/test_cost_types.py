"""Every enum member must have corresponding CostTypeMeta -- a member without one
breaks label_for() and silently disappears from all_cost_type_choices(), exactly
the bug this test was added to catch (FINANZIERUNGSKOSTEN was added to the enum
but not to NON_APPORTIONABLE_COST_TYPES, so it passed lint/type-checks but was
invisible to the CLI and bot until entering an invoice with that code failed)."""

from config.cost_types import (
    COST_TYPES,
    NON_APPORTIONABLE_COST_TYPES,
    BetrKVCostType,
    NichtUmlagefaehigCostType,
    all_cost_type_choices,
    is_apportionable_code,
    label_for,
)


class TestCostTypeCompleteness:
    def test_every_betrkv_member_has_metadata(self):
        assert set(COST_TYPES.keys()) == set(BetrKVCostType)

    def test_every_non_apportionable_member_has_metadata(self):
        assert set(NON_APPORTIONABLE_COST_TYPES.keys()) == set(NichtUmlagefaehigCostType)

    def test_label_for_resolves_every_known_code(self):
        for code, _label, _apportionable in all_cost_type_choices():
            assert label_for(code)  # must not raise, must be non-empty

    def test_all_cost_type_choices_covers_both_enums(self):
        codes = {c for c, _label, _apportionable in all_cost_type_choices()}
        assert codes == {int(c) for c in BetrKVCostType} | {
            int(c) for c in NichtUmlagefaehigCostType
        }


class TestIsApportionableCode:
    def test_betrkv_range_is_apportionable(self):
        assert all(is_apportionable_code(c) for c in BetrKVCostType)

    def test_non_apportionable_range_is_not_apportionable(self):
        assert not any(is_apportionable_code(c) for c in NichtUmlagefaehigCostType)
