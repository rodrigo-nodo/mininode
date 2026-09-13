"""Run the frozen focused PRV-104 QA against public sites.

QA tooling only. It does not submit forms or change product rules.
"""
from __future__ import annotations

import json
from pathlib import Path

from mininode_api.services.privacy_diagnostic import PrivacyInspectionError, diagnose_privacy_url

SITES = [
    "https://hubspot.com",
    "https://mailchimp.com",
    "https://typeform.com",
    "https://surveymonkey.com",
    "https://zendesk.com",
    "https://freshworks.com",
    "https://intercom.com",
    "https://pipedrive.com",
    "https://clickup.com",
    "https://monday.com",
    "https://airtable.com",
    "https://webflow.com",
]
OUT = Path("artifacts/privacy-prv104-focused")


def control_map(diagnostic: dict) -> dict[str, dict]:
    return {item["control_code"]: item for item in diagnostic["controls"]}


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    cases = []
    for index, url in enumerate(SITES, 1):
        row = {"case_id": f"PRV104-QA-{index:02d}", "requested_url": url}
        try:
            diagnostic = diagnose_privacy_url(url)
            controls = control_map(diagnostic)
            row.update(
                {
                    "site_url": diagnostic.get("site_url"),
                    "scope": diagnostic.get("scope"),
                    "prv101": controls.get("PRV-101"),
                    "prv104": controls.get("PRV-104"),
                }
            )
        except PrivacyInspectionError as exc:
            row.update({"inspection_error": exc.code, "diagnostic": exc.diagnostic})
        except Exception as exc:  # QA must retain unexpected failures as evidence.
            row.update({"unexpected_error": type(exc).__name__, "message": str(exc)[:300]})
        cases.append(row)
        print(json.dumps(row, ensure_ascii=False, sort_keys=True))

    payload = {
        "product_sha": "cb7c219f6b3e26bba4fd73a2905305a3a78003a1",
        "framework_version": "0.9",
        "scoring_version": "0.1",
        "control": "PRV-104",
        "candidate_count": len(SITES),
        "cases": cases,
    }
    (OUT / "result.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
