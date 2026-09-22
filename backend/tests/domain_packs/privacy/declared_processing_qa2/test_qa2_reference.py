import json
from pathlib import Path


ROOT = Path(__file__).parent


def test_qa2_reference_evidence_is_literal_and_capture_failures_have_no_facts():
    reference = json.loads((ROOT / "reference.json").read_text(encoding="utf-8"))
    for case in reference["cases"]:
        if case["status"] == "capture_failed":
            assert case["facts"] == []
            continue
        capture = (ROOT / "captures" / f'{case["case_id"]}.txt').read_text(encoding="utf-8")
        assert case["facts"]
        for fact in case["facts"]:
            assert fact["evidence"] in capture
