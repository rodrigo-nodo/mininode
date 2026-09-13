"""PRV-104 QA V2 stage 1: eligibility + blind Artifact A.

QA tooling only. It never reads or persists PRV-104 predictions.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import mininode_api.services.privacy_diagnostic as privacy_diagnostic
from mininode_api.services.privacy_diagnostic import PrivacyInspectionError

SITES = [
    "https://drift.com", "https://front.com", "https://close.com", "https://copper.com",
    "https://insightly.com", "https://keap.com", "https://activecampaign.com",
    "https://constantcontact.com", "https://brevo.com", "https://customer.io",
    "https://postmarkapp.com", "https://mailerlite.com", "https://tally.so",
    "https://jotform.com", "https://paperform.co", "https://formstack.com",
    "https://cognitoforms.com", "https://fillout.com", "https://savvycal.com",
    "https://youcanbook.me", "https://oncehub.com", "https://chilipiper.com",
    "https://demostack.com", "https://storylane.io",
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
        "result": item.get("result"),
        "confidence": item.get("confidence"),
        "evidence": item.get("evidence"),
    }


def form_snapshot(form) -> dict:
    """Return only observable form evidence needed for blind manual adjudication."""
    return {
        "fields": [
            {
                "name": field.name,
                "type": field.type,
                "label": field.label,
                "required": field.required,
            }
            for field in form.fields
        ],
        "checkboxes": [
            {"name": checkbox.name, "label": checkbox.label}
            for checkbox in form.checkboxes
        ],
        "nearby_text": form.nearby_text,
        "privacy_links": [{"text": link.text} for link in form.privacy_links],
        "heading": form.heading,
        "legend": form.legend,
        "introductory_text": form.introductory_text,
        "submit_text": form.submit_text,
    }


def diagnose_with_contract(url: str):
    """Run the production pipeline while retaining its final EvidenceContract."""
    captured = {}
    original = privacy_diagnostic.build_evidence

    def capture(*args, **kwargs):
        contract = original(*args, **kwargs)
        captured["contract"] = contract
        return contract

    privacy_diagnostic.build_evidence = capture
    try:
        diagnostic = privacy_diagnostic.diagnose_privacy_url(url)
    finally:
        privacy_diagnostic.build_evidence = original
    return diagnostic, captured.get("contract")


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    precheck = []
    eligible = []
    mapping = []

    for index, url in enumerate(SITES, 1):
        row = {"candidate_id": f"C-{index:02d}", "requested_url": url}
        try:
            diagnostic, contract = diagnose_with_contract(url)
            controls = control_map(diagnostic)
            prv101 = controls.get("PRV-101")
            # Intentionally never access controls.get("PRV-104").
            row["prv101"] = sanitize_prv101(prv101)
            precheck.append(row)
            if (
                prv101
                and prv101.get("result") == "detected"
                and prv101.get("confidence") == "high"
                and contract is not None
            ):
                blind_id = f"PRV104-V2-A-{len(eligible)+1:02d}"
                eligible.append({
                    "blind_id": blind_id,
                    "forms": [form_snapshot(form) for form in contract.forms],
                })
                mapping.append({"blind_id": blind_id, "candidate_id": row["candidate_id"], "requested_url": url})
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
    # Mapping is operational only; it must remain unopened until Gold is frozen.
    (OUT / "mapping-b.json").write_text(json.dumps({"mapping": mapping}, ensure_ascii=False, indent=2, sort_keys=True)+"\n", encoding="utf-8")
    print(json.dumps({k: summary[k] for k in ("candidate_pool_count", "candidates_checked", "eligible_count", "minimum_required", "precheck_pass", "artifact_a_sha256")}, sort_keys=True))


if __name__ == "__main__":
    main()
