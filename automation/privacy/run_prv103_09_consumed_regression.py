"""Re-score the consumed Issue #223 PRV-103 holdout with framework 0.9.

The input is the frozen Issue #223 reviewer bundle.  This command never fetches
or captures sites: it only classifies the four already-recorded form fields.
"""

from __future__ import annotations

import argparse
import json
import subprocess
from collections import Counter
from pathlib import Path
from typing import Any

from mininode_api.domain_packs.privacy.evidence_adapter import _form_purpose_signal
from mininode_api.domain_packs.privacy.versioning import diagnostic_versions
from mininode_api.web_inspector.models import FormEvidence

EXPECTED_MAIN_SHA = "6fbe6f94887114f4a5459af861f1fcaa0c4b7bd7"
EXPECTED_VERSIONS = {"framework_version": "0.9", "scoring_version": "0.1"}
EXPECTED_ELIGIBLE = 63
EXPECTED_ADJUDICABLE = 58
EXPECTED_UNKNOWN_GOLD = 5
ALLOWED_CLASSES = {"concrete", "generic", "none", "unknown"}
REFERENCE_08 = {
    "eligible_forms": 63,
    "adjudicable_forms": 58,
    "exact_accuracy": 31 / 58,
    "coverage": 43 / 58,
    "emitted_precision": 31 / 43,
    "concrete_precision": 19 / 22,
    "concrete_recall": 19 / 36,
    "false_concrete": 3,
    "false_adverse_none": 0,
}


def _form(case: dict[str, Any]) -> FormEvidence:
    return FormEvidence(
        source_url="https://consumed-holdout.invalid/",
        action="",
        method="post",
        fields=[],
        checkboxes=[],
        nearby_text="",
        privacy_links=[],
        heading=case.get("heading"),
        legend=case.get("legend"),
        introductory_text=case.get("introductory_text"),
        submit_text=case.get("submit_text"),
    )


def metrics(rows: list[dict[str, str]], eligible: int) -> dict[str, int | float]:
    emitted = [row for row in rows if row["prediction"] != "unknown"]
    concrete = [row for row in rows if row["prediction"] == "concrete"]
    gold_concrete = [row for row in rows if row["gold"] == "concrete"]
    true_concrete = [row for row in concrete if row["gold"] == "concrete"]
    exact = sum(row["prediction"] == row["gold"] for row in rows)
    emitted_correct = sum(row["prediction"] == row["gold"] for row in emitted)
    return {
        "eligible_forms": eligible,
        "adjudicable_forms": len(rows),
        "exact_accuracy": exact / len(rows),
        "coverage": len(emitted) / len(rows),
        "emitted_precision": emitted_correct / len(emitted) if emitted else 1.0,
        "concrete_precision": len(true_concrete) / len(concrete) if concrete else 1.0,
        "concrete_recall": len(true_concrete) / len(gold_concrete) if gold_concrete else 1.0,
        "false_concrete": len(concrete) - len(true_concrete),
        "false_adverse_none": sum(
            row["prediction"] == "none" and row["gold"] != "none" for row in rows
        ),
    }


def verdict(result: dict[str, int | float]) -> str:
    if result["false_concrete"] or result["false_adverse_none"]:
        return "NEEDS FIX"
    if (
        result["emitted_precision"] >= 0.90
        and result["coverage"] >= 0.70
        and result["exact_accuracy"] >= 0.80
        and result["concrete_recall"] >= 0.75
    ):
        return "PASS"
    if (
        result["emitted_precision"] >= 0.90
        and result["coverage"] >= 0.60
        and result["exact_accuracy"] >= 0.70
        and result["concrete_recall"] >= 0.65
    ):
        return "PASS WITH OBSERVATIONS"
    return "NEEDS FIX"


def evaluate(payload: dict[str, Any]) -> dict[str, Any]:
    versions = diagnostic_versions()
    assert versions == EXPECTED_VERSIONS, versions
    assert subprocess.check_output(["git", "rev-parse", "main"], text=True).strip() == EXPECTED_MAIN_SHA
    cases = payload["cases"]
    assert len(cases) == EXPECTED_ELIGIBLE
    assert len({case["blind_id"] for case in cases}) == EXPECTED_ELIGIBLE
    assert all(case["gold"] in ALLOWED_CLASSES for case in cases)
    assert Counter(case["gold"] for case in cases)["unknown"] == EXPECTED_UNKNOWN_GOLD

    # Match #223: unknown gold is non-adjudicable and excluded from all rates.
    adjudicable = [case for case in cases if case["gold"] != "unknown"]
    assert len(adjudicable) == EXPECTED_ADJUDICABLE
    rows = [
        {
            "blind_id": case["blind_id"],
            "gold": case["gold"],
            "prediction": _form_purpose_signal(_form(case)),
        }
        for case in adjudicable
    ]
    result = metrics(rows, len(cases))
    return {
        "main_sha": EXPECTED_MAIN_SHA,
        **versions,
        "source": "Issue #223 consumed holdout and frozen gold",
        "unknown_gold_treatment": "excluded from adjudicable metrics, as in Issue #223",
        "framework_08": REFERENCE_08,
        "framework_09": result,
        "difference": {key: result[key] - value for key, value in REFERENCE_08.items()},
        "hypothetical_09_verdict_under_issue_223_thresholds": verdict(result),
        "rows": rows,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path, help="frozen Issue #223 JSON bundle")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = evaluate(json.loads(args.input.read_text(encoding="utf-8")))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
