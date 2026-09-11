from __future__ import annotations

import json
import os
import time
from pathlib import Path

from bs4 import BeautifulSoup, Tag

from mininode_api.web_inspector import WebFetcher
from mininode_api.web_inspector.fetcher import INSPECTION_BUDGET_SECONDS
from privacy_prv103_qa4 import inspect_case

BASE_MAIN_SHA = "723a20160d9b2bf39e5c7ef6ad3bf4878f45dd23"
ALLOWED_FIELDS = ("heading", "legend", "introductory_text", "submit_text")

# Consumed QA cases used only to verify evidence-capture behavior after the fix.
# They are not a fresh holdout and cannot be used to claim final QA accuracy.
CASES = [
    ("REG-MD", "capture_regression", "SaaS", "en", "https://motherduck.com/"),
    ("REG-SB", "capture_regression", "Data", "en", "https://www.starburst.io/"),
    ("REG-LC", "capture_regression", "AI", "en", "https://www.langchain.com/"),
    ("REG-CB", "capture_regression", "AI", "en", "https://www.cerebras.ai/"),
]
TRACE_URLS = [
    "https://motherduck.com/contact-us/product-expert/",
    "https://www.langchain.com/contact-sales",
]


def compact(form: dict) -> dict:
    return {
        **{field: form.get(field) for field in ALLOWED_FIELDS},
        "source_url": form.get("source_url"),
        "personal_confidence": form.get("personal_confidence"),
        "product_purpose": form.get("product_purpose"),
    }


def _text(tag: Tag, limit: int = 180) -> str | None:
    value = " ".join(tag.get_text(" ", strip=True).split())
    return value[:limit] or None


def _classes(tag: Tag) -> list[str]:
    values = tag.get("class") or []
    return [str(value)[:80] for value in values[:4]]


def structure_trace(url: str) -> dict:
    trace = {"url": url, "forms": [], "error": None}
    deadline = time.monotonic() + INSPECTION_BUDGET_SECONDS
    try:
        with WebFetcher(inspection_budget=INSPECTION_BUDGET_SECONDS) as fetcher:
            result = fetcher.fetch(url, [url], deadline=deadline)
        if not result.pages or result.pages[0].error or not result.pages[0].html:
            trace["error"] = "fetch_failed"
            return trace
        soup = BeautifulSoup(result.pages[0].html, "lxml")
        for form_index, form in enumerate(soup.find_all("form")):
            form_trace = {
                "form_index": form_index,
                "inputs": len(form.find_all(["input", "select", "textarea"])),
                "ancestors": [],
            }
            anchor: Tag = form
            for depth in range(7):
                parent = anchor.parent
                if not isinstance(parent, Tag):
                    break
                previous = []
                for sibling in anchor.previous_siblings:
                    if not isinstance(sibling, Tag):
                        continue
                    previous.append({
                        "tag": sibling.name,
                        "classes": _classes(sibling),
                        "text": _text(sibling),
                        "has_form": bool(sibling.name == "form" or sibling.find("form")),
                        "has_link": bool(sibling.find("a", href=True)),
                    })
                    if len(previous) >= 4:
                        break
                form_trace["ancestors"].append({
                    "depth": depth,
                    "parent_tag": parent.name,
                    "parent_classes": _classes(parent),
                    "parent_text": _text(parent, 240),
                    "previous_siblings": previous,
                })
                if parent.name in {"body", "html"}:
                    break
                anchor = parent
            trace["forms"].append(form_trace)
    except Exception as exc:
        trace["error"] = type(exc).__name__
    return trace


def main() -> None:
    output = {
        "baseline_main_sha": BASE_MAIN_SHA,
        "runner_sha": os.getenv("GITHUB_SHA"),
        "purpose": "consumed_cases_capture_regression_only",
        "cases": [],
        "structure_traces": [],
    }

    for case in CASES:
        case_result, forms = inspect_case(*case)
        output["cases"].append({
            "case_id": case[0],
            "requested_url": case[-1],
            "inspection": case_result,
            "high_forms": [
                compact(form)
                for form in forms
                if form.get("personal_confidence") == "high"
            ],
        })

    output["structure_traces"] = [structure_trace(url) for url in TRACE_URLS]

    artifacts = Path("artifacts/privacy-prv103-capture-regression")
    artifacts.mkdir(parents=True, exist_ok=True)
    (artifacts / "regression.json").write_text(
        json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    lines = [
        "# PRV-103 capture regression",
        "",
        "Consumed QA cases only - not a fresh holdout.",
        "",
    ]
    for case in output["cases"]:
        inspection = case["inspection"]
        prv101 = inspection.get("prv101") or {}
        prv103 = inspection.get("prv103") or {}
        lines.extend([
            f"## {case['case_id']} - {case['requested_url']}",
            f"- pages analyzed: {inspection.get('pages_analyzed')}",
            f"- PRV-101: {prv101.get('result') or prv101.get('status') or '(none)'}",
            f"- PRV-103: {prv103.get('result') or prv103.get('status') or '(none)'}",
            f"- HIGH personal forms: {len(case['high_forms'])}",
        ])
        for index, form in enumerate(case["high_forms"], start=1):
            lines.append(f"- form {index} purpose: {form.get('product_purpose')}")
            for field in ALLOWED_FIELDS:
                lines.append(f"  - {field}: {form.get(field) or '(vacío)'}")
            lines.append(f"  - source_url: {form.get('source_url') or '(vacío)'}")
        lines.append("")

    (artifacts / "regression.md").write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps(output, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
