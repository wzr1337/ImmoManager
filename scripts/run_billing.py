"""Produces a full Betriebskostenabrechnung billing run for a property/year,
end-to-end from real DB data: gathers cost entries and unit Wohnfläche, computes
each active contract's statement via calc_engine, renders the .docx, and records
the result in billing_run_statements.

Usage:
    python -m scripts.run_billing --property-id 1 --billing-year 2025

Wasser- and Heizkostenabrechnung generation needs building-level inputs the schema
doesn't (yet) capture as structured data -- combined-system split, fuel invoice
totals, CO2 tier/emission inputs (docs/legal-requirements.md §1/§5). Until that's
wired up, generate those two via calc_engine.statement.build_wasser_statement /
build_heizkosten_statement directly (see calc_engine/tests/test_statement.py for a
full worked example) with a small ad-hoc script per property/year.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from datetime import date
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from calc_engine import proration
from calc_engine import statement as st
from config.settings import load_settings
from db.connection import connect
from db.repositories import (
    billing_repo,
    contract_repo,
    invoice_repo,
    landlord_repo,
    property_repo,
    tenant_repo,
)
from docgen import context_builder, render
from docgen.render import slug


def _decimal_default(obj):
    if isinstance(obj, Decimal):
        return str(obj)
    if isinstance(obj, date):
        return obj.isoformat()
    raise TypeError(f"not JSON serializable: {obj!r}")


def run(
    conn, *, property_id: int, billing_year: int, output_dir: Path, template_path: Path
) -> None:
    landlord = landlord_repo.get(conn)
    if landlord is None:
        raise SystemExit("no landlord profile set — run `scripts.cli set-landlord` first")

    property_ = property_repo.get(conn, property_id)
    if property_ is None:
        raise SystemExit(f"no such property: {property_id}")

    units = property_repo.list_units(conn, property_id)
    period_start = date(billing_year, 1, 1)
    period_end = date(billing_year, 12, 31)

    # Full-building weight map (every unit, occupied or not) -- vacancy is handled
    # afterwards by dropping shares, never by shrinking this map beforehand. See
    # calc_engine/vacancy.py.
    wohnflaeche_weights = {u.id: u.wohnflaeche_m2 for u in units if u.wohnflaeche_m2 is not None}

    active_contracts = []
    for unit in units:
        active_contracts.extend(
            contract_repo.active_for_unit_in_period(conn, unit.id, period_start, period_end)
        )
    if not active_contracts:
        raise SystemExit(f"no contracts active for property {property_id} in {billing_year}")
    occupied_unit_ids = {c.unit_id for c in active_contracts}

    cost_totals = invoice_repo.totals_by_cost_type(conn, property_id, billing_year)
    if not cost_totals:
        raise SystemExit(f"no cost entries recorded for property {property_id} in {billing_year}")

    # § 556a BGB default: Wohnfläche for every cost type, unless a contract
    # specifies a different key for that cost type (not yet wired up here -- see
    # contract_cost_type_keys / db/repositories/contract_repo.py::get_cost_type_keys).
    distribution_key_by_type = {code: "wohnflaeche" for code in cost_totals}
    weight_maps = {"wohnflaeche": st.WeightMap("wohnflaeche", "m²", wohnflaeche_weights)}

    run_id = billing_repo.create_run(
        conn,
        property_id=property_id,
        billing_year=billing_year,
        period_start=period_start,
        period_end=period_end,
    )
    billing_run = billing_repo.get_run(conn, run_id)

    for contract in active_contracts:
        unit = next(u for u in units if u.id == contract.unit_id)
        if unit.id not in occupied_unit_ids:
            continue  # defensive; occupied_unit_ids is derived from active_contracts itself

        tenant = tenant_repo.get(conn, contract.tenant_id)
        advance_payments_total = (
            Decimal(contract.monthly_vorauszahlung_nebenkosten_cents) / 100 * 12
        )

        statement = st.build_betriebskosten_statement(
            tenant_name=tenant.full_name,
            tenant_address=tenant.address,
            unit_label=unit.label,
            property_label=property_.label,
            property_address=property_.address,
            billing_period_start=period_start,
            billing_period_end=period_end,
            deadline_date=billing_run.deadline_date,
            contract_start=contract.start_date,
            contract_end=contract.end_date,
            tenant_unit_id=unit.id,
            cost_totals_by_type=cost_totals,
            distribution_key_by_type=distribution_key_by_type,
            weight_maps=weight_maps,
            advance_payments_total=advance_payments_total,
        )

        context = context_builder.betriebskosten_context(statement, landlord)
        output_path = render.render_statement(
            template_path=template_path,
            context=context,
            output_dir=output_dir,
            property_slug=slug(property_.label),
            unit_label=unit.label,
            tenant_lastname=tenant.last_name,
            billing_year=billing_year,
            document_type="betriebskosten",
        )

        occupied, total_period_days = _occupied_days(period_start, period_end, contract)
        billing_repo.save_statement(
            conn,
            billing_run_id=run_id,
            contract_id=contract.id,
            document_type="betriebskosten",
            document_path=str(output_path),
            total_costs=statement.total_tenant_cost,
            advance_payments=statement.advance_payments_total,
            balance=statement.balance,
            calculation_snapshot_json=json.dumps(asdict(statement), default=_decimal_default),
            proration_days=occupied,
            proration_total_days=total_period_days,
        )
        print(
            f"{tenant.full_name} ({unit.label}): {output_path.name} — balance {statement.balance}"
        )

    billing_repo.set_run_status(conn, run_id, "generated")
    print(f"Billing run {run_id} complete: {len(active_contracts)} statement(s) generated.")


def _occupied_days(period_start: date, period_end: date, contract) -> tuple[int, int]:
    return proration.occupied_days(period_start, period_end, contract.start_date, contract.end_date)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--property-id", type=int, required=True)
    parser.add_argument("--billing-year", type=int, required=True)
    parser.add_argument(
        "--template",
        type=Path,
        default=Path(__file__).resolve().parent.parent
        / "docgen"
        / "templates"
        / "betriebskostenabrechnung.docx",
    )
    args = parser.parse_args()

    settings = load_settings()
    conn = connect(settings.db_path)
    try:
        run(
            conn,
            property_id=args.property_id,
            billing_year=args.billing_year,
            output_dir=settings.generated_dir / str(args.property_id) / str(args.billing_year),
            template_path=args.template,
        )
    finally:
        conn.close()


if __name__ == "__main__":
    main()
