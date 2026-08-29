"""Generic key-weighted cost apportionment with cent-exact rounding reconciliation.

This is the single most important module in the codebase: every Abrechnung line
ultimately calls apportion_by_weights. A naive round-each-share-independently
approach drifts by a few cents on real data (see calc_engine/tests/test_apportionment.py),
which would make a statement formally defective under BGH element 1 (docs/legal-requirements.md §6).
"""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal

CENT = Decimal("0.01")


def apportion_by_weights(total: Decimal, weights: dict[int, Decimal]) -> dict[int, Decimal]:
    """Split `total` proportionally to `weights`, guaranteeing sum(result) == total exactly.

    `weights` maps an arbitrary key (unit_id, etc.) to a non-negative Decimal weight
    (area, persons, consumption units, ...). Raises ValueError if all weights are
    zero (nothing to apportion by) or any weight is negative.
    """
    if not weights:
        return {}

    for key, weight in weights.items():
        if weight < 0:
            raise ValueError(f"negative weight for {key!r}: {weight}")

    weight_total = sum(weights.values())
    if weight_total == 0:
        raise ValueError("all weights are zero; cannot apportion")

    raw_shares: dict[int, Decimal] = {
        key: (total * weight / weight_total) for key, weight in weights.items()
    }
    rounded_shares = {
        key: share.quantize(CENT, rounding=ROUND_HALF_UP) for key, share in raw_shares.items()
    }

    residual = total - sum(rounded_shares.values())
    if residual != 0:
        # Assign the rounding residual to the largest share so the sum matches
        # `total` exactly to the cent. Ties broken by key for determinism.
        largest_key = max(rounded_shares, key=lambda k: (rounded_shares[k], -k))
        rounded_shares[largest_key] += residual

    return rounded_shares
