"""Presentation formatting only — the one place Decimal/date become display strings.
calc_engine stays formatting-free; templates stay logic-free."""

from __future__ import annotations

from datetime import date
from decimal import Decimal


def fmt_money(value: Decimal) -> str:
    # German convention: thousands '.', decimal ','. E.g. Decimal("1234.56") -> "1.234,56 €"
    sign = "-" if value < 0 else ""
    whole, _, frac = f"{abs(value):.2f}".partition(".")
    grouped = f"{int(whole):,}".replace(",", ".")
    return f"{sign}{grouped},{frac} €"


def fmt_number(value: Decimal, decimals: int = 2) -> str:
    whole, _, frac = f"{value:.{decimals}f}".partition(".")
    grouped = f"{int(whole):,}".replace(",", ".")
    return f"{grouped},{frac}" if decimals else grouped


def fmt_date(value: date) -> str:
    return value.strftime("%d.%m.%Y")


def format_wealth_summary(summary) -> str:
    """Shared by scripts.cli show-wealth and bot/handlers/wealth.py -- one place
    for this presentation so the CLI and bot can never drift apart."""
    cash_label = summary.cash_as_of.isoformat() if summary.cash_as_of else "nie gesetzt"
    lines = [f"Bankguthaben (Stand: {cash_label}): {summary.cash_balance:.2f} EUR", ""]
    lines.append("Immobilien (Kaufpreis - Restschuld = Eigenkapital):")
    for line in summary.property_lines:
        price = f"{line.purchase_price:.2f}" if line.purchase_price is not None else "unbekannt"
        equity = f"{line.net_equity:.2f}" if line.net_equity is not None else "unbekannt"
        lines.append(f"  {line.label}: {price} - {line.liability:.2f} = {equity} EUR")
    lines.append(f"\nImmobilien-Eigenkapital gesamt: {summary.total_property_equity:.2f} EUR")
    if summary.has_incomplete_property_data:
        lines.append("(unvollständig -- mind. ein Kaufpreis fehlt)")
    lines.append(f"\nGesamtvermögen: {summary.total_wealth:.2f} EUR")
    return "\n".join(lines)
