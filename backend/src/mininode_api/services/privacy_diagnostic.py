"""In-memory orchestration for URL-based privacy diagnostics."""

from __future__ import annotations

import json
import logging
from collections.abc import Callable
from time import monotonic
from urllib.parse import urlsplit

from mininode_api.domain_packs.privacy.diagnostic import run_privacy_diagnostic
from mininode_api.domain_packs.privacy.prv103_shadow import enqueue_prv103_shadow
from mininode_api.web_inspector import (
    PageCandidate,
    WebFetcher,
    build_evidence,
    classify_page_candidates,
    discover_include_links,
    extract_page,
)
from mininode_api.web_inspector.fetcher import INSPECTION_BUDGET_SECONDS
from mininode_api.web_inspector.models import EvidenceContract, InspectionFetchResult

logger = logging.getLogger(__name__)

MAX_PAGES_ATTEMPTED = 5
_CATEGORY_ORDER = ("privacy", "contact", "action")
_EXPANDABLE_RESULTS_BY_CONTROL = {
    "PRV-002": frozenset({"partial", "not_evaluable"}),
    "PRV-003": frozenset({"partial", "not_evaluable"}),
    "PRV-301": frozenset({"not_detected", "partial", "not_evaluable"}),
    "PRV-101": frozenset({"not_detected", "partial", "not_evaluable"}),
    "PRV-104": frozenset({"not_detected", "partial", "not_evaluable"}),
}
_CATEGORIES_BY_EXPANDABLE_CONTROL = {
    "PRV-002": frozenset({"privacy"}),
    "PRV-003": frozenset({"privacy"}),
    "PRV-101": frozenset({"contact", "action"}),
    "PRV-104": frozenset({"contact", "action"}),
    "PRV-301": frozenset({"contact"}),
}


class PrivacyInspectionError(Exception):
    """A controlled failure inspecting the initial page."""

    def __init__(self, code: str, *, diagnostic: dict | None = None) -> None:
        super().__init__(code)
        self.code = code
        self.diagnostic = diagnostic


def validate_public_url_format(url: str) -> str:
    """Apply format-only checks; Web Inspector remains the SSRF authority."""

    value = url.strip()
    try:
        parsed = urlsplit(value)
        valid_port = parsed.port
    except ValueError as exc:
        raise PrivacyInspectionError("invalid_url") from exc
    if not value or parsed.scheme.lower() not in {"http", "https"} or not parsed.hostname:
        raise PrivacyInspectionError("invalid_url")
    del valid_port
    return value


def _page_diagnostic(result: InspectionFetchResult) -> dict:
    """Return a compact, non-sensitive technical snapshot for internal diagnostics."""

    page = result.pages[0] if result.pages else None
    error = page.error if page and page.error else None
    requested_url = page.requested_url if page else result.target_url
    requested_hostname = (
        page.requested_hostname
        if page and page.requested_hostname
        else (urlsplit(requested_url).hostname or "").rstrip(".").lower() or None
    )
    effective_url = page.final_url if page else None
    effective_hostname = (
        page.effective_hostname
        if page and page.effective_hostname
        else ((urlsplit(effective_url).hostname or "").rstrip(".").lower() if effective_url else None)
    )
    return {
        "requested_url": requested_url,
        "final_url": effective_url,
        "requested_hostname": requested_hostname,
        "effective_hostname": effective_hostname,
        "internal_error_code": error.code if error else "inspection_failed",
        "failure_phase": page.failure_phase if page else "home_fetch",
        "dns_attempt_count": page.dns_attempt_count if page else 0,
        "dns_failure_category": page.dns_failure_category if page else None,
        "network_family": page.network_family if page else None,
        "attempted_network_families": list(page.attempted_network_families) if page else [],
        "resolved_addresses": list(page.resolved_addresses) if page else [],
        "rejected_addresses": list(page.rejected_addresses) if page else [],
        "ssrf_rejection_reason": page.ssrf_rejection_reason if page else None,
        "transport_error_class": page.transport_error_class if page else None,
        "tls_valid": page.tls_valid if page else None,
        "redirect_count": page.redirect_count if page else 0,
        "status_code": page.status_code if page else None,
        "elapsed_ms": page.elapsed_ms if page else 0,
        "connection_attempts": list(page.connection_attempts) if page else [],
    }


def _home_failure(result: InspectionFetchResult) -> None:
    page = result.pages[0] if result.pages else None
    error = page.error if page and page.error else None
    diagnostic = _page_diagnostic(result)
    event = {
        "event": "privacy_home_inspection_failed",
        "hostname": diagnostic["requested_hostname"],
        "effective_hostname": diagnostic["effective_hostname"],
        "phase": diagnostic["failure_phase"],
        "error_code": diagnostic["internal_error_code"],
        "failure_class": "controlled_fetch_error",
        "network_family": diagnostic["network_family"],
        "attempted_network_families": diagnostic["attempted_network_families"],
        "transport_error_class": diagnostic["transport_error_class"],
        "redirect_count": diagnostic["redirect_count"],
        "status_code": diagnostic["status_code"],
        "elapsed_ms": diagnostic["elapsed_ms"],
        "resolved_addresses": diagnostic["resolved_addresses"],
        "rejected_addresses": diagnostic["rejected_addresses"],
        "ssrf_rejection_reason": diagnostic["ssrf_rejection_reason"],
        "connection_attempts": diagnostic["connection_attempts"],
    }
    logger.warning(json.dumps(event, separators=(",", ":"), sort_keys=True))
    if error is None:
        raise PrivacyInspectionError("inspection_failed", diagnostic=diagnostic)
    if error.code == "blocked_by_ssrf":
        raise PrivacyInspectionError("unsafe_target", diagnostic=diagnostic)
    if error.code == "robots_disallowed":
        raise PrivacyInspectionError("inspection_blocked", diagnostic=diagnostic)
    failure_codes = {
        "dns_failure": "dns_resolution_failed",
        "timeout": "request_timeout",
        "tls_certificate_error": "tls_failure",
        "tls_error": "tls_failure",
        "http_error": "http_fetch_failed",
        "unsupported_content_type": "unsupported_content_type",
    }
    if error.code in failure_codes:
        raise PrivacyInspectionError(failure_codes[error.code], diagnostic=diagnostic)
    raise PrivacyInspectionError("inspection_failed", diagnostic=diagnostic)


def _result_map(diagnostic: dict) -> dict[str, str]:
    return {item["control_code"]: item["result"] for item in diagnostic["controls"]}


def _remaining_adaptive_gaps(diagnostic: dict) -> dict[str, frozenset[str]]:
    """Return the current control-to-category adaptive policy matches."""

    results = _result_map(diagnostic)
    return {
        control: _CATEGORIES_BY_EXPANDABLE_CONTROL[control]
        for control in sorted(_CATEGORIES_BY_EXPANDABLE_CONTROL)
        if results.get(control) in _EXPANDABLE_RESULTS_BY_CONTROL[control]
    }


def _needed_categories(diagnostic: dict) -> set[str]:
    """Map resolvable evaluator gaps to candidate categories.

    ``not_evaluable`` is expandable only for the controls where a concrete
    Privacy, Contact, or Action candidate can supply the missing evidence.
    ``detected`` and ``not_applicable`` do not expand. PRV-001, PRV-201, and
    PRV-501 never cause expansion.
    """

    return {
        category
        for categories in _remaining_adaptive_gaps(diagnostic).values()
        for category in categories
    }


def _next_candidate(
    candidates: list[PageCandidate], attempted_urls: set[str], needed: set[str]
) -> PageCandidate | None:
    for category in _CATEGORY_ORDER:
        if category not in needed:
            continue
        available = [
            candidate
            for candidate in candidates
            if candidate.category == category and candidate.url not in attempted_urls
        ]
        if available:
            return min(available, key=lambda candidate: candidate.rank)
    return None


def diagnose_privacy_url(
    url: str,
    *,
    fetcher_factory: Callable[..., WebFetcher] | None = None,
) -> dict:
    """Inspect HOME, then only candidates relevant to current Privacy gaps."""

    target_url = validate_public_url_format(url)
    factory = fetcher_factory or WebFetcher
    started = monotonic()
    deadline = started + INSPECTION_BUDGET_SECONDS
    attempted_urls: set[str] = {target_url}
    categories_attempted: list[str] = []

    with factory(inspection_budget=INSPECTION_BUDGET_SECONDS) as fetcher:
        home_result = fetcher.fetch(target_url, [target_url], deadline=deadline)
        if home_result.pages_fetched != 1 or not home_result.pages:
            _home_failure(home_result)
        home_page = home_result.pages[0]
        if home_page.error or home_page.html is None or home_page.final_url is None:
            _home_failure(home_result)

        home_evidence = extract_page(home_page.html, home_page.final_url)
        include_links = discover_include_links(
            home_page.html,
            home_page.final_url,
            fetcher=fetcher,
            deadline=deadline,
        )
        candidates = classify_page_candidates(
            home_page.final_url, [*home_evidence.links, *include_links]
        )
        attempted_urls.add(home_page.final_url)
        combined = InspectionFetchResult(
            target_url=target_url,
            pages_requested=1,
            pages_fetched=1,
            pages=list(home_result.pages),
            errors=list(home_result.errors),
        )
        latest_contract: EvidenceContract | None = None

        def evaluate() -> dict:
            nonlocal latest_contract
            latest_contract = build_evidence(combined, additional_links=include_links)
            return run_privacy_diagnostic(latest_contract)

        diagnostic = evaluate()
        while True:
            needed = _needed_categories(diagnostic)
            if not needed:
                stop_reason = "no_resolvable_gaps"
                break
            if combined.pages_requested >= MAX_PAGES_ATTEMPTED:
                stop_reason = "max_pages"
                combined.limited = True
                break
            if monotonic() >= deadline:
                stop_reason = "deadline"
                combined.limited = True
                break
            candidate = _next_candidate(candidates, attempted_urls, needed)
            if candidate is None:
                stop_reason = "no_candidates"
                break

            attempted_urls.add(candidate.url)
            categories_attempted.append(candidate.category)
            result = fetcher.fetch(home_page.final_url, [candidate.url], deadline=deadline)
            combined.pages_requested += 1
            combined.pages.extend(result.pages)
            combined.errors.extend(result.errors)
            combined.pages_fetched += result.pages_fetched
            combined.limited |= result.limited
            combined.limited |= combined.pages_requested >= MAX_PAGES_ATTEMPTED
            diagnostic = evaluate()

    if latest_contract is not None:
        try:
            enqueue_prv103_shadow(latest_contract)
        except Exception:
            logger.warning(
                json.dumps(
                    {"event": "privacy_prv103_shadow_failed", "reason": "enqueue_error"},
                    separators=(",", ":"),
                    sort_keys=True,
                )
            )

    diagnostic["scope"] = {
        "pages_requested": combined.pages_requested,
        "pages_analyzed": combined.pages_fetched,
        "limited": combined.limited,
    }
    # The effective HOME URL is the canonical site identity for downstream
    # products built from this exact inspection (including followed redirects).
    diagnostic["site_url"] = home_page.final_url
    elapsed_ms = max(0, round((monotonic() - started) * 1000))
    remaining_gaps = _remaining_adaptive_gaps(diagnostic)
    remaining_categories = {
        category for categories in remaining_gaps.values() for category in categories
    }
    logger.info(
        json.dumps(
            {
                "event": "privacy_adaptive_scope_completed",
                "hostname": (urlsplit(home_page.final_url).hostname or "")
                .rstrip(".")
                .lower()
                or None,
                "pages_attempted": combined.pages_requested,
                "pages_analyzed": combined.pages_fetched,
                "candidate_count": len(candidates),
                "expansion_triggered": combined.pages_requested > 1,
                "stop_reason": stop_reason,
                "elapsed_ms": elapsed_ms,
                "categories_attempted": categories_attempted,
                "remaining_gap_controls": list(remaining_gaps),
                "remaining_gap_categories": [
                    category
                    for category in _CATEGORY_ORDER
                    if category in remaining_categories
                ],
            },
            separators=(",", ":"),
            sort_keys=True,
        )
    )
    return diagnostic
