"""Menu navigation: /start, /menu, and the inline-keyboard sub-navigation for
Properties, Tenants, and cost breakdowns. All read-only browsing; the Mieterwechsel
flow (which mutates data) lives in bot/handlers/mieterwechsel.py."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import CallbackQueryHandler, CommandHandler, ContextTypes

from bot.context import get_conn
from calc_engine import statement as st
from config.cost_types import label_for
from db.repositories import contract_repo, invoice_repo, property_repo, tenant_repo
from docgen.format import fmt_money

TOP_MENU = InlineKeyboardMarkup(
    [
        [InlineKeyboardButton("Properties", callback_data="props")],
        [InlineKeyboardButton("Tenants", callback_data="tenants")],
        [InlineKeyboardButton("Pending invoices", callback_data="pending")],
    ]
)


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "ImmoManager. Send a photo of an invoice to record it, or use the menu below.",
        reply_markup=TOP_MENU,
    )


async def cmd_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("Menu:", reply_markup=TOP_MENU)


async def on_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    data = query.data
    conn = get_conn(context)
    try:
        if data == "menu":
            await query.edit_message_text("Menu:", reply_markup=TOP_MENU)
        elif data == "props":
            await _show_properties(query, conn)
        elif data.startswith("prop:") and data.count(":") == 1:
            await _show_property_detail(query, conn, int(data.split(":")[1]))
        elif data.startswith("prop:") and ":costs:" in data:
            _, property_id, _, year = data.split(":")
            await _show_property_costs(query, conn, int(property_id), int(year))
        elif data == "tenants":
            await _show_tenants(query, conn)
        elif data.startswith("tenant:") and data.count(":") == 1:
            await _show_tenant_detail(query, conn, int(data.split(":")[1]))
        elif data.startswith("tenant:") and ":costs:" in data:
            _, tenant_id, _, year = data.split(":")
            await _show_tenant_costs(query, conn, int(tenant_id), int(year))
        elif data == "pending":
            await query.edit_message_text(
                "Pending invoices: use /pending (see bot/handlers/invoice_intake.py)."
            )
    finally:
        conn.close()


async def _show_properties(query, conn) -> None:
    properties = property_repo.list_all(conn)
    if not properties:
        await query.edit_message_text("No properties yet.")
        return
    buttons = [
        [
            InlineKeyboardButton(
                f"{p.label} ({p.total_wohnflaeche_m2} m²)", callback_data=f"prop:{p.id}"
            )
        ]
        for p in properties
    ]
    buttons.append([InlineKeyboardButton("<< Menu", callback_data="menu")])
    await query.edit_message_text("Properties:", reply_markup=InlineKeyboardMarkup(buttons))


async def _show_property_detail(query, conn, property_id: int) -> None:
    property_ = property_repo.get(conn, property_id)
    if property_ is None:
        await query.edit_message_text("Property not found.")
        return
    units = property_repo.list_units(conn, property_id)
    lines = [
        f"{property_.label}",
        property_.address,
        f"Gesamtwohnfläche: {property_.total_wohnflaeche_m2} m²",
        "",
    ]
    lines.append("Units:")
    for u in units:
        lines.append(f"  [{u.id}] {u.label} ({u.unit_type}, {u.wohnflaeche_m2} m²)")

    year = date.today().year
    buttons = [
        [
            InlineKeyboardButton(
                f"Cost breakdown {year}", callback_data=f"prop:{property_id}:costs:{year}"
            )
        ],
        [InlineKeyboardButton("<< Properties", callback_data="props")],
    ]
    await query.edit_message_text("\n".join(lines), reply_markup=InlineKeyboardMarkup(buttons))


async def _show_property_costs(query, conn, property_id: int, year: int) -> None:
    property_ = property_repo.get(conn, property_id)
    apportionable = invoice_repo.totals_by_cost_type(conn, property_id, year)
    non_apportionable = invoice_repo.list_non_apportionable_for_property_year(
        conn, property_id, year
    )

    lines = [f"{property_.label} — cost breakdown {year}", "", "Umlagefähig (apportionable):"]
    if apportionable:
        for code, total in sorted(apportionable.items()):
            lines.append(f"  {label_for(code)}: {fmt_money(total)}")
        lines.append(f"  Total: {fmt_money(sum(apportionable.values()))}")
    else:
        lines.append("  (none recorded)")

    lines.append("")
    lines.append("Nicht umlagefähig (repairs, admin — landlord only):")
    if non_apportionable:
        total_non = Decimal(0)
        for entry in non_apportionable:
            amount = Decimal(entry.amount_cents) / 100
            total_non += amount
            lines.append(
                f"  {label_for(entry.cost_type_code)} ({entry.vendor_name}): {fmt_money(amount)}"
            )
        lines.append(f"  Total: {fmt_money(total_non)}")
    else:
        lines.append("  (none recorded)")

    buttons = [[InlineKeyboardButton("<< Property", callback_data=f"prop:{property_id}")]]
    await query.edit_message_text("\n".join(lines), reply_markup=InlineKeyboardMarkup(buttons))


async def _show_tenants(query, conn) -> None:
    tenants = tenant_repo.list_all(conn)
    if not tenants:
        await query.edit_message_text("No tenants yet.")
        return
    buttons = [[InlineKeyboardButton(t.full_name, callback_data=f"tenant:{t.id}")] for t in tenants]
    buttons.append([InlineKeyboardButton("<< Menu", callback_data="menu")])
    await query.edit_message_text("Tenants:", reply_markup=InlineKeyboardMarkup(buttons))


async def _show_tenant_detail(query, conn, tenant_id: int) -> None:
    tenant = tenant_repo.get(conn, tenant_id)
    if tenant is None:
        await query.edit_message_text("Tenant not found.")
        return

    lines = [tenant.full_name, tenant.address, ""]
    contracts = contract_repo.list_for_tenant(conn, tenant_id)
    active = [c for c in contracts if c.end_date is None or c.end_date >= date.today()]
    if active:
        for c in active:
            unit = property_repo.get_unit(conn, c.unit_id)
            lines.append(f"Current: {unit.label} since {c.start_date.isoformat()}")
    else:
        lines.append("No active contract.")

    year = date.today().year
    buttons = []
    if active:
        buttons.append(
            [
                InlineKeyboardButton(
                    f"Cost breakdown {year}", callback_data=f"tenant:{tenant_id}:costs:{year}"
                )
            ]
        )
        buttons.append(
            [InlineKeyboardButton("Mieterwechsel", callback_data=f"wechsel_start:{active[0].id}")]
        )
    buttons.append([InlineKeyboardButton("<< Tenants", callback_data="tenants")])
    await query.edit_message_text("\n".join(lines), reply_markup=InlineKeyboardMarkup(buttons))


async def _show_tenant_costs(query, conn, tenant_id: int, year: int) -> None:
    tenant = tenant_repo.get(conn, tenant_id)
    contracts = [
        c
        for c in contract_repo.list_for_tenant(conn, tenant_id)
        if c.end_date is None or c.end_date >= date(year, 1, 1)
    ]
    if not contracts:
        await query.edit_message_text(f"No contract for {tenant.full_name} in {year}.")
        return
    contract = contracts[0]
    unit = property_repo.get_unit(conn, contract.unit_id)
    property_ = property_repo.get(conn, unit.property_id)
    units = property_repo.list_units(conn, unit.property_id)
    wohnflaeche_weights = {u.id: u.wohnflaeche_m2 for u in units if u.wohnflaeche_m2 is not None}

    cost_totals = invoice_repo.totals_by_cost_type(conn, unit.property_id, year)
    if not cost_totals:
        await query.edit_message_text(
            f"No cost entries recorded for {property_.label} in {year} yet."
        )
        return

    period_start, period_end = date(year, 1, 1), date(year, 12, 31)
    statement = st.build_betriebskosten_statement(
        tenant_name=tenant.full_name,
        tenant_address=tenant.address,
        unit_label=unit.label,
        property_label=property_.label,
        property_address=property_.address,
        billing_period_start=period_start,
        billing_period_end=period_end,
        deadline_date=date(year + 1, 12, 31),
        contract_start=contract.start_date,
        contract_end=contract.end_date,
        tenant_unit_id=unit.id,
        cost_totals_by_type=cost_totals,
        distribution_key_by_type={code: "wohnflaeche" for code in cost_totals},
        weight_maps={"wohnflaeche": st.WeightMap("wohnflaeche", "m²", wohnflaeche_weights)},
        advance_payments_total=Decimal(contract.monthly_vorauszahlung_nebenkosten_cents) / 100 * 12,
    )

    lines = [f"{tenant.full_name} — preview {year} (not an official statement)", ""]
    for line in statement.cost_lines:
        lines.append(f"  {line.cost_type_name}: {fmt_money(line.tenant_share_amount)}")
    lines.append("")
    lines.append(f"Total: {fmt_money(statement.total_tenant_cost)}")
    lines.append(f"Vorauszahlungen: {fmt_money(statement.advance_payments_total)}")
    label = "Nachzahlung" if statement.balance > 0 else "Guthaben"
    lines.append(f"{label}: {fmt_money(abs(statement.balance))}")

    buttons = [[InlineKeyboardButton("<< Tenant", callback_data=f"tenant:{tenant_id}")]]
    await query.edit_message_text("\n".join(lines), reply_markup=InlineKeyboardMarkup(buttons))


COMMAND_HANDLERS = [
    CommandHandler("start", cmd_start),
    CommandHandler("menu", cmd_menu),
]
CALLBACK_HANDLERS = [
    CallbackQueryHandler(on_callback, pattern=r"^(menu|props|prop:|tenants|tenant:|pending)"),
]
