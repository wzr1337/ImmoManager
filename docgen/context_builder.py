"""Converts calc_engine StatementData into docxtpl render contexts. Pure — the only
place presentation formatting happens (see docgen/format.py). No I/O, no logic that
affects the actual numbers; that all already happened in calc_engine.
"""

from __future__ import annotations

from calc_engine.statement import BetriebskostenStatement, HeizkostenStatement, WasserStatement
from docgen.format import fmt_date, fmt_money, fmt_number
from models.landlord import LandlordProfile


def _balance_label(balance) -> str:
    return "Nachzahlung" if balance > 0 else "Guthaben"


def betriebskosten_context(statement: BetriebskostenStatement, landlord: LandlordProfile) -> dict:
    return {
        "landlord": {"name": landlord.name, "address": landlord.address},
        "tenant_name": statement.tenant_name,
        "tenant_address": statement.tenant_address,
        "unit_label": statement.unit_label,
        "property_label": statement.property_label,
        "property_address": statement.property_address,
        "billing_period_start": fmt_date(statement.billing_period_start),
        "billing_period_end": fmt_date(statement.billing_period_end),
        "deadline_date": fmt_date(statement.deadline_date),
        "cost_lines": [
            {
                "cost_type_name": line.cost_type_name,
                "total_building_cost": fmt_money(line.total_building_cost),
                "distribution_key_description": line.distribution_key_description,
                "tenant_share_calculation": line.tenant_share_calculation,
                "tenant_share_amount": fmt_money(line.tenant_share_amount),
            }
            for line in statement.cost_lines
        ],
        "total_tenant_cost": fmt_money(statement.total_tenant_cost),
        "advance_payments_total": fmt_money(statement.advance_payments_total),
        "balance": fmt_money(abs(statement.balance)),
        "balance_label": _balance_label(statement.balance),
    }


def wasser_context(statement: WasserStatement, landlord: LandlordProfile) -> dict:
    return {
        "landlord": {"name": landlord.name, "address": landlord.address},
        "tenant_name": statement.tenant_name,
        "tenant_address": statement.tenant_address,
        "unit_label": statement.unit_label,
        "property_label": statement.property_label,
        "property_address": statement.property_address,
        "billing_period_start": fmt_date(statement.billing_period_start),
        "billing_period_end": fmt_date(statement.billing_period_end),
        "meter_lines": [
            {
                "meter_id": m.meter_id,
                "meter_type": m.meter_type,
                "reading_old": fmt_number(m.reading_old, decimals=0),
                "reading_new": fmt_number(m.reading_new, decimals=0),
                "consumption": fmt_number(m.consumption, decimals=0),
            }
            for m in statement.meter_lines
        ],
        "tenant_consumption_total": fmt_number(statement.tenant_consumption_total, decimals=3),
        "building_consumption_total": fmt_number(statement.building_consumption_total, decimals=3),
        "total_building_cost": fmt_money(statement.total_building_cost),
        "tenant_share_calculation": statement.tenant_share_calculation,
        "tenant_share_amount": fmt_money(statement.tenant_share_amount),
        "advance_payments_total": fmt_money(statement.advance_payments_total),
        "balance": fmt_money(abs(statement.balance)),
        "balance_label": _balance_label(statement.balance),
    }


def heizkosten_context(statement: HeizkostenStatement, landlord: LandlordProfile) -> dict:
    def pool_ctx(pool):
        return {
            "grundkosten_total": fmt_money(pool.grundkosten_total),
            "verbrauch_total": fmt_money(pool.verbrauch_total),
            "tenant_grundkosten": fmt_money(pool.tenant_grundkosten),
            "tenant_verbrauch": fmt_money(pool.tenant_verbrauch),
            "grundkosten_calculation": pool.grundkosten_calculation,
            "verbrauch_calculation": pool.verbrauch_calculation,
        }

    return {
        "landlord": {"name": landlord.name, "address": landlord.address},
        "tenant_name": statement.tenant_name,
        "tenant_address": statement.tenant_address,
        "unit_label": statement.unit_label,
        "property_label": statement.property_label,
        "property_address": statement.property_address,
        "billing_period_start": fmt_date(statement.billing_period_start),
        "billing_period_end": fmt_date(statement.billing_period_end),
        "gesamtkosten_liegenschaft": fmt_money(statement.gesamtkosten_liegenschaft),
        "co2_landlord_share": fmt_money(statement.co2_landlord_share),
        "heating": pool_ctx(statement.heating),
        "warmwater": pool_ctx(statement.warmwater) if statement.warmwater else None,
        "metering_compliant": statement.metering_compliant,
        "tenant_total_before_penalty": fmt_money(statement.tenant_total_before_penalty),
        "tenant_total": fmt_money(statement.tenant_total),
        "advance_payments_total": fmt_money(statement.advance_payments_total),
        "balance": fmt_money(abs(statement.balance)),
        "balance_label": _balance_label(statement.balance),
    }
