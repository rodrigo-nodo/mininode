"""In-memory orchestration for URL-based privacy diagnostics."""

from __future__ import annotations

from collections.abc import Callable
from time import monotonic
from urllib.parse import urlsplit

from mininode_api.domain_packs.privacy.diagnostic import run_privacy_diagnostic
from mininode_api.web_inspector import (
    WebFetcher,
    build_evidence,
    discover_include_links,
    extract_page,
    select_pages,
)
from mininode_api.web_inspector.fetcher import INSPECTION_BUDGET_SECONDS
from mininode_api.web_inspector.models import FetchError, FetchPageResult, InspectionFetchResult


class PrivacyInspectionError(Exception):
    """A controlled failure inspecting the initial page."""

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


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


def _home_failure(result: InspectionFetchResult) -> None:
    error = result.pages[0].error if result.pages and result.pages[0].error else None
    if error is None:
        raise PrivacyInspectionError("inspection_failed")
    if error.code == "blocked_by_ssrf":
        raise PrivacyInspectionError("unsafe_target")
    if error.code == "robots_disallowed":
        raise PrivacyInspectionError("inspection_blocked")
    raise PrivacyInspectionError("inspection_failed")


def diagnose_privacy_url(
    url: str,
    *,
    fetcher_factory: Callable[..., WebFetcher] | None = None,
) -> dict:
    """Inspect one URL and run the existing Privacy diagnostic pipeline."""

    target_url = validate_public_url_format(url)
    factory = fetcher_factory or WebFetcher
    started = monotonic()
    with factory(inspection_budget=INSPECTION_BUDGET_SECONDS) as home_fetcher:
        home_result = home_fetcher.fetch(target_url, [target_url])
        if home_result.pages_fetched != 1 or not home_result.pages:
            _home_failure(home_result)

        home_page = home_result.pages[0]
        if home_page.error or home_page.html is None or home_page.final_url is None:
            _home_failure(home_result)

        home_evidence = extract_page(home_page.html, home_page.final_url)
        include_links = discover_include_links(
            home_page.html,
            home_page.final_url,
            lambda budget: factory(inspection_budget=budget),
            lambda: INSPECTION_BUDGET_SECONDS - (monotonic() - started),
        )
        selected = select_pages(
            home_page.final_url,
            [*home_evidence.links, *include_links],
            limit=5,
        )
        remaining = [page_url for page_url in selected if page_url != home_page.final_url]

    remaining_budget = INSPECTION_BUDGET_SECONDS - (monotonic() - started)
    if remaining and remaining_budget > 0:
        with factory(inspection_budget=remaining_budget) as secondary_fetcher:
            secondary_result = secondary_fetcher.fetch(home_page.final_url, remaining)
    elif remaining:
        errors = [
            FetchError("timeout", "Inspection time budget exceeded", page_url)
            for page_url in remaining
        ]
        secondary_result = InspectionFetchResult(
            target_url=home_page.final_url,
            pages_requested=len(remaining),
            pages=[
                FetchPageResult(requested_url=error.url, error=error)
                for error in errors
            ],
            errors=errors,
        )
    else:
        secondary_result = InspectionFetchResult(
            target_url=home_page.final_url,
            pages_requested=0,
        )

    combined = InspectionFetchResult(
        target_url=target_url,
        pages_requested=len(selected),
        pages_fetched=home_result.pages_fetched + secondary_result.pages_fetched,
        pages=[*home_result.pages, *secondary_result.pages],
        errors=[*home_result.errors, *secondary_result.errors],
        limited=len(selected) == 5 or home_result.limited or secondary_result.limited,
    )
    return run_privacy_diagnostic(
        build_evidence(combined, additional_links=include_links)
    )
