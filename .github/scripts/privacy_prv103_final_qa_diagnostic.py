from __future__ import annotations

import json
from pathlib import Path

from privacy_prv103_qa4 import inspect_case

FROZEN_MAIN_SHA = "723a20160d9b2bf39e5c7ef6ad3bf4878f45dd23"
EXPECTED_FRAMEWORK_VERSION = "0.7"
ALLOWED_FIELDS = ("heading", "legend", "introductory_text", "submit_text")

# Cases called out by the independent final QA. These are intentionally fixed
# diagnostic recaptures, not a new holdout and not tuning data.
CASES = [
    ("FINAL-MD", "qa_final_recheck", "SaaS", "en", "https://motherduck.com/"),
    ("FINAL-SB", "qa_final_recheck", "Data", "en", "https://www.starburst.io/"),
    ("FINAL-LC", "qa_final_recheck", "AI", "en", "https://www.langchain.com/"),
    ("FINAL-CB", "qa_final_recheck", "AI", "en", "https://www.cerebras.ai/"),
]


def _compact(form: dict) -> dict:
    return {
        field: form.get(field)
        for field in ALLOWED_FIELDS
    } | {
        "source_url": form.get("source_url"),
        "personal_confidence": form.get("personal_confidence"),
        "product_purpose": form.get("product_purpose"),
    }


def main() -> None:
    output = {
        "baseline": {
            "main_sha": FROZEN_MAIN_SHA,
            "framework_version": EXPECTED_FRAMEWORK_VERSION,
            "purpose": "recapture_final_qa_failures_only",
            "note": "Diagnostic only: this is not a new holdout and must not be used as independent QA after tuning.",
        },
        "cases": [],
    }

    for case in CASES:
        case_result, forms = inspect_case(*case)
        high_forms = [form for form in forms if form.get("personal_confidence") == "high"]
        output["cases"].append(
            {
                "case_id": case[0],
                "requested_url": case[-1],
                "inspection": case_result,
                "high_forms": [_compact(form) for form in high_forms],
            }
        )

    artifacts = Path("artifacts/privacy-prv103-final-qa-diagnostic")
    artifacts.mkdir(parents=True, exist_ok=True)
    json_path = artifacts / "diagnostic.json"
    md_path = artifacts / "diagnostic.md"
    json_path.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")

    lines = [
        "# PRV-103 final QA - diagnostic recapture",
        "",
        f"Frozen main SHA: `{FROZEN_MAIN_SHA}`",
        "",
        "This package only checks what the inspector currently captures for four failed QA cases.",
        "It does not change rules and it is not a new independent holdout.",
        "",
    ]
    for case in output["cases"]:
        lines.append(f"## {case['case_id']} - {case['requested_url']}")
        lines.append(f"- PRV-103: {((case['inspection'].get('prv103') or {}).get('status')) or '(none)'}")
        if not case["high_forms"]:
            lines.append("- HIGH personal forms: none")
        for index, form in enumerate(case["high_forms"], start=1):
            lines.append(f"- form {index} product_purpose: {form.get('product_purpose')}")
            for field in ALLOWED_FIELDS:
                lines.append(f"  - {field}: {form.get(field) or '(vacío)'}")
            lines.append(f"  - source_url: {form.get('source_url') or '(vacío)'}")
        lines.append("")
    md_path.write_text("\n".join(lines), encoding="utf-8")

    print("PRV103_FINAL_QA_DIAGNOSTIC_START")
    print(json.dumps(output, ensure_ascii=False, indent=2))
    print("PRV103_FINAL_QA_DIAGNOSTIC_END")


if __name__ == "__main__":
    main()
