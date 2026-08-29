"""Vacant units keep their cost share with the landlord — never redistribute it.

docs/legal-requirements.md §8: cost shares attributable to vacant units during a
billing period are not redistributed onto other tenants.

IMPORTANT: apportion_by_weights always makes sum(shares) == total exactly (that's
its whole contract — see apportionment.py). So excluding a vacant unit's weight
*before* calling it would spread the *entire* total across only the occupied units,
inflating their bills with the vacant unit's share — precisely what's illegal here.

The correct approach is the opposite order: apportion using the FULL weight map
(every unit, occupied or not — this also matches the standard formula's
denominator, e.g. "Gesamtkosten : Gesamtwohnfläche x eigene Wohnfläche", which uses
the whole building's area regardless of occupancy), then drop the vacant units'
*computed shares* from what's actually billed. The landlord simply never collects
that unit's share from anyone; sum(occupied shares) ends up less than total by
design.
"""

from __future__ import annotations

from decimal import Decimal


def exclude_vacant(shares: dict[int, Decimal], occupied_unit_ids: set[int]) -> dict[int, Decimal]:
    """Drops vacant units' shares from what's billed. Call this AFTER
    apportion_by_weights (using the full, all-units weight map) — never before."""
    return {unit_id: share for unit_id, share in shares.items() if unit_id in occupied_unit_ids}
