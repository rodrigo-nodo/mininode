"""Sequential, bounded HTTP fetcher for already-selected public pages."""

from __future__ import annotations

import ipaddress
import time
from collections.abc import Iterable
from urllib.parse import parse_qsl, urlencode, urljoin, urlsplit, urlunsplit
from urllib.robotparser import RobotFileParser

import httpx

from .models import FetchError, FetchPageResult, InspectionFetchResult
from .ssrf import (
    DNSResolutionError,
    Resolver,
    SSRFGuardError,
    UnsafeTargetError,
    system_resolver,
    validate_url,
)
from .transport import PinnedHTTPTransport, VALIDATED_IP_EXTENSION

USER_AGENT = "Mininode-Web-Inspector/0.1"
ROBOTS_USER_AGENT = "Mininode-Web-Inspector"
MAX_URLS = 5
MAX_REDIRECTS = 5
MAX_RESPONSE_BYTES = 2 * 1024 * 1024
REQUEST_TIMEOUT_SECONDS = 10.0
INSPECTION_BUDGET_SECONDS = 30.0
HTML_CONTENT_TYPES = {"text/html", "application/xhtml+xml"}
REDIRECT_STATUSES = {301, 302, 303, 307, 308}


def same_site_hostname(a: str | None, b: str | None) -> bool:
    """Return whether two hostnames differ only by one leading ``www.``."""

    def normalize(hostname: str | None) -> str | None:
        if not hostname:
            return None
        normalized = hostname.rstrip(".").lower()
        return normalized or None

    normalized_a = normalize(a)
    normalized_b = normalize(b)
    if normalized_a is None or normalized_b is None:
        return False
    if normalized_a == normalized_b:
        return True
    try:
        ipaddress.ip_address(normalized_a)
    except ValueError:
        pass
    else:
        return False
    try:
        ipaddress.ip_address(normalized_b)
    except ValueError:
        pass
    else:
        return False
    return normalized_a.removeprefix("www.") == normalized_b.removeprefix("www.")


def normalize_url(url: str) -> str:
    """Canonicalize an HTTP URL and remove common campaign parameters."""

    parsed = urlsplit(url)
    scheme = parsed.scheme.lower()
    hostname = (parsed.hostname or "").rstrip(".").lower()
    if ":" in hostname and not hostname.startswith("["):
        hostname = f"[{hostname}]"
    port = parsed.port
    default_port = (scheme == "http" and port == 80) or (scheme == "https" and port == 443)
    netloc = hostname if port is None or default_port else f"{hostname}:{port}"
    path = parsed.path or "/"
    query = urlencode(
        [(key, value) for key, value in parse_qsl(parsed.query, keep_blank_values=True) if not key.lower().startswith("utm_")],
        doseq=True,
    )
    return urlunsplit((scheme, netloc, path, query, ""))


class WebFetcher:
    """Fetch at most five same-host HTML pages without crawling."""

    def __init__(
        self,
        *,
        client: httpx.Client | None = None,
        resolver: Resolver = system_resolver,
        inspection_budget: float = INSPECTION_BUDGET_SECONDS,
    ) -> None:
        self._client = client or httpx.Client(
            transport=PinnedHTTPTransport(),
            follow_redirects=False,
            timeout=REQUEST_TIMEOUT_SECONDS,
            headers={"User-Agent": USER_AGENT},
        )
        self._owns_client = client is None
        self._resolver = resolver
        self._inspection_budget = inspection_budget

    def close(self) -> None:
        if self._owns_client:
            self._client.close()

    def __enter__(self) -> WebFetcher:
        return self

    def __exit__(self, *args: object) -> None:
        self.close()

    def fetch(self, target_url: str, candidate_urls: Iterable[str]) -> InspectionFetchResult:
        candidates = list(candidate_urls)
        limited = len(candidates) > MAX_URLS
        candidates = candidates[:MAX_URLS]
        normalized: list[str] = []
        seen: set[str] = set()
        for candidate in candidates:
            try:
                value = normalize_url(candidate)
            except ValueError:
                value = candidate
            if value not in seen:
                normalized.append(value)
                seen.add(value)

        try:
            normalized_target = normalize_url(target_url)
            allowed_hostname = urlsplit(normalized_target).hostname
            validate_url(normalized_target, self._resolver)
        except SSRFGuardError as exc:
            error = self._guard_error(target_url, exc)
            page = FetchPageResult(requested_url=target_url, error=error)
            return InspectionFetchResult(target_url, len(normalized), pages=[page], errors=[error], limited=limited)

        result = InspectionFetchResult(normalized_target, len(normalized), limited=limited)
        started = time.monotonic()
        robots = self._load_robots(normalized_target, allowed_hostname)
        for requested_url in normalized:
            if time.monotonic() - started >= self._inspection_budget:
                error = FetchError("timeout", "Inspection time budget exceeded", requested_url)
                page = FetchPageResult(requested_url=requested_url, error=error)
            elif not same_site_hostname(urlsplit(requested_url).hostname, allowed_hostname):
                error = FetchError("hostname_mismatch", "URL is outside the initial hostname", requested_url)
                page = FetchPageResult(requested_url=requested_url, error=error)
            elif robots is not None and not robots.can_fetch(ROBOTS_USER_AGENT, requested_url):
                error = FetchError("robots_disallowed", "robots.txt disallows this path", requested_url)
                page = FetchPageResult(requested_url=requested_url, error=error)
            else:
                page = self._fetch_page(requested_url, allowed_hostname)
            result.pages.append(page)
            if page.error:
                result.errors.append(page.error)
            else:
                result.pages_fetched += 1
        return result

    def _load_robots(self, target_url: str, allowed_hostname: str | None) -> RobotFileParser | None:
        robots_url = urlunsplit((*urlsplit(target_url)[:2], "/robots.txt", "", ""))
        page = self._fetch_page(robots_url, allowed_hostname, accept_plain_text=True)
        if page.error or page.status_code != 200 or page.html is None:
            return None
        parser = RobotFileParser()
        parser.set_url(robots_url)
        parser.parse(page.html.splitlines())
        return parser

    def _fetch_page(
        self,
        requested_url: str,
        allowed_hostname: str | None,
        *,
        accept_plain_text: bool = False,
    ) -> FetchPageResult:
        started = time.monotonic()
        current_url = requested_url
        redirects = 0
        cookie_names: list[str] = []
        while True:
            try:
                validated_addresses = validate_url(current_url, self._resolver)
                if not same_site_hostname(urlsplit(current_url).hostname, allowed_hostname):
                    raise UnsafeTargetError("Redirect leaves the initial hostname")
                # A deterministic member of the fully validated DNS answer set is
                # passed to the transport. The production transport connects to
                # this address directly and never resolves the hostname again.
                pinned_ip = sorted(validated_addresses)[0]
                with self._client.stream(
                    "GET",
                    current_url,
                    headers={"User-Agent": USER_AGENT},
                    follow_redirects=False,
                    timeout=REQUEST_TIMEOUT_SECONDS,
                    extensions={VALIDATED_IP_EXTENSION: pinned_ip},
                ) as response:
                    for header in response.headers.get_list("set-cookie"):
                        name, separator, _ = header.partition("=")
                        name = name.strip()
                        if separator and name and name not in cookie_names:
                            cookie_names.append(name)
                    if response.status_code in REDIRECT_STATUSES and response.headers.get("location"):
                        if redirects >= MAX_REDIRECTS:
                            return self._error_page(requested_url, current_url, response.status_code, redirects, started, "too_many_redirects", "Maximum redirect count exceeded")
                        current_url = normalize_url(urljoin(current_url, response.headers["location"]))
                        redirects += 1
                        continue
                    content_type = response.headers.get("content-type", "").split(";", 1)[0].strip().lower()
                    accepted = content_type in HTML_CONTENT_TYPES or (accept_plain_text and content_type == "text/plain")
                    if not accepted:
                        return self._error_page(requested_url, current_url, response.status_code, redirects, started, "unsupported_content_type", f"Unsupported content type: {content_type or 'missing'}", content_type)
                    try:
                        content_length = int(response.headers.get("content-length", "0"))
                    except ValueError:
                        content_length = 0
                    if content_length > MAX_RESPONSE_BYTES:
                        return self._error_page(requested_url, current_url, response.status_code, redirects, started, "response_too_large", "Response exceeds 2 MB", content_type)
                    body = bytearray()
                    for chunk in response.iter_bytes():
                        if len(body) + len(chunk) > MAX_RESPONSE_BYTES:
                            return self._error_page(requested_url, current_url, response.status_code, redirects, started, "response_too_large", "Response exceeds 2 MB", content_type)
                        body.extend(chunk)
                    if response.status_code >= 400:
                        return self._error_page(requested_url, current_url, response.status_code, redirects, started, "http_error", f"HTTP status {response.status_code}", content_type)
                    encoding = response.encoding or "utf-8"
                    return FetchPageResult(
                        requested_url=requested_url,
                        final_url=current_url,
                        status_code=response.status_code,
                        content_type=content_type,
                        html=bytes(body).decode(encoding, errors="replace"),
                        elapsed_ms=int((time.monotonic() - started) * 1000),
                        redirect_count=redirects,
                        set_cookie_names=cookie_names,
                        tls_valid=True if urlsplit(current_url).scheme == "https" else None,
                    )
            except httpx.TimeoutException:
                return self._error_page(requested_url, current_url, None, redirects, started, "timeout", "Request timed out")
            except DNSResolutionError as exc:
                return self._error_page(requested_url, current_url, None, redirects, started, "dns_failure", str(exc))
            except SSRFGuardError as exc:
                error = self._guard_error(current_url, exc)
                return FetchPageResult(requested_url, current_url, elapsed_ms=int((time.monotonic() - started) * 1000), redirect_count=redirects, error=error)
            except httpx.HTTPError as exc:
                return self._error_page(requested_url, current_url, None, redirects, started, "http_error", str(exc))

    @staticmethod
    def _guard_error(url: str, exc: SSRFGuardError) -> FetchError:
        return FetchError("blocked_by_ssrf", str(exc), url)

    @staticmethod
    def _error_page(requested_url: str, final_url: str, status_code: int | None, redirects: int, started: float, code: str, message: str, content_type: str | None = None) -> FetchPageResult:
        return FetchPageResult(
            requested_url=requested_url,
            final_url=final_url,
            status_code=status_code,
            content_type=content_type,
            elapsed_ms=int((time.monotonic() - started) * 1000),
            redirect_count=redirects,
            error=FetchError(code, message, final_url),
        )
