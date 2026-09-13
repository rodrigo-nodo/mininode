"""Capture the blind Artifact A for the frozen PRV-103 framework 0.9 holdout."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import time
from pathlib import Path
from urllib.parse import urlsplit

from mininode_api.domain_packs.privacy.evidence_adapter import _personal_form
from mininode_api.web_inspector import (
    InspectionFetchResult,
    WebFetcher,
    build_evidence,
    discover_include_links,
    extract_page,
    select_pages,
)
from mininode_api.web_inspector.fetcher import INSPECTION_BUDGET_SECONDS

FROZEN_PRODUCT_SHA = "6fbe6f94887114f4a5459af861f1fcaa0c4b7bd7"
FROZEN_POOL_SHA256 = "33383fc229068633915d215404f0c9e0d368a1c7d2d968ad7047b97c1136b14a"
EXPECTED_CANDIDATES = 99
MINIMUM_ELIGIBLE_FOR_REVIEW = 30
ALLOWED_FIELDS = ("heading", "legend", "introductory_text", "submit_text")


def repository_root() -> Path:
    return Path(__file__).resolve().parents[2]


def normalize_hostname(value: str) -> str:
    parsed = urlsplit(value if "://" in value else f"https://{value}")
    hostname = (parsed.hostname or "").lower().rstrip(".")
    return hostname.removeprefix("www.")


def load_frozen_candidates(root: Path | None = None) -> list[str]:
    root = root or repository_root()
    path = root / "docs/evidence/prv103-holdout-0.9-candidates.txt"
    payload = path.read_bytes()
    digest = hashlib.sha256(payload).hexdigest()
    if digest != FROZEN_POOL_SHA256:
        raise AssertionError(f"frozen pool hash mismatch: {digest}")
    candidates = [normalize_hostname(line) for line in payload.decode().splitlines() if line.strip()]
    if len(candidates) != EXPECTED_CANDIDATES or len(set(candidates)) != EXPECTED_CANDIDATES:
        raise AssertionError("frozen pool must contain exactly 99 unique hostnames")
    return candidates


def _compact(value: str | None, limit: int) -> str | None:
    compact = " ".join((value or "").split())[:limit]
    return compact or None


def _redact_identity(value: str | None, hostname: str, limit: int) -> str | None:
    value = _compact(value, limit)
    if value is None:
        return None
    labels = [label for label in hostname.split(".")[:-1] if len(label) >= 4]
    patterns = [re.escape(hostname), *(rf"\b{re.escape(label)}\b" for label in labels)]
    redacted = re.sub("|".join(patterns), "[sitio]", value, flags=re.IGNORECASE)
    return _compact(redacted, limit)


def _deduplicated_high_forms(forms: list) -> list[tuple[int, object]]:
    seen: set[tuple[str, ...]] = set()
    selected = []
    for form_index, form in enumerate(forms):
        is_personal, confidence = _personal_form(form)
        if not is_personal or confidence != "high":
            continue
        key = tuple(" ".join((getattr(form, field) or "").casefold().split()) for field in ALLOWED_FIELDS)
        if key in seen:
            continue
        seen.add(key)
        selected.append((form_index, form))
    return selected


def artifact_a_item(blind_id: str, form, hostname: str) -> dict[str, str | None]:
    limits = {"heading": 160, "legend": 160, "introductory_text": 300, "submit_text": 120}
    return {
        "blind_id": blind_id,
        **{
            field: _redact_identity(getattr(form, field), hostname, limits[field])
            for field in ALLOWED_FIELDS
        },
    }


def inspect_candidate(hostname: str) -> tuple[dict, list]:
    requested = f"https://{hostname}/"
    deadline = time.monotonic() + INSPECTION_BUDGET_SECONDS
    status = {"hostname": hostname, "requested_url": requested, "status": "error", "pages_fetched": 0}
    with WebFetcher(inspection_budget=INSPECTION_BUDGET_SECONDS) as fetcher:
        home = fetcher.fetch(requested, [requested], deadline=deadline)
        if not home.pages or home.pages[0].error or home.pages[0].html is None or not home.pages[0].final_url:
            status["error"] = home.errors[0].code if home.errors else "home_fetch_failed"
            return status, []
        page = home.pages[0]
        extracted = extract_page(page.html, page.final_url)
        try:
            includes = discover_include_links(page.html, page.final_url, fetcher=fetcher, deadline=deadline)
        except Exception as exc:  # Public-site variance must not stop the remaining pool.
            includes = []
            status["include_error"] = type(exc).__name__
        selected_urls = select_pages(page.final_url, [*extracted.links, *includes])
        remaining = [url for url in selected_urls if url != page.final_url]
        extra = fetcher.fetch(page.final_url, remaining, deadline=deadline) if remaining else None
        combined = InspectionFetchResult(
            target_url=requested,
            pages_requested=1 + len(remaining),
            pages_fetched=home.pages_fetched + (extra.pages_fetched if extra else 0),
            pages=[*home.pages, *(extra.pages if extra else [])],
            errors=[*home.errors, *(extra.errors if extra else [])],
            limited=home.limited or bool(extra and extra.limited),
        )
        contract = build_evidence(combined, additional_links=includes)
        status.update(status="captured", pages_fetched=combined.pages_fetched)
        return status, _deduplicated_high_forms(contract.forms)


def capture(output_dir: Path, root: Path | None = None) -> dict:
    candidates = load_frozen_candidates(root)
    output_dir.mkdir(parents=True, exist_ok=True)
    artifact_a: list[dict] = []
    manifest: list[dict] = []
    for site_index, hostname in enumerate(candidates, 1):
        row, forms = inspect_candidate(hostname)
        row["candidate_index"] = site_index
        row["eligible_high_forms"] = len(forms)
        row["cases"] = []
        for form_index, form in forms:
            blind_id = f"QA09-A-{len(artifact_a) + 1:03d}"
            artifact_a.append(artifact_a_item(blind_id, form, hostname))
            row["cases"].append(
                {"blind_id": blind_id, "source_url": form.source_url, "form_index": form_index}
            )
        manifest.append(row)

    summary = {
        "frozen_product_sha": FROZEN_PRODUCT_SHA,
        "frozen_pool_sha256": FROZEN_POOL_SHA256,
        "candidate_sites": len(candidates),
        "sites_processed": len(manifest),
        "eligible_high_forms": len(artifact_a),
        "minimum_required": MINIMUM_ELIGIBLE_FOR_REVIEW,
        "sufficient": len(artifact_a) >= MINIMUM_ELIGIBLE_FOR_REVIEW,
        "artifact_a_fields": ["blind_id", *ALLOWED_FIELDS],
        "prv103_executed": False,
    }
    (output_dir / "artifact-a.json").write_text(
        json.dumps(artifact_a, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    (output_dir / "internal-manifest.json").write_text(
        json.dumps({"summary": summary, "sites": manifest}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return summary


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, default=Path("artifacts/privacy-prv103-qa09"))
    args = parser.parse_args()
    summary = capture(args.output_dir)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if summary["sufficient"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
