from __future__ import annotations

import json
import os
from pathlib import Path

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


def compact(form: dict) -> dict:
    return {
        **{field: form.get(field) for field in ALLOWED_FIELDS},
        "source_url": form.get("source_url"),
        "personal_confidence": form.get("personal_confidence"),
        "product_purpose": form.get("product_purpose"),
    }


def main() -> None:
    output = {
        "baseline_main_sha": BASE_MAIN_SHA,
        "runner_sha": os.getenv("GITHUB_SHA"),
        "purpose": "consumed_cases_capture_regression_only",
        "cases": [],
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
