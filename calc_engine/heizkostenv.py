"""HeizkostenV: mandatory consumption/area split for heating & hot water.

docs/legal-requirements.md §4: 50-70% of heating (and, separately, hot water) costs
must be billed by measured consumption, the rest by Wohnfläche; pre-1994 uninsulated
buildings where the tenant can't influence consumption must use a fixed 70/30 split
regardless of the configured ratio. A combined boiler system first splits the pooled
fuel/ancillary cost into a heating share and a hot-water share (see
docs/legal-requirements.md §1 "Combined-system split") before either sub-pool's
Grundkosten/Verbrauchskosten split is applied — that step is skipped when heating
and hot water are separately metered (the more common case).
"""

from __future__ import annotations

from decimal import Decimal

from calc_engine.apportionment import apportion_by_weights

MIN_CONSUMPTION_PCT = Decimal(50)
MAX_CONSUMPTION_PCT = Decimal(70)
PRE1994_CONSUMPTION_PCT = Decimal(70)
METERING_NONCOMPLIANT_KUERZUNG_PCT = Decimal(15)


def split_combined_system(total: Decimal, warmwater_share_pct: Decimal) -> tuple[Decimal, Decimal]:
    """Splits a combined heating+hot-water fuel/ancillary pool into (heating, warmwater).

    `warmwater_share_pct` is the percentage of `total` attributable to hot water
    (typically derived from a submeter, e.g. via VDI 2077-style computation — that
    derivation is out of scope here; this function just applies the given ratio).
    """
    if not (0 <= warmwater_share_pct <= 100):
        raise ValueError(f"warmwater_share_pct out of range: {warmwater_share_pct}")

    shares = apportion_by_weights(
        total, {0: Decimal(100) - warmwater_share_pct, 1: warmwater_share_pct}
    )
    return shares[0], shares[1]


def split_grundkosten_verbrauch(
    pool: Decimal, consumption_pct: Decimal, pre1994_uninsulated: bool
) -> tuple[Decimal, Decimal]:
    """Splits a heating or hot-water cost pool into (grundkosten, verbrauchskosten).

    Raises if `consumption_pct` is outside the legal 50-70 band — a config error here
    is a legal-correctness bug, not something to silently clamp. The pre-1994
    exception overrides the configured ratio entirely, per docs/legal-requirements.md §4.
    """
    effective_pct = PRE1994_CONSUMPTION_PCT if pre1994_uninsulated else consumption_pct

    if not pre1994_uninsulated and not (
        MIN_CONSUMPTION_PCT <= consumption_pct <= MAX_CONSUMPTION_PCT
    ):
        raise ValueError(
            f"heating consumption split {consumption_pct}% is outside the legal "
            f"{MIN_CONSUMPTION_PCT}-{MAX_CONSUMPTION_PCT}% band (§ 7 HeizkostenV)"
        )

    shares = apportion_by_weights(pool, {0: Decimal(100) - effective_pct, 1: effective_pct})
    grundkosten, verbrauchskosten = shares[0], shares[1]
    return grundkosten, verbrauchskosten


def apportion_consumption_pool(pool: Decimal, readings: dict[int, Decimal]) -> dict[int, Decimal]:
    return apportion_by_weights(pool, readings)


def apply_metering_penalty(tenant_total: Decimal, metering_compliant: bool) -> Decimal:
    """§ 12 HeizkostenV: automatic 15% cost reduction if metering/remote-readability
    or the split-ratio band is violated — applies without proof of harm."""
    if metering_compliant:
        return tenant_total
    reduction = (tenant_total * METERING_NONCOMPLIANT_KUERZUNG_PCT / 100).quantize(Decimal("0.01"))
    return tenant_total - reduction
