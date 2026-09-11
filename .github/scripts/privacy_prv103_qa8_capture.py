from __future__ import annotations

import argparse
import json
from pathlib import Path
from urllib.parse import urlsplit

from privacy_prv103_qa4 import inspect_case

FROZEN_MAIN_SHA = "2fcf1c093023d6761cce5460a0a85779f5b0d180"
EXPECTED_FRAMEWORK_VERSION = "0.7"
MAX_SITES = 100
TARGET_SITES = 30
ALLOWED_FIELDS = ("heading", "legend", "introductory_text", "submit_text")

# Frozen before inspecting QA8 outputs. These sites were selected to be outside
# the QA1-QA7 / semantic-development corpus recorded in the repository.
CANDIDATES = [
    ("Q8I001", "SaaS", "en", "https://clickup.com/"),
    ("Q8I002", "SaaS", "en", "https://monday.com/"),
    ("Q8I003", "SaaS", "en", "https://linear.app/"),
    ("Q8I004", "SaaS", "en", "https://slack.com/"),
    ("Q8I005", "SaaS", "en", "https://zoom.us/"),
    ("Q8I006", "SaaS", "en", "https://www.intercom.com/"),
    ("Q8I007", "SaaS", "en", "https://www.zendesk.com/"),
    ("Q8I008", "Marketing", "en", "https://www.klaviyo.com/"),
    ("Q8I009", "Marketing", "en", "https://www.activecampaign.com/"),
    ("Q8I010", "Marketing", "en", "https://www.braze.com/"),
    ("Q8I011", "Marketing", "en", "https://postmarkapp.com/"),
    ("Q8I012", "Marketing", "en", "https://www.beehiiv.com/"),
    ("Q8I013", "Marketing", "en", "https://www.campaignmonitor.com/"),
    ("Q8I014", "Marketing", "en", "https://www.constantcontact.com/"),
    ("Q8I015", "Marketing", "en", "https://www.omnisend.com/"),
    ("Q8I016", "Sales", "en", "https://www.gong.io/"),
    ("Q8I017", "Sales", "en", "https://www.outreach.io/"),
    ("Q8I018", "Sales", "en", "https://www.salesloft.com/"),
    ("Q8I019", "Sales", "en", "https://www.apollo.io/"),
    ("Q8I020", "Sales", "en", "https://www.close.com/"),
    ("Q8I021", "Sales", "en", "https://www.copper.com/"),
    ("Q8I022", "Sales", "en", "https://attio.com/"),
    ("Q8I023", "Forms", "en", "https://tally.so/"),
    ("Q8I024", "Forms", "en", "https://www.cognitoforms.com/"),
    ("Q8I025", "Forms", "en", "https://www.formsite.com/"),
    ("Q8I026", "Forms", "en", "https://www.123formbuilder.com/"),
    ("Q8I027", "Commerce", "en", "https://www.shopify.com/"),
    ("Q8I028", "Commerce", "en", "https://www.bigcommerce.com/"),
    ("Q8I029", "Commerce", "en", "https://woocommerce.com/"),
    ("Q8I030", "Commerce", "en", "https://commercetools.com/"),
    ("Q8I031", "Fintech", "en", "https://stripe.com/"),
    ("Q8I032", "Fintech", "en", "https://www.paypal.com/"),
    ("Q8I033", "Fintech", "en", "https://squareup.com/"),
    ("Q8I034", "Fintech", "en", "https://www.airwallex.com/"),
    ("Q8I035", "Fintech", "en", "https://www.marqeta.com/"),
    ("Q8I036", "Fintech", "en", "https://www.alloy.com/"),
    ("Q8I037", "Identity", "en", "https://withpersona.com/"),
    ("Q8I038", "Fintech", "en", "https://www.sardine.ai/"),
    ("Q8I039", "Fintech", "en", "https://www.chainalysis.com/"),
    ("Q8I040", "Fintech", "en", "https://www.fireblocks.com/"),
    ("Q8I041", "Fintech", "en", "https://www.circle.com/"),
    ("Q8I042", "Fintech", "en", "https://www.coinbase.com/"),
    ("Q8I043", "Security", "en", "https://www.vanta.com/"),
    ("Q8I044", "Security", "en", "https://drata.com/"),
    ("Q8I045", "Security", "en", "https://secureframe.com/"),
    ("Q8I046", "Security", "en", "https://www.wiz.io/"),
    ("Q8I047", "Security", "en", "https://www.crowdstrike.com/"),
    ("Q8I048", "Security", "en", "https://www.sentinelone.com/"),
    ("Q8I049", "Identity", "en", "https://www.okta.com/"),
    ("Q8I050", "Identity", "en", "https://auth0.com/"),
    ("Q8I051", "Security", "en", "https://www.keepersecurity.com/"),
    ("Q8I052", "Security", "en", "https://bitwarden.com/"),
    ("Q8I053", "Cloud", "en", "https://vercel.com/"),
    ("Q8I054", "Cloud", "en", "https://www.netlify.com/"),
    ("Q8I055", "Cloud", "en", "https://www.digitalocean.com/"),
    ("Q8I056", "Cloud", "en", "https://www.vultr.com/"),
    ("Q8I057", "Cloud", "en", "https://www.ovhcloud.com/"),
    ("Q8I058", "Cloud", "en", "https://www.scaleway.com/"),
    ("Q8I059", "Cloud", "en", "https://kinsta.com/"),
    ("Q8I060", "Cloud", "en", "https://wpengine.com/"),
    ("Q8I061", "Data", "en", "https://www.mongodb.com/"),
    ("Q8I062", "Data", "en", "https://www.cockroachlabs.com/"),
    ("Q8I063", "Data", "en", "https://neon.com/"),
    ("Q8I064", "Data", "en", "https://turso.tech/"),
    ("Q8I065", "Data", "en", "https://upstash.com/"),
    ("Q8I066", "Data", "en", "https://redis.io/"),
    ("Q8I067", "Data", "en", "https://www.confluent.io/"),
    ("Q8I068", "Observability", "en", "https://www.elastic.co/"),
    ("Q8I069", "Observability", "en", "https://grafana.com/"),
    ("Q8I070", "Observability", "en", "https://sentry.io/"),
    ("Q8I071", "Observability", "en", "https://newrelic.com/"),
    ("Q8I072", "Observability", "en", "https://www.splunk.com/"),
    ("Q8I073", "Observability", "en", "https://www.dynatrace.com/"),
    ("Q8I074", "Observability", "en", "https://www.honeycomb.io/"),
    ("Q8I075", "Observability", "en", "https://www.pagerduty.com/"),
    ("Q8I076", "Analytics", "en", "https://mixpanel.com/"),
    ("Q8I077", "Analytics", "en", "https://amplitude.com/"),
    ("Q8I078", "Analytics", "en", "https://heap.io/"),
    ("Q8I079", "Analytics", "en", "https://www.fullstory.com/"),
    ("Q8I080", "Analytics", "en", "https://www.hotjar.com/"),
    ("Q8I081", "Analytics", "en", "https://contentsquare.com/"),
    ("Q8I082", "Analytics", "en", "https://posthog.com/"),
    ("Q8I083", "Data", "en", "https://www.rudderstack.com/"),
    ("Q8I084", "Data", "en", "https://segment.com/"),
    ("Q8I085", "Data", "en", "https://hightouch.com/"),
    ("Q8I086", "Data", "en", "https://www.getcensus.com/"),
    ("Q8I087", "Data", "en", "https://www.getdbt.com/"),
    ("Q8I088", "Data", "en", "https://www.fivetran.com/"),
    ("Q8I089", "Data", "en", "https://airbyte.com/"),
    ("Q8I090", "Data", "en", "https://dagster.io/"),
    ("Q8I091", "Data", "en", "https://www.astronomer.io/"),
    ("Q8I092", "Data", "en", "https://www.prefect.io/"),
    ("Q8I093", "Web", "en", "https://webflow.com/"),
    ("Q8I094", "Web", "en", "https://www.wix.com/"),
    ("Q8I095", "CMS", "en", "https://www.contentful.com/"),
    ("Q8I096", "CMS", "en", "https://www.storyblok.com/"),
    ("Q8I097", "CMS", "en", "https://prismic.io/"),
    ("Q8I098", "CMS", "en", "https://www.datocms.com/"),
    ("Q8I099", "CMS", "en", "https://www.builder.io/"),
    ("Q8I100", "CMS", "en", "https://strapi.io/"),
]

HISTORY_PATHS = [
    ".github/scripts/privacy_prv103_qa4.py",
    ".github/scripts/privacy_prv103_qa4_extension.py",
    ".github/scripts/privacy_prv103_intent_qa6_discovery.py",
    ".github/scripts/privacy_prv103_qa7_capture.py",
    "docs/privacy-form-evidence-real-calibration.md",
    "docs/privacy-prv103-real-calibration.md",
    "docs/privacy-prv103-real-calibration-qa2.md",
    "docs/privacy-prv103-real-calibration-qa3.md",
    "docs/privacy-prv103-real-calibration-qa4.md",
    "docs/privacy-prv103-calibration-fix4.md",
]


def _root() -> Path:
    return Path(__file__).resolve().parents[2]


def _host(url: str) -> str:
    host = (urlsplit(url).hostname or "").lower().rstrip(".")
    return host[4:] if host.startswith("www.") else host


def assert_fresh_candidates(root: Path | None = None) -> None:
    root = root or _root()
    history = "\n".join(
        (root / path).read_text(encoding="utf-8", errors="ignore").lower()
        for path in HISTORY_PATHS
        if (root / path).is_file()
    )
    duplicates = sorted({_host(url) for _, _, _, url in CANDIDATES if _host(url) in history})
    if duplicates:
        raise AssertionError(f"QA8 candidate host(s) already present in historical corpus: {duplicates}")


def _norm(value: str | None) -> str:
    return " ".join((value or "").casefold().split())


def unique_high(forms: list[dict]) -> list[dict]:
    seen: set[tuple[str, str, str, str]] = set()
    result: list[dict] = []
    for form in forms:
        if form.get("personal_confidence") != "high":
            continue
        key = tuple(_norm(form.get(field)) for field in ALLOWED_FIELDS)
        if key in seen:
            continue
        seen.add(key)
        result.append(form)
    return result


def blind_item(blind_id: str, form: dict) -> dict:
    return {"blind_id": blind_id, **{field: form.get(field) for field in ALLOWED_FIELDS}}


def reviewer_markdown(items: list[dict]) -> str:
    lines = [
        "# PRV-103 QA8 - paquete ciego independiente",
        "",
        "Clasifica cada caso usando exclusivamente heading, legend, introductory_text y submit_text.",
        "No uses conocimiento externo, URL, hostname, sector, campos del formulario ni resultados de Mininode/LLM.",
        "Clases permitidas: concrete, generic, none, unknown.",
        "Devuelve una clase por blind_id y una justificación breve basada solo en el texto visible.",
        "",
    ]
    for item in items:
        lines.append(f"## {item['blind_id']}")
        for field in ALLOWED_FIELDS:
            lines.append(f"- {field}: {item.get(field) or '(vacío)'}")
        lines.append("")
    return "\n".join(lines)


def capture(output_dir: Path) -> dict:
    assert_fresh_candidates()
    reviewer_dir = output_dir / "reviewer"
    internal_dir = output_dir / "internal"
    reviewer_dir.mkdir(parents=True, exist_ok=True)
    internal_dir.mkdir(parents=True, exist_ok=True)

    blind: list[dict] = []
    manifest: list[dict] = []
    attempted = 0

    for case_id, sector, language, url in CANDIDATES[:MAX_SITES]:
        if len(blind) >= TARGET_SITES:
            break
        attempted += 1
        row = {"case_id": case_id, "url": url, "status": "pending", "high_count": 0}
        try:
            case_result, forms = inspect_case(case_id, "qa8_fresh", sector, language, url)
            highs = unique_high(forms)
            row["status"] = "captured"
            row["high_count"] = len(highs)
            row["inspection"] = case_result
            if highs:
                blind_id = f"QA8-{len(blind) + 1:03d}"
                row["selected"] = True
                row["blind_id"] = blind_id
                row["selection_rule"] = "first deduplicated personal HIGH form in inspector order"
                blind.append(blind_item(blind_id, highs[0]))
            else:
                row["selected"] = False
                row["reason"] = "no_deduplicated_high_form"
        except Exception as exc:
            row["status"] = "error"
            row["selected"] = False
            row["reason"] = exc.__class__.__name__
        manifest.append(row)

    public_summary = {
        "qa_cycle": "PRV-103 QA8 fresh independent holdout",
        "frozen_main_sha": FROZEN_MAIN_SHA,
        "framework_version": EXPECTED_FRAMEWORK_VERSION,
        "candidate_sites_frozen": len(CANDIDATES),
        "max_sites": MAX_SITES,
        "target_distinct_sites": TARGET_SITES,
        "sites_attempted": attempted,
        "selected_distinct_sites": len(blind),
        "allowed_fields": list(ALLOWED_FIELDS),
        "selection_rule": "first deduplicated personal HIGH form per qualifying site, stop at 30 distinct sites or 100 attempts",
        "llm_calls": 0,
    }
    internal_summary = {**public_summary, "candidate_order": [url for _, _, _, url in CANDIDATES]}

    (reviewer_dir / "qa8_summary.json").write_text(json.dumps(public_summary, ensure_ascii=False, indent=2), encoding="utf-8")
    (reviewer_dir / "qa8_blind.json").write_text(json.dumps(blind, ensure_ascii=False, indent=2), encoding="utf-8")
    (reviewer_dir / "qa8_reviewer.md").write_text(reviewer_markdown(blind), encoding="utf-8")
    (internal_dir / "qa8_summary_internal.json").write_text(json.dumps(internal_summary, ensure_ascii=False, indent=2), encoding="utf-8")
    (internal_dir / "qa8_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return public_summary


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", default="artifacts/privacy-prv103-qa8")
    args = parser.parse_args()
    summary = capture(Path(args.output_dir))
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if summary["selected_distinct_sites"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
