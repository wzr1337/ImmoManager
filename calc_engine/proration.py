"""Partial-period proration: flat (day/month-based) and Gradtag (degree-day-weighted).

docs/legal-requirements.md §1/§8: a tenant occupying a unit for only part of a
billing period gets a time-prorated share. Heating demand is seasonal, so heating
Grundkosten uses Gradtag (degree-day) weighting instead of flat day-counting — a
tenant who leaves in July shouldn't be charged the same per-day heating share as one
who leaves in January. Betriebskosten and Warmwasser-Grundkosten use flat proration.
"""

from __future__ import annotations

import calendar
from datetime import date
from decimal import ROUND_HALF_UP, Decimal

from calc_engine.apportionment import CENT


def occupied_days(
    period_start: date,
    period_end: date,
    contract_start: date,
    contract_end: date | None,
) -> tuple[int, int]:
    """Returns (occupied_days_within_period, total_period_days)."""
    total_period_days = (period_end - period_start).days + 1

    overlap_start = max(period_start, contract_start)
    overlap_end = min(period_end, contract_end) if contract_end else period_end
    if overlap_start > overlap_end:
        return 0, total_period_days

    occupied = (overlap_end - overlap_start).days + 1
    return occupied, total_period_days


def prorate_flat(full_period_share: Decimal, occupied: int, total_period_days: int) -> Decimal:
    if total_period_days == 0:
        raise ValueError("total_period_days is zero; cannot prorate")
    return (full_period_share * occupied / total_period_days).quantize(CENT, rounding=ROUND_HALF_UP)


def _days_in_month(year: int, month: int) -> int:
    return calendar.monthrange(year, month)[1]


def gradtag_anteile(
    period_start: date,
    period_end: date,
    contract_start: date,
    contract_end: date | None,
    gradtagstabelle: dict[int, Decimal],
) -> tuple[Decimal, Decimal]:
    """Returns (tenant_anteile, total_period_anteile).

    `gradtagstabelle` maps month (1-12) -> degree-day points for that month
    (published table, summing to 1000 for a standard full year — see
    calc_engine/reference_data/gradtagstabelle_default.yaml). Within a month, points
    are distributed evenly per calendar day (matching the reference document's
    "je Tag" column: month_points / days_in_month).
    """
    overlap_start = max(period_start, contract_start)
    overlap_end = min(period_end, contract_end) if contract_end else period_end

    total_anteile = Decimal(0)
    tenant_anteile = Decimal(0)

    current = date(period_start.year, period_start.month, 1)
    while current <= period_end:
        days_in_month = _days_in_month(current.year, current.month)
        month_points = gradtagstabelle.get(current.month, Decimal(0))
        per_day = month_points / days_in_month

        month_start = current
        month_end = date(current.year, current.month, days_in_month)
        clipped_start = max(month_start, period_start)
        clipped_end = min(month_end, period_end)
        total_anteile += per_day * ((clipped_end - clipped_start).days + 1)

        if overlap_start <= overlap_end:
            t_start = max(clipped_start, overlap_start)
            t_end = min(clipped_end, overlap_end)
            if t_start <= t_end:
                tenant_anteile += per_day * ((t_end - t_start).days + 1)

        current = (
            date(current.year + 1, 1, 1)
            if current.month == 12
            else date(current.year, current.month + 1, 1)
        )

    return tenant_anteile, total_anteile


def prorate_gradtag(
    full_period_share: Decimal, tenant_anteile: Decimal, total_anteile: Decimal
) -> Decimal:
    if total_anteile == 0:
        raise ValueError("total_anteile is zero; cannot prorate")
    return (full_period_share * tenant_anteile / total_anteile).quantize(
        CENT, rounding=ROUND_HALF_UP
    )


def occupied_months(
    period_start: date,
    period_end: date,
    contract_start: date,
    contract_end: date | None,
) -> tuple[int, int]:
    """Whole-calendar-month approximation used for Warmwasser-Grundkosten proration
    (docs/legal-requirements.md §1 — hot water demand isn't seasonal, so the
    reference document prorates it by flat month count rather than Gradtag weight).
    Counts every calendar month touched by the overlap, inclusive.
    """
    total_months = (
        (period_end.year - period_start.year) * 12 + (period_end.month - period_start.month) + 1
    )

    overlap_start = max(period_start, contract_start)
    overlap_end = min(period_end, contract_end) if contract_end else period_end
    if overlap_start > overlap_end:
        return 0, total_months

    occupied = (
        (overlap_end.year - overlap_start.year) * 12 + (overlap_end.month - overlap_start.month) + 1
    )
    return occupied, total_months
