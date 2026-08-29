from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class LandlordProfile:
    name: str
    street: str
    house_number: str
    postal_code: str
    city: str
    tax_id: str | None = None
    bank_iban: str | None = None
    bank_bic: str | None = None
    bank_account_holder: str | None = None
    contact_email: str | None = None
    contact_phone: str | None = None

    @property
    def address(self) -> str:
        return f"{self.street} {self.house_number}, {self.postal_code} {self.city}"
