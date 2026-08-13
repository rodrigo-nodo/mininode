"""Bounded discovery of links declared in static HTML includes."""

from __future__ import annotations

from collections.abc import Callable
from urllib.parse import urljoin, urlsplit, urlunsplit

from bs4 import BeautifulSoup

from .extractor import extract_page
from .fetcher import WebFetcher, normalize_url
from .models import LinkEvidence

MAX_INCLUDES_PER_PAGE = 5


def _same_host_http_url(value: str, base_url: str, hostname: str | None) -> str | None:
    try:
        url = normalize_url(urljoin(base_url, value))
    except (TypeError, ValueError):
        return None
    parsed = urlsplit(url)
    if parsed.scheme not in {"http", "https"} or parsed.hostname != hostname:
        return None
    return url


def _include_urls(html: str, source_url: str) -> list[str]:
    soup = BeautifulSoup(html, "lxml")
    hostname = urlsplit(source_url).hostname
    results: list[str] = []
    seen: set[str] = set()
    for node in soup.find_all(attrs={"data-include": True}):
        value = str(node.get("data-include") or "").strip()
        url = _same_host_http_url(value, source_url, hostname) if value else None
        if url is not None and url not in seen:
            seen.add(url)
            results.append(url)
            if len(results) == MAX_INCLUDES_PER_PAGE:
                break
    return results


def _fragment_links(html: str, fragment_url: str, site_url: str) -> list[LinkEvidence]:
    """Extract normal hrefs and root-based, same-host anchor data-rel values."""

    soup = BeautifulSoup(html, "lxml")
    for removable in soup.find_all(["script", "style", "template"]):
        removable.decompose()

    # Mininode's include.js prefixes data-rel with the path back to the public
    # root. Reproduce that declarative URL result without executing the script.
    site_parts = urlsplit(site_url)
    site_root = urlunsplit((site_parts.scheme, site_parts.netloc, "/", "", ""))
    hostname = site_parts.hostname
    results: list[LinkEvidence] = []
    seen: set[str] = set()
    for anchor in soup.find_all("a"):
        data_rel = str(anchor.get("data-rel") or "").strip()
        if data_rel:
            url = _same_host_http_url(data_rel, site_root, hostname)
            if url is None:
                continue
            text = " ".join(anchor.get_text(" ", strip=True).split())
            if url not in seen:
                seen.add(url)
                results.append(LinkEvidence(url, text, fragment_url))
            continue

        # Keep the established href extraction behavior for ordinary anchors.
        wrapper = BeautifulSoup(str(anchor), "lxml")
        for link in extract_page(str(wrapper), fragment_url).links:
            if urlsplit(link.url).hostname == hostname and link.url not in seen:
                seen.add(link.url)
                results.append(link)
    return results


def discover_include_links(
    home_html: str,
    home_url: str,
    fetcher_factory: Callable[[float], WebFetcher] | None = None,
    remaining_budget: Callable[[], float] | None = None,
    *,
    fetcher: WebFetcher | None = None,
    deadline: float | None = None,
) -> list[LinkEvidence]:
    """Fetch depth-one include resources and return only discovered links.

    Auxiliary fetch failures are intentionally omitted. Fragment bodies and
    fetch results remain local to this call and never enter page evidence.
    """

    include_urls = _include_urls(home_html, home_url)
    if not include_urls:
        return []
    if fetcher is not None:
        if deadline is None:
            fetched = fetcher.fetch(home_url, include_urls)
        else:
            fetched = fetcher.fetch(home_url, include_urls, deadline=deadline)
    else:
        if fetcher_factory is None or remaining_budget is None:
            raise TypeError("fetcher_factory and remaining_budget are required without fetcher")
        budget = remaining_budget()
        if budget <= 0:
            return []
        with fetcher_factory(budget) as owned_fetcher:
            if deadline is None:
                fetched = owned_fetcher.fetch(home_url, include_urls)
            else:
                fetched = owned_fetcher.fetch(home_url, include_urls, deadline=deadline)
    links: list[LinkEvidence] = []
    seen: set[str] = set()
    for fragment in fetched.pages:
        if fragment.error or fragment.html is None or fragment.final_url is None:
            continue
        for link in _fragment_links(fragment.html, fragment.final_url, home_url):
            if link.url not in seen:
                seen.add(link.url)
                links.append(link)
    return links
