from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Literal

MeterType = Literal["heating", "hot_water", "cold_water", "electricity_common"]


@dataclass(frozen=True)
class MeterReading:
    id: int
    unit_id: int
    meter_id: str
    meter_type: MeterType
    reading_date: date
    value: Decimal
    billing_year: int
    remote_read: bool = False
