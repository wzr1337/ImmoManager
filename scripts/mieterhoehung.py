"""Checks and drafts a Mieterhöhungsverlangen (§ 558 BGB) for one contract.

Usage:
    python -m scripts.mieterhoehung --contract-id 2 --current-rent 700 --percent 3 \
        --rent-3y-ago 680 --last-increase 2025-03-15 --vergleichsmiete 760 \
        --begruendung "Mietspiegel 2025, Feld F4"

Rents are Nettokaltmiete and are not stored in the DB, so they are passed in. Exits
without writing a letter if any § 558 rule is violated."""

from __future__ import annotations

import argparse
import sys
from datetime import date
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from calc_engine import rent_increase
from config.settings import load_settings
from db.connection import connect
from db.repositories import contract_repo, landlord_repo, property_repo, tenant_repo
from docgen import brief
from docgen.render import slug


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--contract-id", type=int, required=True)
    parser.add_argument("--current-rent", type=Decimal, required=True)
    parser.add_argument("--percent", type=Decimal, required=True)
    parser.add_argument("--rent-3y-ago", type=Decimal, required=True)
    parser.add_argument("--last-increase", type=date.fromisoformat)
    parser.add_argument("--vergleichsmiete", type=Decimal)
    parser.add_argument("--kappungsgrenze", type=Decimal, choices=[Decimal("20"), Decimal("15")])
    parser.add_argument("--begruendung", required=True)
    parser.add_argument("--zugang", type=date.fromisoformat, default=date.today())
    args = parser.parse_args()

    settings = load_settings()
    conn = connect(settings.db_path)
    try:
        landlord = landlord_repo.get(conn)
        contract = contract_repo.get(conn, args.contract_id)
        tenant = tenant_repo.get(conn, contract.tenant_id)
        unit = next(
            u
            for p in property_repo.list_all(conn)
            for u in property_repo.list_units(conn, p.id)
            if u.id == contract.unit_id
        )
        property_ = property_repo.get(conn, unit.property_id)
    finally:
        conn.close()

    new_rent = rent_increase.increase_by_percent(args.current_rent, args.percent)
    check = rent_increase.check_rent_increase(
        zugang=args.zugang,
        current_rent=args.current_rent,
        new_rent=new_rent,
        last_increase_effective=args.last_increase,
        rent_three_years_before=args.rent_3y_ago,
        kappungsgrenze_pct=args.kappungsgrenze or Decimal("20"),
        vergleichsmiete=args.vergleichsmiete,
    )
    print(
        f"New rent {check.new_rent}, effective {check.effective_date}, "
        f"Zustimmung until {check.zustimmungsfrist_end}"
    )
    if not check.is_valid:
        print("NOT sent -- violations:")
        for violation in check.violations:
            print(f"  - {violation}")
        raise SystemExit(1)

    content = brief.mieterhoehung_schreiben(
        landlord=landlord,
        tenant=tenant,
        unit_label=unit.label,
        property_address=property_.address,
        current_rent=args.current_rent,
        check=check,
        begruendung=args.begruendung,
        today=args.zugang,
    )
    output = (
        settings.generated_dir
        / "mieterhoehung"
        / (f"{slug(unit.label)}_{slug(tenant.last_name)}_{check.effective_date.isoformat()}.docx")
    )
    print(brief.render_brief(content, output))


if __name__ == "__main__":
    main()
