"""One-shot invoice extraction via the Anthropic Messages API on AWS Bedrock (EU
inference profile, so tenant data stays in the EU) -- not the Agent SDK. A single vision call per invoice (CLAUDE.md: minimize LLM calls, one
extraction call per invoice, not per property/tenant/statement), forced tool use for
a strict JSON-shaped result. Deliberately lightweight for a Raspberry Pi: no
subprocess, no agentic loop, no larger system prompt than this one task needs."""

from __future__ import annotations

import base64
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation

import anthropic

from bot.ocr.prompts import EXTRACT_INVOICE_TOOL, EXTRACTION_SYSTEM_PROMPT

PDF_MEDIA_TYPE = "application/pdf"


@dataclass(frozen=True)
class LineItem:
    description: str
    amount: Decimal
    suggested_cost_type: int | None


@dataclass(frozen=True)
class ExtractionResult:
    vendor: str | None
    amount: Decimal | None
    currency: str | None
    invoice_date: date | None
    suggested_cost_type: int | None
    likely_non_apportionable: bool
    confidence: str
    raw_response_json: str
    billing_year: int | None = None
    line_items: tuple[LineItem, ...] = ()


def extract_invoice(
    *,
    model_id: str,
    aws_region: str,
    image_bytes_list: list[bytes],
    media_type: str = "image/jpeg",
) -> ExtractionResult:
    """`image_bytes_list` holds one entry per page of a (possibly multi-page)
    invoice, all sent in a single call -- see bot/handlers/invoice_intake.py's
    media_group buffering. With media_type application/pdf it holds one whole PDF."""
    client = anthropic.AnthropicBedrock(aws_region=aws_region)

    block_type = "document" if media_type == PDF_MEDIA_TYPE else "image"
    content = [
        {
            "type": block_type,
            "source": {
                "type": "base64",
                "media_type": media_type,
                "data": base64.standard_b64encode(image_bytes).decode("ascii"),
            },
        }
        for image_bytes in image_bytes_list
    ]
    content.append({"type": "text", "text": "Extract the invoice data from the document above."})

    response = client.messages.create(
        model=model_id,
        max_tokens=4096,
        system=EXTRACTION_SYSTEM_PROMPT,
        tools=[EXTRACT_INVOICE_TOOL],
        tool_choice={"type": "tool", "name": "extract_invoice"},
        messages=[{"role": "user", "content": content}],
    )

    tool_use = next(block for block in response.content if block.type == "tool_use")
    return _parse_tool_input(tool_use.input, raw_response_json=response.model_dump_json())


def _parse_tool_input(data: dict, *, raw_response_json: str) -> ExtractionResult:
    amount = None
    if data.get("amount"):
        try:
            amount = Decimal(str(data["amount"]).replace(",", "."))
        except InvalidOperation:
            amount = None

    invoice_date = None
    if data.get("invoice_date"):
        try:
            invoice_date = date.fromisoformat(data["invoice_date"])
        except ValueError:
            invoice_date = None

    return ExtractionResult(
        billing_year=data.get("billing_year"),
        line_items=_parse_line_items(data.get("line_items")),
        vendor=data.get("vendor"),
        amount=amount,
        currency=data.get("currency"),
        invoice_date=invoice_date,
        suggested_cost_type=data.get("suggested_cost_type"),
        likely_non_apportionable=bool(data.get("likely_non_apportionable", False)),
        confidence=data.get("confidence", "low"),
        raw_response_json=raw_response_json,
    )


def _parse_line_items(raw_items: list | None) -> tuple[LineItem, ...]:
    items = []
    for raw in raw_items or []:
        try:
            amount = Decimal(str(raw["amount"]).replace(",", "."))
            description = raw["description"]
        except (KeyError, InvalidOperation):
            continue
        items.append(LineItem(description, amount, raw.get("suggested_cost_type")))
    return tuple(items)
