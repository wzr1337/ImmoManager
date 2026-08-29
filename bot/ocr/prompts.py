"""Tool schema and system prompt for one-shot invoice data extraction.

This is the ONLY place in the codebase an LLM call happens. It extracts data;
it never computes a Euro amount, distribution key, or apportionment -- that's
calc_engine's job, in plain deterministic code (CLAUDE.md)."""

EXTRACTION_SYSTEM_PROMPT = (
    "You extract structured data from a scanned German rental-property invoice "
    "(Rechnung/Beleg). Extract exactly what's printed -- do not calculate, estimate, "
    "or invent any value. If a field isn't legible or isn't present, omit it or set "
    "confidence low; never guess."
)

EXTRACT_INVOICE_TOOL = {
    "name": "extract_invoice",
    "description": "Records the extracted fields from a scanned invoice image.",
    "input_schema": {
        "type": "object",
        "properties": {
            "vendor": {"type": "string", "description": "Name of the invoicing company/vendor."},
            "amount": {
                "type": "string",
                "description": "Total invoice amount as a plain decimal string, e.g. '812.21'. "
                "German decimal commas must be converted to a decimal point.",
            },
            "currency": {"type": "string", "description": "ISO currency code, e.g. 'EUR'."},
            "invoice_date": {
                "type": "string",
                "description": "Invoice date in ISO format YYYY-MM-DD.",
            },
            "suggested_cost_type": {
                "type": ["integer", "null"],
                "description": (
                    "Best-guess § 2 BetrKV cost type code (1-17) this invoice likely belongs "
                    "to, or null if unclear. 1=Grundsteuer, 2=Wasserversorgung, "
                    "3=Entwaesserung, 4=Heizung, 5=Warmwasser, 7=Aufzug, "
                    "8=Strassenreinigung/Muellabfuhr, 9=Gebaeudereinigung/Ungeziefer, "
                    "10=Gartenpflege, 11=Beleuchtung, 12=Schornsteinreinigung, "
                    "13=Versicherung, 14=Hauswart, 16=Waeschepflege, 17=Sonstige. "
                    "If this looks like a repair/maintenance invoice (Reparatur, "
                    "Instandhaltung) rather than a recurring operating cost, set this to "
                    "null and set likely_non_apportionable to true instead."
                ),
            },
            "likely_non_apportionable": {
                "type": "boolean",
                "description": (
                    "True if this looks like a repair, maintenance, or administrative cost "
                    "that is NOT apportionable to tenants under BetrKV (e.g. Reparatur, "
                    "Instandhaltung, Modernisierung) rather than a recurring operating cost."
                ),
            },
            "confidence": {
                "type": "string",
                "enum": ["high", "medium", "low"],
                "description": "Overall confidence in the extracted amount and date.",
            },
        },
        "required": ["confidence"],
    },
}
