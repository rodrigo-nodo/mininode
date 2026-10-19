"""Passive, SSRF-guarded evidence for apex/www redirects.

Detection is advisory. It does not mutate Access or grant entitlements.
"""
from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlsplit

from mininode_api.services.access import normalize_site_url
from mininode_api.web_inspector.fetcher import WebFetcher


@dataclass(frozen=True)
class WWWEquivalence:
    requested_hostname: str
    counterpart_hostname: str
    equivalent: bool
    reason: str


def inspect_www_equivalence(url: str, *, fetcher: WebFetcher | None = None) -> WWWEquivalence:
    """Require both public HTTPS homepages to converge by actual redirect.

    Reuses pinned-IP SSRF guard, redirect budget and timeout from WebFetcher.
    Neither matching page content nor DNS equality counts as equivalence.
    """
    hostname, _ = normalize_site_url(url)
    apex = hostname.removeprefix("www.")
    counterpart = apex if hostname.startswith("www.") else f"www.{hostname}"
    # www under an already nested subdomain must not infer an independent app.
    if hostname.startswith("www.www.") or apex.count(".") != 1:
        return WWWEquivalence(hostname, counterpart, False, "subdomain_not_supported")
    target = f"https://{hostname}/"
    alternate = f"https://{counterpart}/"

    def probe(inspector: WebFetcher, page_url: str):
        page = inspector._fetch_page(page_url, hostname, deadline=None)
        if page.error or page.status_code != 200 or not page.final_url:
            return None
        final = urlsplit(page.final_url)
        if final.scheme != "https" or final.hostname not in {hostname, counterpart}:
            return None
        return final.hostname, page.redirect_count

    if fetcher is None:
        with WebFetcher() as inspector:
            first, second = probe(inspector, target), probe(inspector, alternate)
    else:
        first, second = probe(fetcher, target), probe(fetcher, alternate)
    verified = bool(first and second and first[0] == second[0] and
                    (first[1] > 0 or second[1] > 0))
    return WWWEquivalence(hostname, counterpart, verified,
                          "stable_www_redirect" if verified else "insufficient_redirect_evidence")
