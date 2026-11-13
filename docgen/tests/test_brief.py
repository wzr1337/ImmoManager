import zipfile
from datetime import date
from decimal import Decimal

from calc_engine import rent_increase as ri
from calc_engine.statement import BetriebskostenStatement
from docgen import brief
from models.landlord import LandlordProfile
from models.tenant import Tenant

LANDLORD = LandlordProfile(
    name="Max Vermieter",
    street="Musterweg",
    house_number="1",
    postal_code="12345",
    city="Musterstadt",
    bank_iban="DE00 0000 0000 0000 0000 00",
    contact_email="vermieter@example.org",
)
TENANT = Tenant(
    id=1,
    first_name="Erika",
    last_name="Beispiel",
    street="Beispielstr. 5",
    postal_code="20095",
    city="Hamburg",
)


def _statement(balance: Decimal) -> BetriebskostenStatement:
    return BetriebskostenStatement(
        tenant_name="Erika Beispiel",
        tenant_address="Beispielstr. 5, 20095 Hamburg",
        unit_label="Whg 1",
        property_label="Musterhaus",
        property_address="Musterweg 1, 12345 Musterstadt",
        billing_period_start=date(2025, 1, 1),
        billing_period_end=date(2025, 12, 31),
        deadline_date=date(2026, 12, 31),
        cost_lines=[],
        total_tenant_cost=Decimal("1234.56"),
        advance_payments_total=Decimal("1000.00"),
        balance=balance,
    )


def _document_text(path) -> str:
    with zipfile.ZipFile(path) as archive:
        return archive.read("word/document.xml").decode("utf-8")


class TestAbrechnungAnschreiben:
    def test_nachzahlung_names_amount_and_asks_for_transfer(self):
        content = brief.abrechnung_anschreiben(
            _statement(Decimal("234.56")), LANDLORD, today=date(2026, 11, 13)
        )

        text = " ".join(content["body"])
        assert "Nachzahlung von 234,56 €" in text
        assert content["empfaenger"] == ["Erika Beispiel", "Beispielstr. 5", "20095 Hamburg"]
        assert content["betreff"] == "Betriebskostenabrechnung 2025 – Whg 1"

    def test_guthaben_is_refunded(self):
        content = brief.abrechnung_anschreiben(
            _statement(Decimal("-50.00")), LANDLORD, today=date(2026, 11, 13)
        )

        assert "Guthaben von 50,00 €" in " ".join(content["body"])

    def test_sender_line_fits_the_return_address_field(self):
        content = brief.abrechnung_anschreiben(
            _statement(Decimal("1")), LANDLORD, today=date(2026, 11, 13)
        )

        assert len(content["absender"]) <= 60


class TestMieterhoehungSchreiben:
    def test_letter_states_rents_effective_date_and_deadline(self):
        check = ri.check_rent_increase(
            zugang=date(2026, 11, 13),
            current_rent=Decimal("700.00"),
            new_rent=Decimal("721.00"),
            last_increase_effective=None,
            rent_three_years_before=Decimal("700.00"),
            kappungsgrenze_pct=Decimal("20"),
            vergleichsmiete=None,
        )

        content = brief.mieterhoehung_schreiben(
            landlord=LANDLORD,
            tenant=TENANT,
            unit_label="Whg 1",
            property_address="Musterweg 1, 12345 Musterstadt",
            current_rent=Decimal("700.00"),
            check=check,
            begruendung="Mietspiegel 2025, Feld F4",
            today=date(2026, 11, 13),
        )

        text = " ".join(content["body"])
        assert "700,00 € auf 721,00 €" in text
        assert "ab 01.02.2027" in text
        assert "bis zum 31.01.2027" in text
        assert "Mietspiegel 2025, Feld F4" in text


class TestRender:
    def test_rendered_docx_contains_letter_text(self, tmp_path):
        content = brief.abrechnung_anschreiben(
            _statement(Decimal("234.56")), LANDLORD, today=date(2026, 11, 13)
        )

        path = brief.render_brief(content, tmp_path / "brief.docx")

        assert "Betriebskostenabrechnung 2025" in _document_text(path)
