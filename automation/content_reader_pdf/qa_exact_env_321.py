"""One-off read-only capability probe for PR #321 exact CI dependencies.

No product implementation changed. No OCR, LLM, POST or user login.
Public source PDFs are downloaded by GET only; inaccessible sources are reported
as not validated rather than substituted with local tests.
"""
from __future__ import annotations

import hashlib
import io
import json
import platform
import sys
import time
import unicodedata
import urllib.request
from importlib.metadata import version
from reportlab.pdfgen import canvas
from reportlab.pdfbase.pdfmetrics import stringWidth
import pdfplumber

SOURCES = {
    "AMF": (
        "https://amf.cl/wp-content/uploads/2022/11/Politica-de-Privacidad-AMF-1.pdf", 3
    ),
    "Claro": (
        "https://www.clarochile.cl/portal/cl/archivos_generales/"
        "Politica_de_Proteccion_de_Datos_Personales_Claro_2023.pdf", 8
    ),
    "S3": (
        "https://s3chile.cl/wp-content/uploads/2025/11/POLITICA-DE-PRIVACIDAD.pdf", 6
    ),
}


def normalize(s):
    s = unicodedata.normalize("NFKD", s or "")
    return "".join(c for c in s.casefold() if not unicodedata.combining(c))


def summarize_table(table):
    rows = table.extract()
    return {
        "rows": len(rows),
        "cols": max((len(r) for r in rows), default=0),
        "empty_rows": sum(not any((c or "").strip() for c in r) for r in rows),
        "pairs": [
            [(c or "").replace("\n", " ")[:190] for c in r[:2]]
            for r in rows if any((c or "").strip() for c in r)
        ][:9],
    }


def synthetic_pdf(kind):
    stream = io.BytesIO()
    pdf = canvas.Canvas(stream, pagesize=(600, 800))
    if kind.startswith("variable_gap_"):
        gap = int(kind.rsplit("_", 1)[-1])
        for i in range(5):
            left, right = f"Area{i:02}", f"Dato{i:02}"
            y = 730 - i * 29
            pdf.drawString(50, y, left)
            pdf.drawString(50 + stringWidth(left, "Helvetica", 12) + gap, y, right)
    elif kind == "list":
        for i in range(5):
            pdf.drawString(50, 730 - i * 29, f"{i + 1}.")
            pdf.drawString(86, 730 - i * 29, f"Elemento de lista {i}")
    elif kind == "borderless":
        for i in range(5):
            pdf.drawString(50, 730 - i * 29, f"Servicio{i}")
            pdf.drawString(320, 730 - i * 29, f"Dato{i}")
    elif kind == "ruled":
        for x in (50, 270, 560):
            pdf.line(x, 580, x, 720)
        for y in (580, 625, 670, 720):
            pdf.line(50, y, 560, y)
        for i in range(3):
            pdf.drawString(65, 687 - i * 45, f"Servicio{i}")
            pdf.drawString(285, 687 - i * 45, f"Dato{i}")
    pdf.save()
    return stream.getvalue()


def inspect_pdf(data, *, chosen=None):
    with pdfplumber.open(io.BytesIO(data), laparams={"boxes_flow": 0.5}) as pdf:
        result = {"pages": len(pdf.pages), "chars": 0, "mcid_chars": 0, "blocks": 0, "per_page": []}
        for index, page in enumerate(pdf.pages, 1):
            result["chars"] += len(page.chars)
            result["mcid_chars"] += sum(ch.get("mcid") is not None for ch in page.chars)
            blocks = page.objects.get("textboxhorizontal", [])
            result["blocks"] += len(blocks)
            row = {
                "page": index,
                "chars": len(page.chars),
                "blocks": len(blocks),
                "mcid_chars": sum(ch.get("mcid") is not None for ch in page.chars),
            }
            try:
                tree = page.structure_tree
                row["structure_roots"] = [node.get("type") for node in tree[:7]]
            except Exception as error:
                row["structure_tree_error"] = type(error).__name__ + ": " + str(error)[:120]
            if chosen is None or index in chosen:
                row["tables_lines"] = [
                    summarize_table(t) for t in page.find_tables(table_settings={
                        "vertical_strategy": "lines",
                        "horizontal_strategy": "lines",
                    })
                ]
                if (chosen is None or index in chosen) and index in (1, 3, 4):
                    try:
                        text_tables = page.find_tables(table_settings={
                            "vertical_strategy": "text",
                            "horizontal_strategy": "text",
                            "min_words_vertical": 3,
                            "min_words_horizontal": 3,
                            "text_x_tolerance": 1,
                        })
                        row["tables_text_shapes"] = [
                            [len(t.rows), max((len(r.cells) for r in t.rows), default=0)]
                            for t in text_tables
                        ][:6]
                    except Exception as exc:
                        row["tables_text_error"] = type(exc).__name__ + ": " + str(exc)[:110]
                row["words_default_first"] = [w["text"] for w in page.extract_words()[:10]]
                words = page.extract_words(x_tolerance=1, return_chars=True)
                row["words_x1_first"] = [w["text"] for w in words[:10]]
                row["word_char_provenance"] = all("chars" in w for w in words)
            result["per_page"].append(row)
        if chosen is not None:
            result["sha256"] = hashlib.sha256(data).hexdigest()
        return result


def download(url):
    req = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0 (compatible; MininodePDF-Capability-QA/1.0)",
        "Accept": "application/pdf",
    })
    with urllib.request.urlopen(req, timeout=25) as response:
        data = response.read(2 * 1024 * 1024 + 1)
    if len(data) > 2 * 1024 * 1024 or not data.startswith(b"%PDF-"):
        raise ValueError("size or PDF header does not match")
    return data


def main():
    assert sys.version_info[:2] == (3, 11), platform.python_version()
    assert version("pdfplumber") == "0.11.4", version("pdfplumber")
    report = {
        "python": platform.python_version(),
        "pdfplumber": version("pdfplumber"),
        "pdfminer.six": version("pdfminer.six"),
        "synthetic": {},
        "public_sources": {},
    }
    for name in ("variable_gap_3", "variable_gap_4", "variable_gap_7",
                 "list", "borderless", "ruled"):
        data = synthetic_pdf(name)
        result = inspect_pdf(data)
        with pdfplumber.open(io.BytesIO(data)) as pdf:
            page = pdf.pages[0]
            result["words_default"] = [w["text"] for w in page.extract_words()[:12]]
            result["words_x1"] = [w["text"] for w in page.extract_words(
                x_tolerance=1, return_chars=True)[:12]]
            result["table_lines_shapes"] = [
                (len(t.rows), len(t.rows[0].cells)) for t in page.find_tables({
                    "vertical_strategy": "lines", "horizontal_strategy": "lines"
                })
            ]
            result["table_text_shapes"] = [
                (len(t.rows), len(t.rows[0].cells)) for t in page.find_tables({
                    "vertical_strategy": "text", "horizontal_strategy": "text",
                    "min_words_vertical": 3, "min_words_horizontal": 3,
                    "text_x_tolerance": 1,
                })
            ]
        report["synthetic"][name] = {
            "words_default": result["words_default"],
            "words_x1": result["words_x1"],
            "table_lines_shapes": result["table_lines_shapes"],
            "table_text_shapes": result["table_text_shapes"],
            "blocks": result["blocks"],
        }
    for name, (url, expected_pages) in SOURCES.items():
        try:
            data = download(url)
            inspected = inspect_pdf(data, chosen={
                "AMF": (1, 2, 3), "Claro": (3, 4), "S3": (1, 4),
            }[name])
            inspected["status"] = "DOWNLOADED_AND_TESTED"
            inspected["expected_pages_match"] = inspected["pages"] == expected_pages
            report["public_sources"][name] = inspected
        except Exception as exc:
            report["public_sources"][name] = {
                "status": "NOT_TESTED_SOURCE_INACCESSIBLE",
                "reason": type(exc).__name__ + ": " + str(exc)[:190],
            }
    print("PR321_CAPABILITY_RESULT_START", flush=True)
    print(json.dumps(report, ensure_ascii=False, indent=2), flush=True)
    print("PR321_CAPABILITY_RESULT_END", flush=True)


if __name__ == "__main__":
    main()
