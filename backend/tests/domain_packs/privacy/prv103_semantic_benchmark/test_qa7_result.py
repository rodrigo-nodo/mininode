from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
REFERENCE_PATH = HERE / "qa7_reference.json"


def load_cases() -> list[dict]:
    return json.loads(REFERENCE_PATH.read_text(encoding="utf-8"))["cases"]


def metrics(field: str) -> dict[str, float | int]:
    cases = load_cases()
    exact = sum(row[field] == row["reference"] for row in cases)
    emitted = [row for row in cases if row[field] != "unknown"]
    concrete_pred = [row for row in cases if row[field] == "concrete"]
    reference_concrete = [row for row in cases if row["reference"] == "concrete"]
    return {
        "exact": exact,
        "accuracy": exact / len(cases),
        "coverage": len(emitted) / len(cases),
        "emitted_precision": sum(row[field] == row["reference"] for row in emitted) / len(emitted),
        "concrete_precision": sum(row["reference"] == "concrete" for row in concrete_pred) / len(concrete_pred),
        "concrete_recall": sum(row[field] == "concrete" for row in reference_concrete) / len(reference_concrete),
        "false_concrete": sum(row[field] == "concrete" and row["reference"] != "concrete" for row in cases),
        "false_none": sum(row[field] == "none" and row["reference"] != "none" for row in cases),
    }


def test_qa7_reference_is_complete_and_independent():
    payload = json.loads(REFERENCE_PATH.read_text(encoding="utf-8"))
    assert payload["independent_reviewer"] is True
    assert payload["allowed_fields"] == ["heading", "legend", "introductory_text", "submit_text"]
    assert payload["invalid_outputs"] == 0
    assert len(payload["cases"]) == 30
    assert len({row["blind_id"] for row in payload["cases"]}) == 30
    assert Counter(row["reference"] for row in payload["cases"]) == Counter(
        {"generic": 20, "concrete": 7, "unknown": 3}
    )


def test_shadow_metrics_match_qa7_result():
    result = metrics("shadow")
    assert result["exact"] == 29
    assert result["accuracy"] == 29 / 30
    assert result["coverage"] == 27 / 30
    assert result["emitted_precision"] == 26 / 27
    assert result["concrete_precision"] == 7 / 8
    assert result["concrete_recall"] == 1.0
    assert result["false_concrete"] == 1
    assert result["false_none"] == 0


def test_baseline_metrics_match_qa7_result():
    result = metrics("baseline")
    assert result["exact"] == 19
    assert result["accuracy"] == 19 / 30
    assert result["coverage"] == 17 / 30
    assert result["emitted_precision"] == 16 / 17
    assert result["concrete_precision"] == 0.0
    assert result["concrete_recall"] == 0.0
    assert result["false_concrete"] == 1
    assert result["false_none"] == 0


def test_all_shadow_disagreements_with_baseline_are_reference_improvements():
    disagreements = [row for row in load_cases() if row["baseline"] != row["shadow"]]
    assert len(disagreements) == 10
    assert all(row["baseline"] == "unknown" for row in disagreements)
    assert all(row["shadow"] == row["reference"] for row in disagreements)


def test_only_shadow_error_is_preexisting_baseline_false_concrete():
    errors = [row for row in load_cases() if row["shadow"] != row["reference"]]
    assert errors == [
        {
            "blind_id": "QA7-019",
            "reference": "generic",
            "baseline": "concrete",
            "shadow": "concrete",
        }
    ]
