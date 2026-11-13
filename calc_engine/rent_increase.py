"""Mieterhöhung bis zur ortsüblichen Vergleichsmiete (§§ 558, 558b BGB). Pure date and
money rules; nothing here reads the DB. Staffel-/Indexmiete (§§ 557a/557b BGB) follow
other rules and are not covered."""

from __future__ import annotations

import calendar
from dataclasses import dataclass
from datetime import date
from decimal import ROUND_HALF_UP, Decimal

CENT = Decimal("0.01")


def add_months(value: date, months: int) -> date:
    index = value.year * 12 + (value.month - 1) + months
    year, month = divmod(index, 12)
    last_day = calendar.monthrange(year, month + 1)[1]
    return date(year, month + 1, min(value.day, last_day))


def increase_by_percent(rent: Decimal, percent: Decimal) -> Decimal:
    return (rent * (Decimal(100) + percent) / Decimal(100)).quantize(CENT, ROUND_HALF_UP)


def earliest_effective_date(zugang: date) -> date:
    # § 558b Abs. 1 BGB: erhöhte Miete ab Beginn des dritten Kalendermonats nach Zugang.
    return add_months(zugang.replace(day=1), 3)


def zustimmungsfrist_end(zugang: date) -> date:
    # § 558b Abs. 2 BGB: Überlegungsfrist bis zum Ende des übernächsten Monats.
    first_of_target = add_months(zugang.replace(day=1), 2)
    return first_of_target.replace(day=calendar.monthrange(*first_of_target.timetuple()[:2])[1])


@dataclass(frozen=True)
class RentIncreaseCheck:
    new_rent: Decimal
    increase_pct: Decimal
    effective_date: date
    zustimmungsfrist_end: date
    violations: tuple[str, ...]

    @property
    def is_valid(self) -> bool:
        return not self.violations


def check_rent_increase(
    *,
    zugang: date,
    current_rent: Decimal,
    new_rent: Decimal,
    last_increase_effective: date | None,
    rent_three_years_before: Decimal,
    kappungsgrenze_pct: Decimal,
    vergleichsmiete: Decimal | None,
) -> RentIncreaseCheck:
    """All rents are Nettokaltmiete. `rent_three_years_before` is the rent three
    years before the increase takes effect, ignoring Erhöhungen under §§ 559-560 BGB
    (§ 558 Abs. 3 BGB)."""
    effective = earliest_effective_date(zugang)
    violations: list[str] = []

    if last_increase_effective is not None:
        if zugang < add_months(last_increase_effective, 12):
            violations.append(
                "§ 558 Abs. 1 S. 2 BGB: Verlangen frühestens ein Jahr nach der letzten Erhöhung"
            )
        if effective < add_months(last_increase_effective, 15):
            violations.append(
                "§ 558 Abs. 1 S. 1 BGB: Miete muss zum Wirksamkeitstermin 15 Monate "
                "unverändert sein"
            )

    kappung_limit = increase_by_percent(rent_three_years_before, kappungsgrenze_pct)
    if new_rent > kappung_limit:
        violations.append(
            f"§ 558 Abs. 3 BGB: Kappungsgrenze {kappungsgrenze_pct} % in drei Jahren "
            f"erlaubt höchstens {kappung_limit}"
        )

    if vergleichsmiete is not None and new_rent > vergleichsmiete:
        violations.append(
            f"§ 558 Abs. 1 BGB: neue Miete über der Vergleichsmiete {vergleichsmiete}"
        )

    return RentIncreaseCheck(
        new_rent=new_rent,
        increase_pct=((new_rent - current_rent) / current_rent * 100).quantize(CENT),
        effective_date=effective,
        zustimmungsfrist_end=zustimmungsfrist_end(zugang),
        violations=tuple(violations),
    )
