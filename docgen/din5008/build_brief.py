#!/usr/bin/env python3
"""Füllt die DIN-5008-Vorlage aus einer JSON-Datei. Aufruf: build_brief.py inhalt.json ausgabe.docx"""
import copy, json, sys
from pathlib import Path
from docx import Document
from docx.oxml.ns import qn
from docx.shared import Cm
from docx.text.paragraph import Paragraph

TEMPLATE = Path(__file__).resolve().parent / "vorlage.docx"

# Feld -> Erkennungsmerkmal im Original-Text des Textfelds
MARKER = {
    "footer": "Kunden GmbH & Co. KG · Volksbank",
    "betreff": "Hier steht Ihre Betreffzeile",
    "datum": "Musterstadt, den",
    "logo": "Platzieren Sie hier",
    "body": "Sehr geehrte",
    "empfaenger": "Kunden GmbH & Co. KG",
    "absender": "Ihr Firmenname GmbH, Musterweg",
    "kontakt": "Telefonnr",
}


def fill_runs(p, text, rpr):
    """Text -> Runs; \\n = Zeilenumbruch, \\t = Tab."""
    for i, line in enumerate(text.split("\n")):
        for j, part in enumerate(line.split("\t")):
            r = p.makeelement(qn("w:r"), {})
            if rpr is not None:
                r.append(copy.deepcopy(rpr))
            if i and not j:
                r.append(r.makeelement(qn("w:br"), {}))
            if j:
                r.append(r.makeelement(qn("w:tab"), {}))
            if part:
                t = r.makeelement(qn("w:t"), {"{http://www.w3.org/XML/1998/namespace}space": "preserve"})
                t.text = part
                r.append(t)
            p.append(r)


def set_paragraphs(tb, lines, proto_idx=0):
    ps = tb.findall(qn("w:p"))
    proto = ps[min(proto_idx, len(ps) - 1)]
    ppr = proto.find(qn("w:pPr"))
    r0 = proto.find(qn("w:r"))
    rpr = r0.find(qn("w:rPr")) if r0 is not None else None
    for p in ps:
        tb.remove(p)
    for line in lines:
        p = tb.makeelement(qn("w:p"), {})
        if ppr is not None:
            p.append(copy.deepcopy(ppr))
        fill_runs(p, line, rpr)
        tb.append(p)


def as_list(v):
    return v if isinstance(v, list) else [v]


def build(data, out):
    doc = Document(TEMPLATE)
    for ac in list(doc.element.body.iter("{http://schemas.openxmlformats.org/markup-compatibility/2006}AlternateContent")):
        if any(e.get("name") == "Textfeld 3" for e in ac.iter("{http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing}docPr")):
            ac.getparent().remove(ac)  # gestrichelter Logo-Platzhalterrahmen
    boxes = list(doc.element.body.iter(qn("w:txbxContent")))
    # Reihenfolge: Choice (DrawingML) vor Fallback (VML) – beide werden befüllt
    for key, marker in MARKER.items():
        if key != "logo" and key not in data:
            continue
        for tb in boxes:
            p1 = tb.find(qn("w:p"))
            first = "".join(t.text or "" for t in p1.iter(qn("w:t"))).strip() if p1 is not None else ""
            if first == marker if key == "empfaenger" else first.startswith(marker):
                if key == "logo":
                    set_paragraphs(tb, [""])
                elif key == "kontakt":
                    lines = as_list(data[key])
                    web = copy.deepcopy(tb.findall(qn("w:p"))[1])
                    set_paragraphs(tb, ["\n".join(lines[:-1] or lines)])
                    if len(lines) > 1:
                        for t in web.iter(qn("w:t")):
                            t.text = lines[-1]
                        tb.append(web)
                else:
                    set_paragraphs(tb, as_list(data[key]))
    logo = data.get("logo")
    if logo:
        for tb in boxes:
            if tb.find(qn("w:p")) is not None and not "".join(tb.itertext()).strip() and \
               tb.find(".//" + qn("w:pStyle")) is not None and \
               tb.find(".//" + qn("w:pStyle")).get(qn("w:val")) == "LogoPlatzhalter":
                Paragraph(tb.find(qn("w:p")), doc._body).add_run().add_picture(logo, height=Cm(1.2))
                break
    doc.save(out)


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    build(json.loads(Path(sys.argv[1]).read_text(encoding="utf-8")), sys.argv[2])
    print("geschrieben:", sys.argv[2])
