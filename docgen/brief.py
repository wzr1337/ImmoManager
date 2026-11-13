"""DIN-5008 letters (Anschreiben) built from the same calc_engine results the
statements use. The layout lives in docgen/din5008/vorlage.docx; this module only
supplies the text."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from pathlib import Path

from calc_engine.rent_increase import RentIncreaseCheck
from calc_engine.statement import BetriebskostenStatement
from docgen.din5008.build_brief import build
from docgen.format import fmt_date, fmt_money
from models.landlord import LandlordProfile
from models.tenant import Tenant

_GREETING_CLOSING = "Mit freundlichen Grüßen"


def _sender_fields(landlord: LandlordProfile, today: date) -> dict:
    footer = [landlord.name]
    if landlord.bank_iban:
        bank = f"IBAN {landlord.bank_iban}"
        if landlord.bank_bic:
            bank += f" · BIC {landlord.bank_bic}"
        footer = [f"{landlord.name} · {bank}"]
    contact = [
        line
        for line in (
            f"Telefon:\t{landlord.contact_phone}" if landlord.contact_phone else None,
            f"E-Mail:\t\t{landlord.contact_email}" if landlord.contact_email else None,
        )
        if line
    ]
    return {
        "absender": f"{landlord.name}, {landlord.street} {landlord.house_number}, "
        f"{landlord.postal_code} {landlord.city}",
        "kontakt": contact + [""],
        "datum": f"{landlord.city}, den {fmt_date(today)}",
        "footer": footer,
    }


def abrechnung_anschreiben(
    statement: BetriebskostenStatement, landlord: LandlordProfile, *, today: date
) -> dict:
    owed = statement.balance > 0
    amount = fmt_money(abs(statement.balance))
    period = (
        f"{fmt_date(statement.billing_period_start)} bis {fmt_date(statement.billing_period_end)}"
    )
    outcome = (
        f"Daraus ergibt sich eine Nachzahlung von {amount}. Bitte überweisen Sie diesen "
        "Betrag auf das unten genannte Konto."
        if owed
        else f"Daraus ergibt sich ein Guthaben von {amount}, das wir Ihnen erstatten."
    )
    return {
        **_sender_fields(landlord, today),
        "empfaenger": [statement.tenant_name, *statement.tenant_address.split(", ")],
        "betreff": f"Betriebskostenabrechnung {statement.billing_period_end.year} – "
        f"{statement.unit_label}",
        "body": [
            f"Guten Tag {statement.tenant_name},",
            (
                f"anbei erhalten Sie die Betriebskostenabrechnung für {statement.property_label} "
                f"für den Zeitraum {period}."
            ),
            (
                f"Ihre Kosten betragen {fmt_money(statement.total_tenant_cost)}, abzüglich Ihrer "
                f"Vorauszahlungen von {fmt_money(statement.advance_payments_total)}. {outcome}"
            ),
            "Die Aufstellung der Kosten und Verteilerschlüssel finden Sie in der Anlage.",
            f"{_GREETING_CLOSING}\n{landlord.name}",
        ],
    }


def mieterhoehung_schreiben(
    *,
    landlord: LandlordProfile,
    tenant: Tenant,
    unit_label: str,
    property_address: str,
    current_rent: Decimal,
    check: RentIncreaseCheck,
    begruendung: str,
    today: date,
) -> dict:
    return {
        **_sender_fields(landlord, today),
        "empfaenger": [tenant.full_name, tenant.street, f"{tenant.postal_code} {tenant.city}"],
        "betreff": f"Mieterhöhungsverlangen gemäß § 558 BGB – {unit_label}",
        "body": [
            f"Guten Tag {tenant.full_name},",
            (
                f"für die Wohnung {unit_label} ({property_address}) bitten wir Sie um Zustimmung "
                f"zur Erhöhung der monatlichen Nettokaltmiete von {fmt_money(current_rent)} auf "
                f"{fmt_money(check.new_rent)}. Das entspricht einer Erhöhung um "
                f"{fmt_money(check.new_rent - current_rent)} ({check.increase_pct} %). "
                f"Die erhöhte Miete soll ab {fmt_date(check.effective_date)} gelten."
            ),
            f"Begründung: {begruendung}",
            (
                f"Bitte stimmen Sie der Erhöhung bis zum {fmt_date(check.zustimmungsfrist_end)} "
                "schriftlich oder in Textform zu. Bei Zustimmung schulden Sie die erhöhte Miete "
                f"gemäß § 558b BGB ab {fmt_date(check.effective_date)}."
            ),
            f"{_GREETING_CLOSING}\n{landlord.name}",
        ],
    }


def render_brief(content: dict, output_path: Path) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    build(content, str(output_path))
    return output_path
