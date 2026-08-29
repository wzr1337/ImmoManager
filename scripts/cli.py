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
    contract_repo,
    invoice_repo,
    landlord_repo,
    property_repo,
    tenant_repo,
)
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
        ),
    )
    print(f"Unit created: id={unit_id}")


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
        ),
    )
    print(f"Contract created: id={contract_id}")


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
    for p in property_repo.list_all(conn):
        print(f"[{p.id}] {p.label} — {p.address} ({p.total_wohnflaeche_m2} m²)")
        for u in property_repo.list_units(conn, p.id):
            print(f"    [{u.id}] {u.label} ({u.unit_type}, {u.wohnflaeche_m2} m²)")


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
    p.set_defaults(func=cmd_add_unit)

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
    p.set_defaults(func=cmd_add_contract)

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
