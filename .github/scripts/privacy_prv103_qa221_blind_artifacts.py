from __future__ import annotations

import json
from pathlib import Path

from mininode_api.domain_packs.privacy.evaluator import load_control_catalog
from mininode_api.domain_packs.privacy.scoring import load_scoring
from privacy_prv103_qa4 import inspect_case

FROZEN_SHA = "244671de83e5463d1f65a4bd7e2d561bc2f38fd5"
EXPECTED_FRAMEWORK_VERSION = "0.8"
EXPECTED_SCORING_VERSION = "0.1"
ISSUE_NUMBER = 221
FIELDS = ("heading", "legend", "introductory_text", "submit_text")

POOL = [
    "https://workleap.com/",
    "https://www.pigment.com/",
    "https://mistral.ai/",
    "https://www.harvey.ai/",
    "https://www.clay.com/",
    "https://lovable.dev/",
    "https://replit.com/",
    "https://cursor.com/",
    "https://supabase.com/",
    "https://planetscale.com/",
    "https://motherduck.com/",
    "https://clickhouse.com/",
    "https://www.together.ai/",
    "https://cohere.com/",
    "https://www.pinecone.io/",
    "https://weaviate.io/",
    "https://qdrant.tech/",
    "https://modal.com/",
    "https://fly.io/",
    "https://railway.com/",
    "https://render.com/",
    "https://sentry.io/",
    "https://snyk.io/",
    "https://semgrep.dev/",
    "https://tailscale.com/",
    "https://www.zerotier.com/",
    "https://proton.me/",
    "https://mullvad.net/",
    "https://ghost.org/",
    "https://webflow.com/",
    "https://www.framer.com/",
    "https://www.typeform.com/",
    "https://www.fillout.com/",
    "https://paperform.co/",
    "https://plaid.com/",
    "https://wise.com/",
    "https://mercury.com/",
    "https://www.deel.com/",
    "https://remote.com/",
    "https://www.rippling.com/",
]


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


def _blind_readme() -> str:
    return """# PRV-103 0.8 — QA #221 — Artifact A (evidencia ciega)\n\nAbrir este artifact antes que el Artifact B.\n\nAdjudicar cada `blind_id` usando exclusivamente `heading`, `legend`, `introductory_text` y `submit_text`.\nClases permitidas: `concrete`, `generic`, `none`, `unknown`.\nCongelar el gold antes de abrir el Artifact B.\n\nEl pool corresponde exactamente al Issue #221. No se agregaron ni reemplazaron sitios.\nLos sitios sin formularios personales de alta confianza o con fallo técnico permanecen registrados en `sites`.\n"""


def _prediction_readme() -> str:
    return """# PRV-103 0.8 — QA #221 — Artifact B (predicciones)\n\nNO abrir antes de congelar el gold construido con el Artifact A.\n\n`form_prediction` contiene la clasificación determinística de PRV-103 para el mismo `blind_id`: `concrete`, `generic`, `none` o `unknown`.\nEl pool y los identificadores son los mismos del Artifact A.\n"""


def main() -> None:
    if len(POOL) != 40 or len(set(POOL)) != 40:
        raise SystemExit("QA #221 pool must contain exactly 40 unique frozen URLs")

    catalog = load_control_catalog()
    scoring = load_scoring()
    if catalog.get("version") != EXPECTED_FRAMEWORK_VERSION:
        raise SystemExit(f"Expected framework {EXPECTED_FRAMEWORK_VERSION}, got {catalog.get('version')}")
    if scoring.get("version") != EXPECTED_SCORING_VERSION:
        raise SystemExit(f"Expected scoring {EXPECTED_SCORING_VERSION}, got {scoring.get('version')}")

    blind_sites: list[dict] = []
    blind_forms: list[dict] = []
    predictions: list[dict] = []

    for site_index, requested_url in enumerate(POOL, start=1):
        site_id = f"H221-S{site_index:02d}"
        case, forms = inspect_case(site_id, "qa221", "frozen_holdout", "unknown", requested_url)
        high_forms = _dedupe_high(forms)

        blind_sites.append(
            {
                "site_id": site_id,
                "requested_url": requested_url,
                "capture_status": _capture_status(case, high_forms),
                "captured_form_count": len(high_forms),
            }
        )

        for form_index, form in enumerate(high_forms, start=1):
            blind_id = f"{site_id}-F{form_index:02d}"
            blind_forms.append(
                {
                    "blind_id": blind_id,
                    "site_id": site_id,
                    "requested_url": requested_url,
                    "source_url": form.get("source_url"),
                    "heading": form.get("heading"),
                    "legend": form.get("legend"),
                    "introductory_text": form.get("introductory_text"),
                    "submit_text": form.get("submit_text"),
                }
            )
            predictions.append(
                {
                    "blind_id": blind_id,
                    "site_id": site_id,
                    "form_prediction": form.get("product_purpose"),
                }
            )

    metadata = {
        "product_sha": FROZEN_SHA,
        "framework_version": EXPECTED_FRAMEWORK_VERSION,
        "scoring_version": EXPECTED_SCORING_VERSION,
        "issue": ISSUE_NUMBER,
        "candidate_sites": len(POOL),
        "replacement_policy": "none",
    }

    blind_payload = {
        "metadata": metadata,
        "instructions": "Adjudicate and freeze gold before opening Artifact B.",
        "sites": blind_sites,
        "forms": blind_forms,
    }
    prediction_payload = {
        "metadata": metadata,
        "instructions": "Open only after gold is frozen from Artifact A.",
        "predictions": predictions,
    }

    root = Path("artifacts/privacy-prv103-qa221")
    blind_dir = root / "artifact-a-blind"
    prediction_dir = root / "artifact-b-predictions"
    blind_dir.mkdir(parents=True, exist_ok=True)
    prediction_dir.mkdir(parents=True, exist_ok=True)

    (blind_dir / "README.md").write_text(_blind_readme(), encoding="utf-8")
    (blind_dir / "blind-evidence.json").write_text(
        json.dumps(blind_payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (prediction_dir / "README.md").write_text(_prediction_readme(), encoding="utf-8")
    (prediction_dir / "predictions.json").write_text(
        json.dumps(prediction_payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    summary = {
        "candidate_sites": len(POOL),
        "sites_with_high_confidence_forms": sum(
            site["capture_status"] == "captured_high_confidence_personal_form" for site in blind_sites
        ),
        "technical_failures": sum(site["capture_status"] == "technical_failure" for site in blind_sites),
        "blind_forms": len(blind_forms),
    }
    print("PRV103_QA221_SUMMARY_START")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print("PRV103_QA221_SUMMARY_END")


if __name__ == "__main__":
    main()
