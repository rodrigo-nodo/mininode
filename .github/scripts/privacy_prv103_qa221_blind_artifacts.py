from __future__ import annotations

import argparse
import json
from pathlib import Path
from urllib.parse import urlsplit

from mininode_api.domain_packs.privacy.evaluator import load_control_catalog
from mininode_api.domain_packs.privacy.scoring import load_scoring
from privacy_prv103_qa4 import inspect_case

FROZEN_SHA = "244671de83e5463d1f65a4bd7e2d561bc2f38fd5"
EXPECTED_FRAMEWORK_VERSION = "0.8"
EXPECTED_SCORING_VERSION = "0.1"
ISSUE_NUMBER = 223
FIELDS = ("heading", "legend", "introductory_text", "submit_text")
CURRENT_FILE = Path(__file__).resolve()

POOL = [
    "https://helpcrunch.com/",
    "https://www.helpscout.com/",
    "https://www.gorgias.com/",
    "https://www.kustomer.com/",
    "https://www.gladly.com/",
    "https://www.dixa.com/",
    "https://crisp.chat/",
    "https://www.livechat.com/",
    "https://www.tawk.to/",
    "https://www.olark.com/",
    "https://www.zenefits.com/",
    "https://www.justworks.com/",
    "https://www.paycor.com/",
    "https://factorialhr.com/",
    "https://www.hibob.com/",
    "https://recruitee.com/",
    "https://breezy.hr/",
    "https://www.workable.com/",
    "https://www.ashbyhq.com/",
    "https://www.teamtailor.com/",
    "https://freedcamp.com/",
    "https://www.ntaskmanager.com/",
    "https://basecamp.com/",
    "https://www.smartsheet.com/",
    "https://www.teamwork.com/",
    "https://www.wrike.com/",
    "https://www.shortcut.com/",
    "https://slab.com/",
    "https://todoist.com/",
    "https://evernote.com/",
    "https://rollbar.com/",
    "https://www.bugsnag.com/",
    "https://raygun.com/",
    "https://logrocket.com/",
    "https://buddy.works/",
    "https://www.travis-ci.com/",
    "https://semaphoreci.com/",
    "https://codefresh.io/",
    "https://www.harness.io/",
    "https://buildkite.com/",
    "https://www.chargebee.com/",
    "https://www.mollie.com/",
    "https://www.meshpayments.com/",
    "https://www.bill.com/",
    "https://www.spendesk.com/",
    "https://www.payoneer.com/",
    "https://www.klarna.com/",
    "https://www.affirm.com/",
    "https://www.afterpay.com/",
    "https://monzo.com/",
    "https://www.sendlane.com/",
    "https://www.moengage.com/",
    "https://loops.so/",
    "https://onesignal.com/",
    "https://www.getresponse.com/",
    "https://www.sender.net/",
    "https://unbounce.com/",
    "https://instapage.com/",
    "https://plausible.io/",
    "https://june.so/",
    "https://pirsch.io/",
    "https://www.pendo.io/",
    "https://www.smartlook.com/",
    "https://mouseflow.com/",
    "https://www.crazyegg.com/",
    "https://fusionauth.io/",
    "https://duo.com/",
    "https://signwell.com/",
    "https://nordpass.com/",
    "https://surfshark.com/",
    "https://www.proofpoint.com/",
    "https://www.mimecast.com/",
    "https://www.knowbe4.com/",
    "https://www.huntress.com/",
    "https://www.sophos.com/",
    "https://www.fortinet.com/",
    "https://replicate.com/",
    "https://groq.com/",
    "https://huggingface.co/",
    "https://labelbox.com/",
    "https://typesense.org/",
    "https://fauna.com/",
    "https://materialize.com/",
    "https://www.databricks.com/",
    "https://www.alation.com/",
    "https://www.montecarlodata.com/",
    "https://www.collibra.com/",
    "https://www.dataiku.com/",
    "https://directus.io/",
    "https://hygraph.com/",
    "https://buttercms.com/",
    "https://formsort.com/",
    "https://www.wufoo.com/",
    "https://www.formassembly.com/",
    "https://www.alchemer.com/",
    "https://www.questionpro.com/",
    "https://www.concord.app/",
    "https://qwilr.com/",
    "https://ironcladapp.com/",
    "https://www.clio.com/",
]

EXCLUDED_EXTERNAL_HOSTS = {
    "workleap.com", "pigment.com", "mistral.ai", "harvey.ai", "clay.com", "lovable.dev",
    "replit.com", "cursor.com", "supabase.com", "planetscale.com", "motherduck.com",
    "clickhouse.com", "together.ai", "cohere.com", "pinecone.io", "weaviate.io", "qdrant.tech",
    "modal.com", "fly.io", "railway.com", "render.com", "sentry.io", "snyk.io", "semgrep.dev",
    "tailscale.com", "zerotier.com", "proton.me", "mullvad.net", "ghost.org", "webflow.com",
    "framer.com", "typeform.com", "fillout.com", "paperform.co", "plaid.com", "wise.com",
    "mercury.com", "deel.com", "remote.com", "rippling.com",
}


def _host(url: str) -> str:
    host = (urlsplit(url).hostname or "").lower().rstrip(".")
    return host[4:] if host.startswith("www.") else host


def validate_fresh_pool() -> None:
    if len(POOL) != 100 or len(set(POOL)) != 100:
        raise SystemExit(f"Fresh holdout must contain exactly 100 unique URLs; got {len(POOL)} / {len(set(POOL))}")

    hosts = [_host(url) for url in POOL]
    if len(set(hosts)) != len(hosts):
        raise SystemExit("Fresh holdout contains duplicate normalized hosts")

    external_overlap = sorted(set(hosts) & EXCLUDED_EXTERNAL_HOSTS)
    if external_overlap:
        raise SystemExit(f"Fresh holdout overlaps Issue #221: {external_overlap}")

    root = Path(__file__).resolve().parents[2]
    history_files = [
        *root.joinpath(".github", "scripts").glob("privacy_prv103*.py"),
        *root.joinpath("docs").glob("privacy*prv103*.md"),
        *root.joinpath("docs").glob("privacy*form*calibration*.md"),
    ]
    history_chunks: list[str] = []
    for path in history_files:
        if path.resolve() == CURRENT_FILE:
            continue
        history_chunks.append(path.read_text(encoding="utf-8", errors="ignore").lower())
    history = "\n".join(history_chunks)

    historical_overlap = sorted(host for host in hosts if host in history)
    if historical_overlap:
        raise SystemExit(f"Fresh holdout host(s) already present in versioned PRV-103 history: {historical_overlap}")

    print(json.dumps({"candidate_sites": len(POOL), "freshness": "pass", "historical_overlap": []}, indent=2))


def _normalized(value: str | None) -> str:
    return " ".join((value or "").casefold().split())


def _dedupe_high(forms: list[dict]) -> list[dict]:
    seen: set[tuple[str, str, str, str]] = set()
    result: list[dict] = []
    for form in forms:
        if form.get("personal_confidence") != "high":
            continue
        key = tuple(_normalized(form.get(field)) for field in FIELDS)
        if key in seen:
            continue
        seen.add(key)
        result.append(form)
    return result


def _capture_status(case: dict, high_forms: list[dict]) -> str:
    if int(case.get("pages_analyzed") or 0) == 0:
        return "technical_failure"
    if not high_forms:
        return "inspected_no_high_confidence_personal_form"
    return "captured_high_confidence_personal_form"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--validate-only", action="store_true")
    args = parser.parse_args()

    validate_fresh_pool()
    if args.validate_only:
        return
    if ISSUE_NUMBER <= 0:
        raise SystemExit("Pool must be frozen in a GitHub Issue before capture; ISSUE_NUMBER is not set")

    catalog = load_control_catalog()
    scoring = load_scoring()
    if catalog.get("version") != EXPECTED_FRAMEWORK_VERSION:
        raise SystemExit(f"Expected framework {EXPECTED_FRAMEWORK_VERSION}, got {catalog.get('version')}")
    if scoring.get("version") != EXPECTED_SCORING_VERSION:
        raise SystemExit(f"Expected scoring {EXPECTED_SCORING_VERSION}, got {scoring.get('version')}")

    blind_forms: list[dict] = []
    sealed_sites: list[dict] = []
    sealed_predictions: list[dict] = []

    for site_index, requested_url in enumerate(POOL, start=1):
        site_id = f"HF-S{site_index:03d}"
        case, forms = inspect_case(site_id, "qa_final_fresh", "frozen_holdout", "unknown", requested_url)
        high_forms = _dedupe_high(forms)
        sealed_sites.append({
            "site_id": site_id,
            "requested_url": requested_url,
            "capture_status": _capture_status(case, high_forms),
            "captured_form_count": len(high_forms),
            "pages_requested": case.get("pages_requested"),
            "pages_analyzed": case.get("pages_analyzed"),
            "errors": case.get("errors") or [],
        })

        for form_index, form in enumerate(high_forms, start=1):
            blind_id = f"{site_id}-F{form_index:02d}"
            blind_forms.append({
                "blind_id": blind_id,
                "heading": form.get("heading"),
                "legend": form.get("legend"),
                "introductory_text": form.get("introductory_text"),
                "submit_text": form.get("submit_text"),
            })
            sealed_predictions.append({
                "blind_id": blind_id,
                "site_id": site_id,
                "requested_url": requested_url,
                "source_url": form.get("source_url"),
                "form_prediction": form.get("product_purpose"),
            })

    metadata = {
        "product_sha": FROZEN_SHA,
        "framework_version": EXPECTED_FRAMEWORK_VERSION,
        "scoring_version": EXPECTED_SCORING_VERSION,
        "issue": ISSUE_NUMBER,
        "candidate_sites": len(POOL),
        "replacement_policy": "none",
        "selection_policy": "all deduplicated personal HIGH forms from all frozen candidate sites",
    }

    blind_payload = {
        "metadata": {
            "product_sha": FROZEN_SHA,
            "framework_version": EXPECTED_FRAMEWORK_VERSION,
            "candidate_sites": len(POOL),
            "issue": ISSUE_NUMBER,
        },
        "instructions": "Adjudicate every blind_id using only the four visible text fields. Freeze gold before opening Artifact B.",
        "forms": blind_forms,
    }
    prediction_payload = {
        "metadata": metadata,
        "instructions": "Open only after gold is frozen from Artifact A.",
        "sites": sealed_sites,
        "predictions": sealed_predictions,
    }

    root = Path("artifacts/privacy-prv103-final-fresh")
    blind_dir = root / "artifact-a-blind"
    prediction_dir = root / "artifact-b-predictions"
    blind_dir.mkdir(parents=True, exist_ok=True)
    prediction_dir.mkdir(parents=True, exist_ok=True)

    (blind_dir / "README.md").write_text(
        "# PRV-103 0.8 — final fresh holdout — Artifact A\n\nOpen this artifact first. Adjudicate every `blind_id` using only `heading`, `legend`, `introductory_text`, and `submit_text`. Freeze the gold before opening Artifact B. URLs and Mininode predictions are intentionally absent.\n",
        encoding="utf-8",
    )
    (blind_dir / "blind-evidence.json").write_text(json.dumps(blind_payload, ensure_ascii=False, indent=2), encoding="utf-8")
    (prediction_dir / "README.md").write_text(
        "# PRV-103 0.8 — final fresh holdout — Artifact B\n\nDo not open until the gold from Artifact A is frozen. This artifact contains site mapping, technical capture status, and deterministic Mininode predictions.\n",
        encoding="utf-8",
    )
    (prediction_dir / "predictions.json").write_text(json.dumps(prediction_payload, ensure_ascii=False, indent=2), encoding="utf-8")

    summary = {
        "candidate_sites": len(POOL),
        "sites_with_high_confidence_forms": sum(s["capture_status"] == "captured_high_confidence_personal_form" for s in sealed_sites),
        "technical_failures": sum(s["capture_status"] == "technical_failure" for s in sealed_sites),
        "blind_forms": len(blind_forms),
    }
    print("PRV103_FINAL_FRESH_SUMMARY_START")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print("PRV103_FINAL_FRESH_SUMMARY_END")


if __name__ == "__main__":
    main()
