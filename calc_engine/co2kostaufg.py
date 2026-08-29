"""CO2KostAufG: splits the CO2-pricing portion of heating fuel cost between
landlord and tenant. docs/legal-requirements.md §5.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import Literal

import yaml

from calc_engine.apportionment import apportion_by_weights

REFERENCE_DATA_DIR = Path(__file__).resolve().parent / "reference_data"

BuildingType = Literal["residential", "non_residential"]
NON_RESIDENTIAL_LANDLORD_PCT = Decimal(50)
NON_RESIDENTIAL_TENANT_PCT = Decimal(50)


@dataclass(frozen=True)
class CO2Tier:
    tier_number: int
    co2_per_sqm_max: Decimal | None  # None = open-ended top tier
    landlord_pct: Decimal
    tenant_pct: Decimal


def load_tiers(billing_year: int) -> list[CO2Tier]:
    path = REFERENCE_DATA_DIR / f"co2_tiers_{billing_year}.yaml"
    if not path.exists():
        raise FileNotFoundError(
            f"no CO2KostAufG tier table for billing year {billing_year} at {path}; "
            "tier boundaries change yearly and must not be assumed from a prior year"
        )
    data = yaml.safe_load(path.read_text())
    return [
        CO2Tier(
            tier_number=t["tier_number"],
            co2_per_sqm_max=(
                None if t["co2_per_sqm_max"] is None else Decimal(str(t["co2_per_sqm_max"]))
            ),
            landlord_pct=Decimal(str(t["landlord_pct"])),
            tenant_pct=Decimal(str(t["tenant_pct"])),
        )
        for t in data["tiers"]
    ]


def compute_co2_per_sqm(
    fuel_consumption: Decimal, emission_factor: Decimal, heated_area_m2: Decimal
) -> Decimal:
    if heated_area_m2 <= 0:
        raise ValueError("heated_area_m2 must be positive")
    return (fuel_consumption * emission_factor) / heated_area_m2


def lookup_tier(
    co2_per_sqm: Decimal, tiers: list[CO2Tier], manual_override: int | None = None
) -> CO2Tier:
    if manual_override is not None:
        for tier in tiers:
            if tier.tier_number == manual_override:
                return tier
        raise ValueError(f"manual_override tier {manual_override} not found in tier table")

    for tier in sorted(tiers, key=lambda t: t.tier_number):
        if tier.co2_per_sqm_max is None or co2_per_sqm < tier.co2_per_sqm_max:
            return tier
    raise ValueError("no matching CO2 tier found (tier table missing an open-ended top tier)")


def split_co2_cost(
    co2_portion: Decimal, building_type: BuildingType, tier: CO2Tier | None
) -> tuple[Decimal, Decimal]:
    """Returns (landlord_share, tenant_share) of the CO2-pricing cost portion."""
    if building_type == "non_residential":
        shares = apportion_by_weights(
            co2_portion, {0: NON_RESIDENTIAL_LANDLORD_PCT, 1: NON_RESIDENTIAL_TENANT_PCT}
        )
        return shares[0], shares[1]

    if tier is None:
        raise ValueError("tier is required for residential buildings")
    shares = apportion_by_weights(co2_portion, {0: tier.landlord_pct, 1: tier.tenant_pct})
    return shares[0], shares[1]


def deduct_landlord_co2_share(brennstoffkosten: Decimal, landlord_share: Decimal) -> Decimal:
    """Removes the landlord's CO2KostAufG share from the fuel cost pool before it's
    divided among tenants — the law's intent is tenants only ever pay their own
    CO2KostAufG-assigned share, never the landlord's.

    NOTE: verify this against a real non-zero example before first production use —
    docs/legal-requirements.md §1 flags that the reference document's CO2 line was
    €0.00 and doesn't disambiguate the sign convention from the source system.
    """
    if landlord_share > brennstoffkosten:
        raise ValueError(
            f"landlord CO2 share ({landlord_share}) exceeds Brennstoffkosten ({brennstoffkosten})"
        )
    return brennstoffkosten - landlord_share
