"""PRV-104 QA V2 stage 4: reveal frozen-product predictions after Gold."""
from __future__ import annotations

import json
from pathlib import Path

from mininode_api.services.privacy_diagnostic import PrivacyInspectionError, diagnose_privacy_url

CASES = [
    ("PRV104-V2-A-01", "https://close.com"),
    ("PRV104-V2-A-02", "https://keap.com"),
    ("PRV104-V2-A-03", "https://activecampaign.com"),
    ("PRV104-V2-A-04", "https://brevo.com"),
    ("PRV104-V2-A-05", "https://customer.io"),
    ("PRV104-V2-A-06", "https://postmarkapp.com"),
    ("PRV104-V2-A-07", "https://mailerlite.com"),
    ("PRV104-V2-A-08", "https://tally.so"),
    ("PRV104-V2-A-09", "https://jotform.com"),
    ("PRV104-V2-A-10", "https://cognitoforms.com"),
    ("PRV104-V2-A-11", "https://savvycal.com"),
    ("PRV104-V2-A-12", "https://oncehub.com"),
]
OUT = Path("artifacts/privacy-prv104-qa-v2-reveal")
GOLD = Path("docs/evidence/prv104-focused-qa-v2-gold.json")
EXPECTED_A_SHA = "11fe49cad563351d9873692891285d1ab1afb418d898e5ada04de2757435b00e"


def control_map(diagnostic: dict) -> dict[str, dict]:
    return {item["control_code"]: item for item in diagnostic["controls"]}


def main() -> None:
    gold = json.loads(GOLD.read_text(encoding="utf-8"))
    if gold.get("artifact_a_sha256") != EXPECTED_A_SHA or not gold.get("adjudicated_before_artifact_b"):
        raise SystemExit("Gold is not frozen against the expected blind Artifact A")

    OUT.mkdir(parents=True, exist_ok=True)
    predictions = []
    for blind_id, url in CASES:
        row = {"blind_id": blind_id, "requested_url": url}
        try:
            diagnostic = diagnose_privacy_url(url)
            controls = control_map(diagnostic)
            row["prv101"] = {k: controls["PRV-101"].get(k) for k in ("result", "confidence")}
            row["prv104"] = {k: controls["PRV-104"].get(k) for k in ("result", "confidence", "evidence_summary")}
        except PrivacyInspectionError as exc:
            row["inspection_error"] = exc.code
        except Exception as exc:
            row["unexpected_error"] = type(exc).__name__
        predictions.append(row)

    gold_by_id = {case["blind_id"]: case["gold"] for case in gold["cases"]}
    adjudicable = []
    for row in predictions:
        expected = gold_by_id[row["blind_id"]]
        if expected == "unknown":
            continue
        predicted = (row.get("prv104") or {}).get("result")
        adjudicable.append({
            "blind_id": row["blind_id"], "gold": expected,
            "prediction": predicted, "match": predicted == expected,
        })

    comparable = [row for row in adjudicable if row["prediction"] is not None]
    matches = sum(row["match"] for row in comparable)
    accuracy = 100.0 * matches / len(comparable) if comparable else 0.0
    false_detected = sum(row["prediction"] == "detected" and row["gold"] != "detected" for row in comparable)
    discrepancies = [row for row in comparable if not row["match"]]
    if len(comparable) < 6:
        verdict = "INCONCLUSIVE"
    elif accuracy >= 90.0 and false_detected == 0 and not discrepancies:
        verdict = "PASS"
    elif accuracy >= 80.0 and false_detected == 0 and len(discrepancies) <= 1:
        verdict = "PASS WITH OBSERVATIONS"
    else:
        verdict = "NEEDS FIX"

    result = {
        "product_sha": "cb7c219f6b3e26bba4fd73a2905305a3a78003a1",
        "framework_version": "0.9", "scoring_version": "0.1",
        "artifact_a_sha256": EXPECTED_A_SHA,
        "predictions": predictions,
        "comparison": adjudicable,
        "comparable_count": len(comparable),
        "exact_accuracy": round(accuracy, 2),
        "false_detected": false_detected,
        "discrepancy_count": len(discrepancies),
        "verdict": verdict,
        "note": "Predictions are a post-Gold reveal using the frozen product. Public sites may change between Artifact A capture and reveal; any evidence drift must be reviewed before attributing a mismatch to PRV-104.",
    }
    (OUT / "artifact-b-result.json").write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True)+"\n", encoding="utf-8")
    print(json.dumps({k: result[k] for k in ("comparable_count", "exact_accuracy", "false_detected", "discrepancy_count", "verdict")}, sort_keys=True))


if __name__ == "__main__":
    main()
