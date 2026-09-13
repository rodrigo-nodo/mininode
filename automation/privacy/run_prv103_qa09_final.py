#!/usr/bin/env python3
"""Final frozen QA09 comparison for deterministic PRV-103 framework 0.9."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from mininode_api.domain_packs.privacy.evidence_adapter import _form_purpose_signal
from mininode_api.web_inspector.models import FormEvidence

ROOT = Path(__file__).resolve().parents[2]
ARTIFACT_A = ROOT / "docs/evidence/prv103-holdout-0.9-artifact-a.json"
GOLD = ROOT / "docs/evidence/prv103-holdout-0.9-gold.json"
EXPECTED_A_SHA256 = "45a16c3bea81a62a9504d6616ac67221ee1240efe340703a8ad9f3fe7682afd2"
EXPECTED_GOLD_SHA256 = "210ad0fa63916cb0a3f940431000dc4b985a2e2e88d973c2aaffda0ebd42570e"
EXPECTED_CASES = 56
CLASSES = {"concrete", "generic", "none", "unknown"}


def canonical_sha(path: Path) -> str:
    payload = json.loads(path.read_text(encoding="utf-8"))
    canonical = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode()
    return hashlib.sha256(canonical).hexdigest()


def as_form(row: dict) -> FormEvidence:
    return FormEvidence(
        source_url="https://blind.invalid/", action="", method="post", fields=[], checkboxes=[],
        nearby_text="", privacy_links=[], heading=row.get("heading"), legend=row.get("legend"),
        introductory_text=row.get("introductory_text"), submit_text=row.get("submit_text"),
    )


def pct(n: int, d: int) -> float:
    return round(100.0 * n / d, 2) if d else 0.0


def main() -> int:
    assert canonical_sha(ARTIFACT_A) == EXPECTED_A_SHA256, "Artifact A changed"
    assert canonical_sha(GOLD) == EXPECTED_GOLD_SHA256, "Gold changed"
    cases = json.loads(ARTIFACT_A.read_text(encoding="utf-8"))
    gold_rows = json.loads(GOLD.read_text(encoding="utf-8"))
    assert len(cases) == len(gold_rows) == EXPECTED_CASES
    gold = {r["blind_id"]: r["gold"] for r in gold_rows}
    assert len(gold) == EXPECTED_CASES and set(gold.values()) <= CLASSES
    assert {r["blind_id"] for r in cases} == set(gold)

    rows = []
    for row in cases:
        pred = _form_purpose_signal(as_form(row))
        assert pred in CLASSES
        rows.append({"blind_id": row["blind_id"], "gold": gold[row["blind_id"]], "prediction": pred})

    adjudicable = [r for r in rows if r["gold"] != "unknown"]
    emitted = [r for r in adjudicable if r["prediction"] != "unknown"]
    gold_concrete = [r for r in adjudicable if r["gold"] == "concrete"]
    pred_concrete = [r for r in adjudicable if r["prediction"] == "concrete"]
    exact = sum(r["prediction"] == r["gold"] for r in adjudicable)
    emitted_correct = sum(r["prediction"] == r["gold"] for r in emitted)
    true_concrete = sum(r["prediction"] == "concrete" and r["gold"] == "concrete" for r in adjudicable)
    false_concrete = sum(r["prediction"] == "concrete" and r["gold"] != "concrete" for r in adjudicable)
    false_adverse_none = sum(r["prediction"] == "none" and r["gold"] not in {"none", "unknown"} for r in rows)

    metrics = {
        "eligible": EXPECTED_CASES,
        "adjudicable": len(adjudicable),
        "exact_accuracy": pct(exact, len(adjudicable)),
        "coverage": pct(len(emitted), len(adjudicable)),
        "emitted_precision": pct(emitted_correct, len(emitted)),
        "concrete_precision": pct(true_concrete, len(pred_concrete)),
        "concrete_recall": pct(true_concrete, len(gold_concrete)),
        "false_concrete": false_concrete,
        "false_adverse_none": false_adverse_none,
    }
    pass_gate = (
        EXPECTED_CASES >= 30 and metrics["exact_accuracy"] >= 90 and metrics["coverage"] >= 90
        and metrics["emitted_precision"] >= 95 and metrics["concrete_precision"] >= 90
        and metrics["concrete_recall"] >= 85 and false_concrete <= 1 and false_adverse_none == 0
    )
    observations_gate = (
        metrics["exact_accuracy"] >= 85 and metrics["coverage"] >= 80
        and metrics["emitted_precision"] >= 90 and metrics["concrete_precision"] >= 85
        and metrics["concrete_recall"] >= 80 and false_adverse_none <= 1
    )
    verdict = "PASS" if pass_gate else "PASS WITH OBSERVATIONS" if observations_gate else "NEEDS FIX"
    errors = [r for r in rows if r["gold"] != "unknown" and r["prediction"] != r["gold"]]
    result = {
        "product_sha": "6fbe6f94887114f4a5459af861f1fcaa0c4b7bd7",
        "framework_version": "0.9", "scoring_version": "0.1",
        "artifact_a_canonical_sha256": EXPECTED_A_SHA256,
        "gold_canonical_sha256": EXPECTED_GOLD_SHA256,
        "metrics": metrics, "provisional_verdict": verdict, "errors": errors, "predictions": rows,
        "note": "Final verdict still requires manual check for a systematic failure pattern, per frozen protocol.",
    }
    out = ROOT / "artifacts/privacy-prv103-qa09-final"
    out.mkdir(parents=True, exist_ok=True)
    (out / "result.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"metrics": metrics, "provisional_verdict": verdict, "errors": errors}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
