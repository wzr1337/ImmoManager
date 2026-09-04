"""Manual data entry CLI for Phase 1 (no Telegram bot yet). Run as:
    python -m scripts.cli <command> [args...]
Run `python -m scripts.cli --help` for the full command list.
"""

from __future__ import annotations

import argparse
import sys
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config.cost_types import all_cost_type_choices, is_apportionable_code
from config.settings import load_settings
from db.connection import connect
from db.repositories import (
    billing_repo,
    contract_repo,
    document_repo,
    financing_repo,
    invoice_repo,
    kassenbuch_repo,
    landlord_repo,
    property_repo,
    tenant_repo,
    wealth_repo,
)
from docgen.format import format_wealth_summary
from models.financing import LoanPayment, LoanTerms
from models.landlord import LandlordProfile
from models.property import Property, Unit
from models.tenant import Contract, Tenant


def cmd_set_landlord(conn, args: argparse.Namespace) -> None:
    landlord_repo.upsert(
        conn,
        LandlordProfile(
            name=args.name,
            street=args.street,
            house_number=args.house_number,
            postal_code=args.postal_code,
            city=args.city,
            tax_id=args.tax_id,
            bank_iban=args.iban,
            bank_bic=args.bic,
            bank_account_holder=args.account_holder,
            contact_email=args.email,
            contact_phone=args.phone,
        ),
    )
    print("Landlord profile saved.")


def cmd_add_property(conn, args: argparse.Namespace) -> None:
    property_id = property_repo.create(
        conn,
        Property(
            id=0,
            label=args.label,
            street=args.street,
            house_number=args.house_number,
            postal_code=args.postal_code,
            city=args.city,
            total_wohnflaeche_m2=Decimal(args.wohnflaeche),
            build_year=args.build_year,
            pre1994_uninsulated=args.pre1994_uninsulated,
            heating_split_ratio_consumption_pct=(
                Decimal(args.heating_consumption_pct) if args.heating_consumption_pct else None
            ),
            heating_combined_system=args.heating_combined_system,
            heating_metering_remote_readable=args.heating_remote_readable,
            heating_metering_compliant=not args.heating_noncompliant,
        ),
    )
    print(f"Property created: id={property_id}")


def cmd_add_unit(conn, args: argparse.Namespace) -> None:
    unit_id = property_repo.add_unit(
        conn,
        Unit(
            id=0,
            property_id=args.property_id,
            label=args.label,
            unit_type=args.type,
            wohnflaeche_m2=Decimal(args.wohnflaeche) if args.wohnflaeche else None,
            heated=args.heated,
            miteigentumsanteil_promille=Decimal(args.mea) if args.mea else None,
        ),
    )
    print(f"Unit created: id={unit_id}")


def cmd_set_unit_mea(conn, args: argparse.Namespace) -> None:
    property_repo.set_unit_mea(conn, args.unit_id, Decimal(args.mea))
    print(f"Unit {args.unit_id} Miteigentumsanteil set to {args.mea}/1000.")


def cmd_add_tenant(conn, args: argparse.Namespace) -> None:
    tenant_id = tenant_repo.create(
        conn,
        Tenant(
            id=0,
            first_name=args.first_name,
            last_name=args.last_name,
            street=args.street,
            postal_code=args.postal_code,
            city=args.city,
            email=args.email,
            phone=args.phone,
            bank_iban=args.iban,
        ),
    )
    print(f"Tenant created: id={tenant_id}")


def cmd_add_contract(conn, args: argparse.Namespace) -> None:
    contract_id = contract_repo.create(
        conn,
        Contract(
            id=0,
            unit_id=args.unit_id,
            tenant_id=args.tenant_id,
            start_date=date.fromisoformat(args.start_date),
            end_date=date.fromisoformat(args.end_date) if args.end_date else None,
            monthly_vorauszahlung_nebenkosten_cents=round(Decimal(args.monthly_advance) * 100),
            monthly_vorauszahlung_heizkosten_cents=(
                round(Decimal(args.monthly_advance_heating) * 100)
                if args.monthly_advance_heating
                else None
            ),
            persons_count=args.persons,
            deposit_cents=round(Decimal(args.deposit) * 100) if args.deposit else 0,
        ),
    )
    print(f"Contract created: id={contract_id}")


def cmd_set_deposit(conn, args: argparse.Namespace) -> None:
    contract_repo.set_deposit(conn, args.contract_id, round(Decimal(args.deposit) * 100))
    print(f"Contract {args.contract_id} deposit set to {args.deposit} EUR.")


def cmd_return_deposit(conn, args: argparse.Namespace) -> None:
    contract_repo.return_deposit(
        conn,
        args.contract_id,
        round(Decimal(args.amount) * 100),
        date.fromisoformat(args.date),
    )
    print(f"Contract {args.contract_id}: {args.amount} EUR deposit returned on {args.date}.")


def cmd_add_invoice(conn, args: argparse.Namespace) -> None:
    try:
        amount = Decimal(args.amount)
    except InvalidOperation:
        raise SystemExit(f"invalid amount: {args.amount}")

    known_codes = {code for code, _label, _apportionable in all_cost_type_choices()}
    if args.cost_type not in known_codes:
        raise SystemExit(
            f"unknown cost type code: {args.cost_type} — run `list-cost-types` for valid codes"
        )

    invoice_repo.create(
        conn,
        property_id=args.property_id,
        cost_type_code=args.cost_type,
        billing_year=args.billing_year,
        amount=amount,
        vendor_name=args.vendor,
        invoice_date=date.fromisoformat(args.invoice_date) if args.invoice_date else None,
        description=args.description,
        source_file_path=args.source_file,
        entry_method="manual",
        entered_by="cli",
    )
    kind = "apportionable" if is_apportionable_code(args.cost_type) else "non-apportionable"
    print(f"Invoice recorded ({kind}).")


def cmd_list_properties(conn, args: argparse.Namespace) -> None:
    liabilities = financing_repo.current_liability_by_property(conn)
    for p in property_repo.list_all(conn):
        print(f"[{p.id}] {p.label} — {p.address} ({p.total_wohnflaeche_m2} m²)")
        for u in property_repo.list_units(conn, p.id):
            print(f"    [{u.id}] {u.label} ({u.unit_type}, {u.wohnflaeche_m2} m²)")
        if p.purchase_price_cents is not None:
            price = Decimal(p.purchase_price_cents) / 100
            liability = liabilities.get(p.id, Decimal(0))
            paid_off = price - liability
            print(
                f"    Kaufpreis: {price:.2f} EUR, Restschuld: {liability:.2f} EUR, "
                f"bezahlt: {paid_off:.2f} EUR"
            )
        if p.verwalter_name or p.weg_name:
            if p.weg_name:
                print(f"    WEG: {p.weg_name}")
            if p.verwalter_name:
                print(f"    Verwalter: {p.verwalter_name}")
                if p.verwalter_contact_person:
                    print(f"      Ansprechpartner: {p.verwalter_contact_person}")
                contact = " / ".join(x for x in (p.verwalter_email, p.verwalter_phone) if x)
                if contact:
                    print(f"      {contact}")
        if (
            p.grundsteuer_objektnummer
            or p.grundsteuer_debitorennummer
            or p.grundsteuer_kassenzeichen
        ):
            refs = ", ".join(
                f"{label}={value}"
                for label, value in (
                    ("Objektnr", p.grundsteuer_objektnummer),
                    ("Debitorennr", p.grundsteuer_debitorennummer),
                    ("Kassenzeichen", p.grundsteuer_kassenzeichen),
                )
                if value
            )
            print(f"    Grundsteuer: {refs}")


def cmd_set_property_meta(conn, args: argparse.Namespace) -> None:
    property_repo.set_verwalter(
        conn,
        args.property_id,
        name=args.verwalter_name,
        contact_person=args.verwalter_contact,
        email=args.verwalter_email,
        phone=args.verwalter_phone,
        address=args.verwalter_address,
    )
    property_repo.set_weg_grundsteuer_info(
        conn,
        args.property_id,
        weg_name=args.weg_name,
        objektnummer=args.grundsteuer_objektnummer,
        debitorennummer=args.grundsteuer_debitorennummer,
        kassenzeichen=args.grundsteuer_kassenzeichen,
    )
    print(f"Property {args.property_id} meta updated.")


def cmd_set_contract_cost_types(conn, args: argparse.Namespace) -> None:
    known_codes = {code for code, _label, apportionable in all_cost_type_choices() if apportionable}
    try:
        codes = [int(c.strip()) for c in args.cost_types.split(",") if c.strip()]
    except ValueError:
        raise SystemExit(f"invalid --cost-types list: {args.cost_types}")
    unknown = [c for c in codes if c not in known_codes]
    if unknown:
        raise SystemExit(
            f"unknown/non-apportionable cost type code(s): {unknown} — "
            "run `list-cost-types` for valid apportionable codes (1-17)"
        )
    contract_repo.set_cost_type_allowlist(conn, args.contract_id, codes)
    print(f"Contract {args.contract_id} cost-type allow-list set to: {codes}")


def cmd_list_contract_cost_types(conn, args: argparse.Namespace) -> None:
    codes = contract_repo.get_cost_type_allowlist(conn, args.contract_id)
    if not codes:
        print(
            "No allow-list set — run_billing will warn and bill every recorded "
            "cost type for this contract's property."
        )
        return
    for code, label, _apportionable in all_cost_type_choices():
        if code in codes:
            print(f"  {code:>3}  {label}")


def cmd_list_cost_types(conn, args: argparse.Namespace) -> None:
    print("Umlagefähig (§ 2 BetrKV):")
    for code, label, apportionable in all_cost_type_choices():
        if apportionable:
            print(f"  {code:>3}  {label}")
    print("Nicht umlagefähig (landlord tracking only, never billed to tenants):")
    for code, label, apportionable in all_cost_type_choices():
        if not apportionable:
            print(f"  {code:>3}  {label}")


def cmd_list_invoices(conn, args: argparse.Namespace) -> None:
    for entry in invoice_repo.list_for_property_year(conn, args.property_id, args.billing_year):
        kind = "umlagefähig" if entry.is_apportionable else "NICHT umlagefähig"
        print(
            f"[{entry.id}] cost_type={entry.cost_type_code} ({kind}) "
            f"amount={entry.amount_cents / 100:.2f} vendor={entry.vendor_name} "
            f"date={entry.invoice_date}"
        )


def cmd_add_loan_payment(conn, args: argparse.Namespace) -> None:
    payment_id = financing_repo.create(
        conn,
        LoanPayment(
            id=0,
            property_id=args.property_id,
            payment_date=date.fromisoformat(args.date),
            interest_cents=round(Decimal(args.interest) * 100),
            principal_cents=round(Decimal(args.principal) * 100) if args.principal else 0,
            balance_after_cents=round(Decimal(args.balance_after) * 100),
            lender=args.lender,
            loan_account=args.loan_account,
            notes=args.notes,
        ),
    )
    print(f"Loan payment recorded: id={payment_id}")


def cmd_list_loan_payments(conn, args: argparse.Namespace) -> None:
    total_interest = Decimal(0)
    for p in financing_repo.list_for_property(conn, args.property_id):
        total_interest += Decimal(p.interest_cents) / 100
        print(
            f"[{p.id}] {p.payment_date}: Zinsen={p.interest_cents / 100:.2f} "
            f"Tilgung={p.principal_cents / 100:.2f} Saldo danach={p.balance_after_cents / 100:.2f} "
            f"({p.lender or ''})"
        )
    print(f"\nGesamtzinsen (alle Jahre): {total_interest:.2f} EUR")


def cmd_set_loan_terms(conn, args: argparse.Namespace) -> None:
    financing_repo.set_terms(
        conn,
        LoanTerms(
            property_id=args.property_id,
            lender=args.lender,
            loan_account=args.loan_account,
            annual_interest_rate_pct=Decimal(args.rate),
            monthly_principal_cents=round(Decimal(args.monthly_principal) * 100),
        ),
    )
    print(
        f"Loan terms set for property {args.property_id}: {args.rate}% p.a., {args.monthly_principal} EUR/month Tilgung."
    )


def cmd_set_loan_share(conn, args: argparse.Namespace) -> None:
    financing_repo.set_property_share(
        conn, args.loan_account, args.property_id, Decimal(args.share)
    )
    print(f"Property {args.property_id} share of '{args.loan_account}' set to {args.share}/1000.")


def cmd_show_loan_allocation(conn, args: argparse.Namespace) -> None:
    allocations = financing_repo.allocate_interest_by_property(conn, args.loan_account, args.year)
    if not allocations:
        print("No shares configured for this loan_account -- use set-loan-share first.")
        return
    for property_id, interest in sorted(allocations.items()):
        prop = property_repo.get(conn, property_id)
        label = prop.label if prop else f"property {property_id}"
        print(f"{label}: {interest:.2f} EUR Zinsen ({args.year})")
    print(f"\nGesamt: {sum(allocations.values()):.2f} EUR")


def cmd_set_purchase_price(conn, args: argparse.Namespace) -> None:
    property_repo.set_purchase_price(conn, args.property_id, round(Decimal(args.price) * 100))
    print(f"Property {args.property_id} purchase price set to {args.price} EUR.")


def cmd_set_cash_balance(conn, args: argparse.Namespace) -> None:
    wealth_repo.add_cash_snapshot(
        conn,
        round(Decimal(args.balance) * 100),
        date.fromisoformat(args.date) if args.date else date.today(),
        notes=args.notes,
    )
    print(f"Cash balance snapshot recorded: {args.balance} EUR.")


def cmd_show_wealth(conn, args: argparse.Namespace) -> None:
    summary = wealth_repo.compute_wealth_summary(conn)
    print(format_wealth_summary(summary))


def cmd_add_kassenbuch_entry(conn, args: argparse.Namespace) -> None:
    entry_id = kassenbuch_repo.create(
        conn,
        property_id=args.property_id,
        entry_date=date.fromisoformat(args.date),
        position=args.position,
        amount_patrick_cents=round(Decimal(args.patrick) * 100) if args.patrick else 0,
        amount_sven_cents=round(Decimal(args.sven) * 100) if args.sven else 0,
        amount_gemeinschaftskonto_cents=(
            round(Decimal(args.gemeinschaftskonto) * 100) if args.gemeinschaftskonto else 0
        ),
        notes=args.notes,
    )
    print(f"Kassenbuch entry recorded: id={entry_id}")


def cmd_list_kassenbuch(conn, args: argparse.Namespace) -> None:
    total = Decimal(0)
    for e in kassenbuch_repo.list_for_property(conn, args.property_id):
        total += Decimal(e.amount_total_cents) / 100
        print(
            f"[{e.id}] {e.entry_date} {e.position}: "
            f"Patrick={e.amount_patrick_cents / 100:.2f} Sven={e.amount_sven_cents / 100:.2f} "
            f"Gemeinschaftskonto={e.amount_gemeinschaftskonto_cents / 100:.2f} "
            f"Summe={e.amount_total_cents / 100:.2f}"
        )
    print(f"\nSaldo: {total:.2f} EUR")


def cmd_add_document(conn, args: argparse.Namespace) -> None:
    import shutil

    settings = load_settings()
    src = Path(args.file).expanduser()
    if not src.is_file():
        raise SystemExit(f"file not found: {src}")

    dest_dir = settings.documents_dir / str(args.property_id) / args.category
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / src.name
    if dest.exists() and dest.resolve() != src.resolve():
        stem, suffix = dest.stem, dest.suffix
        n = 2
        while dest.exists():
            dest = dest_dir / f"{stem}-{n}{suffix}"
            n += 1
    if dest.resolve() != src.resolve():
        shutil.copy2(src, dest)

    document_id = document_repo.create(
        conn,
        property_id=args.property_id,
        unit_id=args.unit_id,
        category=args.category,
        title=args.title or src.name,
        billing_year=args.year,
        file_path=str(dest),
        notes=args.notes,
        uploaded_by="cli",
    )
    print(f"Document recorded: id={document_id} path={dest}")


def cmd_list_documents(conn, args: argparse.Namespace) -> None:
    docs = document_repo.list_for_property(conn, args.property_id, category=args.category)
    if docs:
        print("Uploaded documents:")
        current_category = None
        for d in docs:
            if d.category != current_category:
                current_category = d.category
                print(f"  {current_category}:")
            year = f" ({d.billing_year})" if d.billing_year else ""
            print(f"    [{d.id}] {d.title}{year} — {d.file_path}")
    else:
        print("Uploaded documents: none")

    if args.category is not None:
        return  # generated Abrechnungen aren't filed under a document category

    runs = billing_repo.list_runs_for_property(conn, args.property_id)
    generated = [
        (run, stmt)
        for run in runs
        for stmt in billing_repo.list_statements_for_run(conn, run.id)
        if stmt.document_path
    ]
    if generated:
        print("Generated Abrechnungen:")
        for run, stmt in generated:
            print(
                f"    [{stmt.id}] {run.billing_year} {stmt.document_type} "
                f"(contract {stmt.contract_id}) — {stmt.document_path}"
            )
    else:
        print("Generated Abrechnungen: none")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("set-landlord")
    p.add_argument("--name", required=True)
    p.add_argument("--street", required=True)
    p.add_argument("--house-number", required=True)
    p.add_argument("--postal-code", required=True)
    p.add_argument("--city", required=True)
    p.add_argument("--tax-id")
    p.add_argument("--iban")
    p.add_argument("--bic")
    p.add_argument("--account-holder")
    p.add_argument("--email")
    p.add_argument("--phone")
    p.set_defaults(func=cmd_set_landlord)

    p = sub.add_parser("add-property")
    p.add_argument("--label", required=True)
    p.add_argument("--street", required=True)
    p.add_argument("--house-number", required=True)
    p.add_argument("--postal-code", required=True)
    p.add_argument("--city", required=True)
    p.add_argument("--wohnflaeche", required=True, help="total Wohnfläche in m²")
    p.add_argument("--build-year", type=int)
    p.add_argument("--pre1994-uninsulated", action="store_true")
    p.add_argument("--heating-consumption-pct", help="e.g. 70 for a 70/30 split")
    p.add_argument("--heating-combined-system", action="store_true")
    p.add_argument("--heating-remote-readable", action="store_true")
    p.add_argument("--heating-noncompliant", action="store_true")
    p.set_defaults(func=cmd_add_property)

    p = sub.add_parser("add-unit")
    p.add_argument("--property-id", type=int, required=True)
    p.add_argument("--label", required=True)
    p.add_argument("--type", choices=["apartment", "garage"], required=True)
    p.add_argument("--wohnflaeche", help="m²")
    p.add_argument("--heated", action="store_true")
    p.add_argument("--mea", help="WEG Miteigentumsanteil per mille, e.g. 7.92 for 7,92/1000")
    p.set_defaults(func=cmd_add_unit)

    p = sub.add_parser("set-unit-mea")
    p.add_argument("--unit-id", type=int, required=True)
    p.add_argument("--mea", required=True, help="WEG Miteigentumsanteil per mille, e.g. 7.92")
    p.set_defaults(func=cmd_set_unit_mea)

    p = sub.add_parser("add-tenant")
    p.add_argument("--first-name", required=True)
    p.add_argument("--last-name", required=True)
    p.add_argument("--street", required=True)
    p.add_argument("--postal-code", required=True)
    p.add_argument("--city", required=True)
    p.add_argument("--email")
    p.add_argument("--phone")
    p.add_argument("--iban")
    p.set_defaults(func=cmd_add_tenant)

    p = sub.add_parser("add-contract")
    p.add_argument("--unit-id", type=int, required=True)
    p.add_argument("--tenant-id", type=int, required=True)
    p.add_argument("--start-date", required=True, help="YYYY-MM-DD")
    p.add_argument("--end-date", help="YYYY-MM-DD")
    p.add_argument("--monthly-advance", required=True, help="Nebenkosten Vorauszahlung, EUR")
    p.add_argument("--monthly-advance-heating", help="Heizkosten Vorauszahlung, EUR")
    p.add_argument("--persons", type=int)
    p.add_argument("--deposit", help="Kaution, EUR")
    p.set_defaults(func=cmd_add_contract)

    p = sub.add_parser("set-deposit")
    p.add_argument("--contract-id", type=int, required=True)
    p.add_argument("--deposit", required=True, help="Kaution held, EUR")
    p.set_defaults(func=cmd_set_deposit)

    p = sub.add_parser("return-deposit")
    p.add_argument("--contract-id", type=int, required=True)
    p.add_argument("--amount", required=True, help="Amount actually returned, EUR")
    p.add_argument("--date", required=True, help="YYYY-MM-DD")
    p.set_defaults(func=cmd_return_deposit)

    p = sub.add_parser("add-invoice")
    p.add_argument("--property-id", type=int, required=True)
    p.add_argument("--cost-type", type=int, required=True, help="1-17, see list-cost-types")
    p.add_argument("--billing-year", type=int, required=True)
    p.add_argument("--amount", required=True, help="EUR")
    p.add_argument("--vendor")
    p.add_argument("--invoice-date", help="YYYY-MM-DD")
    p.add_argument("--description")
    p.add_argument("--source-file")
    p.set_defaults(func=cmd_add_invoice)

    p = sub.add_parser("list-properties")
    p.set_defaults(func=cmd_list_properties)

    p = sub.add_parser("list-cost-types")
    p.set_defaults(func=cmd_list_cost_types)

    p = sub.add_parser("list-invoices")
    p.add_argument("--property-id", type=int, required=True)
    p.add_argument("--billing-year", type=int, required=True)
    p.set_defaults(func=cmd_list_invoices)

    p = sub.add_parser("add-loan-payment")
    p.add_argument("--property-id", type=int, required=True)
    p.add_argument("--date", required=True, help="YYYY-MM-DD (Wert-Datum from the Kontoauszug)")
    p.add_argument("--interest", required=True, help="Sollzins for this period, EUR")
    p.add_argument("--principal", help="Tilgung for this period, EUR (default 0)")
    p.add_argument("--balance-after", required=True, help="Resulting Kontostand, EUR")
    p.add_argument("--lender", help="e.g. 'Volksbank BraWo'")
    p.add_argument("--loan-account", help="Kontonummer")
    p.add_argument("--notes")
    p.set_defaults(func=cmd_add_loan_payment)

    p = sub.add_parser("list-loan-payments")
    p.add_argument("--property-id", type=int, required=True)
    p.set_defaults(func=cmd_list_loan_payments)

    p = sub.add_parser("set-loan-terms")
    p.add_argument("--property-id", type=int, required=True)
    p.add_argument("--lender", required=True)
    p.add_argument("--loan-account", required=True)
    p.add_argument("--rate", required=True, help="Annual interest rate, %% (e.g. 4.20)")
    p.add_argument("--monthly-principal", required=True, help="Fixed monthly Tilgung, EUR")
    p.set_defaults(func=cmd_set_loan_terms)

    p = sub.add_parser("set-loan-share")
    p.add_argument("--loan-account", required=True)
    p.add_argument("--property-id", type=int, required=True)
    p.add_argument("--share", required=True, help="Miteigentumsanteil per mille, e.g. 7.92")
    p.set_defaults(func=cmd_set_loan_share)

    p = sub.add_parser("show-loan-allocation")
    p.add_argument("--loan-account", required=True)
    p.add_argument("--year", type=int, required=True)
    p.set_defaults(func=cmd_show_loan_allocation)

    p = sub.add_parser("set-purchase-price")
    p.add_argument("--property-id", type=int, required=True)
    p.add_argument("--price", required=True, help="Kaufpreis, EUR")
    p.set_defaults(func=cmd_set_purchase_price)

    p = sub.add_parser("set-cash-balance")
    p.add_argument("--balance", required=True, help="Current cash/checking balance, EUR")
    p.add_argument("--date", help="YYYY-MM-DD (default: today)")
    p.add_argument("--notes")
    p.set_defaults(func=cmd_set_cash_balance)

    p = sub.add_parser("show-wealth")
    p.set_defaults(func=cmd_show_wealth)

    p = sub.add_parser("add-kassenbuch-entry")
    p.add_argument("--property-id", type=int, required=True)
    p.add_argument("--date", required=True, help="YYYY-MM-DD")
    p.add_argument("--position", required=True, help="Description, e.g. 'Notar'")
    p.add_argument("--patrick", help="Amount paid by Patrick, EUR (negative for an outflow)")
    p.add_argument("--sven", help="Amount paid by Sven, EUR (negative for an outflow)")
    p.add_argument(
        "--gemeinschaftskonto",
        help="Amount paid from the joint account, EUR (negative for an outflow)",
    )
    p.add_argument("--notes")
    p.set_defaults(func=cmd_add_kassenbuch_entry)

    p = sub.add_parser("list-kassenbuch")
    p.add_argument("--property-id", type=int, required=True)
    p.set_defaults(func=cmd_list_kassenbuch)

    p = sub.add_parser("add-document")
    p.add_argument("--property-id", type=int, required=True)
    p.add_argument("--unit-id", type=int)
    p.add_argument(
        "--category",
        required=True,
        choices=[
            "hausverwaltung",
            "grundsteuer",
            "versicherung",
            "behoerde",
            "mietvertrag",
            "sonstige",
        ],
    )
    p.add_argument("--file", required=True, help="path to the document to file away")
    p.add_argument("--title", help="default: the file's name")
    p.add_argument("--year", type=int, help="billing year this document pertains to, if any")
    p.add_argument("--notes")
    p.set_defaults(func=cmd_add_document)

    p = sub.add_parser("list-documents")
    p.add_argument("--property-id", type=int, required=True)
    p.add_argument(
        "--category",
        choices=[
            "hausverwaltung",
            "grundsteuer",
            "versicherung",
            "behoerde",
            "mietvertrag",
            "sonstige",
        ],
    )
    p.set_defaults(func=cmd_list_documents)

    p = sub.add_parser("set-property-meta")
    p.add_argument("--property-id", type=int, required=True)
    p.add_argument("--verwalter-name")
    p.add_argument("--verwalter-contact", help="Ansprechpartner/in beim Verwalter")
    p.add_argument("--verwalter-email")
    p.add_argument("--verwalter-phone")
    p.add_argument("--verwalter-address")
    p.add_argument("--weg-name", help="e.g. 'Wohnungseigentümergemeinschaft Hochring 32, WOB'")
    p.add_argument("--grundsteuer-objektnummer")
    p.add_argument("--grundsteuer-debitorennummer")
    p.add_argument("--grundsteuer-kassenzeichen")
    p.set_defaults(func=cmd_set_property_meta)

    p = sub.add_parser("set-contract-cost-types")
    p.add_argument("--contract-id", type=int, required=True)
    p.add_argument(
        "--cost-types",
        required=True,
        help="comma-separated BetrKV codes actually named in the Mietvertrag, e.g. '8,9,11,13'",
    )
    p.set_defaults(func=cmd_set_contract_cost_types)

    p = sub.add_parser("list-contract-cost-types")
    p.add_argument("--contract-id", type=int, required=True)
    p.set_defaults(func=cmd_list_contract_cost_types)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    settings = load_settings()
    conn = connect(settings.db_path)
    try:
        args.func(conn, args)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
