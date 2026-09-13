"""PRV-104 QA V2 stage 1: eligibility + blind Artifact A.

QA tooling only. Never reads or persists PRV-104 predictions.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from mininode_api.services.privacy_diagnostic import PrivacyInspectionError, diagnose_privacy_url

# New candidate pool, frozen before execution. Deliberately uses likely public
# contact/demo/newsletter surfaces, but eligibility is decided only by PRV-101.
SITES = [
    "https://drift.com",
    "https://front.com",
    "https://close.com",
    "https://copper.com",
    "https://insightly.com",
    "https://keap.com",
    "https://activecampaign.com",
    "https://constantcontact.com",
    "https://brevo.com",
    "https://customer.io",
    "https://postmarkapp.com",
    "https://mailerlite.com",
    "https://tally.so",
    "https://jotform.com",
    "https://paperform.co",
    "https://formstack.com",
    "https://cognitoforms.com",
    "https://fillout.com",
    "https://savvycal.com",
    "https://youcanbook.me",
    "https://oncehub.com",
    "https://chilipiper.com",
    "https://demostack.com",
    "https://storylane.io",
]
OUT = Path("artifacts/privacy-prv104-qa-v2")
TARGET_MIN = 6
TARGET_MAX = 12


def control_map(diagnostic: dict) -> dict[str, dict]:
    return {item["control_code"]: item for item in diagnostic["controls"]}


def sanitize_prv101(item: dict | None) -> dict | None:
    if not item:
        return None
    return {
        "status": item.get("status"),
        "confidence": item.get("confidence"),
        "evidence": item.get("evidence"),
    }


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    precheck = []
    eligible = []

    for index, url in enumerate(SITES, 1):
        row = {"candidate_id": f"C-{index:02d}", "requested_url": url}
        try:
            diagnostic = diagnose_privacy_url(url)
            controls = control_map(diagnostic)
            prv101 = controls.get("PRV-101")
            # Intentionally do not access controls.get("PRV-104").
            row["prv101"] = sanitize_prv101(prv101)
            precheck.append(row)
            if prv101 and prv101.get("status") == "detected" and prv101.get("confidence") == "high":
                evidence = prv101.get("evidence") or {}
                # Artifact A excludes site identity and product PRV-104 prediction.
                blind = {
                    "blind_id": f"PRV104-V2-A-{len(eligible)+1:02d}",
                    "form_evidence": evidence,
                }
                eligible.append(blind)
                if len(eligible) >= TARGET_MAX:
                    break
        except PrivacyInspectionError as exc:
            row["inspection_error"] = exc.code
            precheck.append(row)
        except Exception as exc:
            row["unexpected_error"] = type(exc).__name__
            precheck.append(row)

    artifact_a = {
        "product_sha": "cb7c219f6b3e26bba4fd73a2905305a3a78003a1",
        "framework_version": "0.9",
        "scoring_version": "0.1",
        "control": "PRV-104",
        "stage": "artifact_a_blind",
        "eligible_count": len(eligible),
        "cases": eligible,
    }
    canonical = json.dumps(artifact_a, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    summary = {
        "candidate_pool_count": len(SITES),
        "candidates_checked": len(precheck),
        "eligible_count": len(eligible),
        "minimum_required": TARGET_MIN,
        "precheck_pass": len(eligible) >= TARGET_MIN,
        "artifact_a_sha256": hashlib.sha256(canonical.encode()).hexdigest(),
        "precheck": precheck,
    }
    (OUT / "artifact-a.json").write_text(json.dumps(artifact_a, ensure_ascii=False, indent=2, sort_keys=True)+"\n", encoding="utf-8")
    (OUT / "precheck.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True)+"\n", encoding="utf-8")
    print(json.dumps({k: summary[k] for k in ("candidate_pool_count", "candidates_checked", "eligible_count", "minimum_required", "precheck_pass", "artifact_a_sha256")}, sort_keys=True))


if __name__ == "__main__":
    main()
