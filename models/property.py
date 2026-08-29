from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Literal

UnitType = Literal["apartment", "garage"]


@dataclass(frozen=True)
class Property:
    id: int
    label: str
    street: str
    house_number: str
    postal_code: str
    city: str
    total_wohnflaeche_m2: Decimal
    build_year: int | None = None
    pre1994_uninsulated: bool = False
    heating_split_ratio_consumption_pct: Decimal | None = None
    heating_combined_system: bool = False
    heating_metering_remote_readable: bool = False
    heating_metering_compliant: bool = True
    co2_building_tier_override: int | None = None
    co2_override_reason: str | None = None
    gradtagstabelle_ref: str = "default"

    @property
    def address(self) -> str:
        return f"{self.street} {self.house_number}, {self.postal_code} {self.city}"


@dataclass(frozen=True)
class Unit:
    id: int
    property_id: int
    label: str
    unit_type: UnitType
    wohnflaeche_m2: Decimal | None
    heated: bool = False
