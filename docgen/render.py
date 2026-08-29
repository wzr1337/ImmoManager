"""Renders a docxtpl template with a context dict and saves the result, with a
cheap post-render sanity check for unresolved {{ }} / {% %} artifacts — docxtpl
leaves these verbatim in the output when the context is missing a key, which is a
much cheaper way to catch a context bug than a human noticing it in Word."""

from __future__ import annotations

import re
import zipfile
from pathlib import Path

from docxtpl import DocxTemplate

_UNRESOLVED_PATTERN = re.compile(r"\{\{|\}\}|\{%|%\}")


def render_statement(
    *,
    template_path: Path,
    context: dict,
    output_dir: Path,
    property_slug: str,
    unit_label: str,
    tenant_lastname: str,
    billing_year: int,
    document_type: str,
) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    filename = (
        f"{property_slug}_{slug(unit_label)}_{slug(tenant_lastname)}_"
        f"{billing_year}_{document_type}.docx"
    )
    output_path = output_dir / filename

    doc = DocxTemplate(template_path)
    doc.render(context)
    doc.save(output_path)

    _check_no_unresolved_placeholders(output_path)
    return output_path


_UMLAUT_MAP = str.maketrans(
    {"ä": "ae", "ö": "oe", "ü": "ue", "Ä": "Ae", "Ö": "Oe", "Ü": "Ue", "ß": "ss"}
)


def slug(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9]+", "-", value.translate(_UMLAUT_MAP)).strip("-").lower()


def _check_no_unresolved_placeholders(docx_path: Path) -> None:
    with zipfile.ZipFile(docx_path) as archive:
        xml = archive.read("word/document.xml").decode("utf-8", errors="ignore")
    if _UNRESOLVED_PATTERN.search(xml):
        raise ValueError(
            f"{docx_path} contains unresolved template placeholders — the render "
            "context is missing a key the template references. Check the template's "
            "Jinja tags against docgen/context_builder.py's output keys."
        )
