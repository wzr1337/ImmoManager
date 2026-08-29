from __future__ import annotations

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class Tenant:
    id: int
    first_name: str
    last_name: str
    street: str
    postal_code: str
    city: str
    email: str | None = None
    phone: str | None = None
    bank_iban: str | None = None

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"

    @property
    def address(self) -> str:
        return f"{self.street}, {self.postal_code} {self.city}"


@dataclass(frozen=True)
class Contract:
    id: int
    unit_id: int
    tenant_id: int
    start_date: date
    end_date: date | None
    monthly_vorauszahlung_nebenkosten_cents: int
    monthly_vorauszahlung_heizkosten_cents: int | None = None
    persons_count: int | None = None


@dataclass(frozen=True)
class ContractCostTypeKey:
    contract_id: int
    cost_type_code: int
    distribution_key: (
        str  # 'wohnflaeche' | 'personenzahl' | 'verbrauch' | 'stueck' | 'mea' | 'custom'
    )
