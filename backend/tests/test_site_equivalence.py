"""Contract: only demonstrated apex/www redirect equivalence is accepted."""
from types import SimpleNamespace

import httpx
import pytest

from mininode_api.services.site_equivalence import inspect_www_equivalence
from mininode_api.web_inspector.fetcher import WebFetcher
from mininode_api.web_inspector.transport import VALIDATED_IP_EXTENSION


class FakeFetcher:
    def __init__(self, pages):
        self.pages = pages
        self.calls = []

    def _fetch_page(self, url, hostname, *, deadline=None):
        self.calls.append((url, hostname))
        return self.pages[url]


def page(host, redirects=0, *, error=None, status=200, scheme="https"):
    return SimpleNamespace(error=error, status_code=status,
                           final_url=f"{scheme}://{host}/", redirect_count=redirects)


@pytest.mark.parametrize("pages, expected", [
    ({"https://example.com/": page("www.example.com", 1),
      "https://www.example.com/": page("www.example.com")}, True),
    ({"https://example.com/": page("example.com"),
      "https://www.example.com/": page("www.example.com")}, False),
    ({"https://example.com/": page("example.com"),
      "https://www.example.com/": page("example.com", 1)}, True),
    ({"https://example.com/": page("www.example.com", 1),
      "https://www.example.com/": page("example.com", 1)}, False),
    ({"https://example.com/": page("www.example.com", 1),
      "https://www.example.com/": page("www.example.com", error=Exception())}, False),
    ({"https://example.com/": page("www.example.com", 1),
      "https://www.example.com/": page("www.example.com", status=403)}, False),
    ({"https://example.com/": page("www.example.com", 1),
      "https://www.example.com/": page("www.example.com", scheme="http")}, False),
])
def test_www_proof_requires_successful_convergence_and_redirect(pages, expected):
    fetcher = FakeFetcher(pages)
    result = inspect_www_equivalence("https://example.com/", fetcher=fetcher)
    assert result.equivalent is expected
    assert len(fetcher.calls) == 2
    assert all(hostname == "example.com" for _, hostname in fetcher.calls)


def test_www_subdomains_not_merged_by_inference():
    fetcher = FakeFetcher({})
    result = inspect_www_equivalence("shop.example.com", fetcher=fetcher)
    assert not result.equivalent
    assert fetcher.calls == []


@pytest.mark.parametrize("url", ["localhost", "http://127.0.0.1", "http://admin:pass@example.com", "file:///etc/hosts"])
def test_unsafe_input_rejected_without_fetch(url):
    with pytest.raises(ValueError):
        inspect_www_equivalence(url, fetcher=FakeFetcher({}))


# B1 independent review: exercise the real WebFetcher, not FakeFetcher.
# MockTransport and the explicit resolver keep every request offline while
# retaining the production DNS/SSRF checks, redirect policy and pinned-IP path.


def real_fetcher(handler, resolver):
    client = httpx.Client(transport=httpx.MockTransport(handler), follow_redirects=False)
    return WebFetcher(client=client, resolver=resolver)


@pytest.mark.parametrize("source_host,target_host", [
    ("example.com", "www.example.com"),
    ("www.example.com", "example.com"),
])
@pytest.mark.parametrize("requested_host", ["example.com", "www.example.com"])
def test_real_fetcher_verifies_apex_www_redirect_in_both_directions(
    source_host, target_host, requested_host,
):
    addresses = {"example.com": "93.184.216.34", "www.example.com": "93.184.216.35"}
    requests = []
    resolutions = []

    def resolver(hostname, port):
        resolutions.append((hostname, port))
        return {addresses[hostname]}

    def handler(request):
        requests.append((
            request.url.host,
            request.extensions[VALIDATED_IP_EXTENSION],
            request.url.path,
        ))
        if request.url.host == source_host:
            return httpx.Response(
                301, headers={"location": f"https://{target_host}/"}
            )
        return httpx.Response(
            200, text="<html>Public homepage</html>",
            headers={"content-type": "text/html"},
        )

    with real_fetcher(handler, resolver) as inspector:
        result = inspect_www_equivalence(f"https://{requested_host}/", fetcher=inspector)

    assert result.equivalent is True
    assert result.reason == "stable_www_redirect"
    assert (result.requested_hostname, result.counterpart_hostname) == (
        requested_host,
        "www.example.com" if requested_host == "example.com" else "example.com",
    )
    # Both HOME pages are independently fetched, and the redirect is followed.
    assert [host for host, _, _ in requests] == [
        requested_host, target_host,
        "www.example.com" if requested_host == "example.com" else "example.com",
    ] if requested_host == source_host else [
        requested_host,
        "example.com" if requested_host == "www.example.com" else "www.example.com",
        target_host,
    ]
    assert all(ip == addresses[host] for host, ip, _ in requests)
    assert len(resolutions) == 3
    assert all(port == 443 for _, port in resolutions)


@pytest.mark.parametrize("location", [
    "https://shop.example.com/",
    "https://outside.example.net/",
    "http://www.example.com/",
])
def test_real_fetcher_rejects_untrusted_or_insecure_redirects(location):
    requests = []

    def handler(request):
        requests.append(request.url.host)
        if request.url.host == "example.com":
            return httpx.Response(302, headers={"location": location})
        return httpx.Response(200, text="<html>Same</html>",
                              headers={"content-type": "text/html"})

    def resolver(hostname, port):
        return {"93.184.216.34"}

    with real_fetcher(handler, resolver) as inspector:
        result = inspect_www_equivalence("https://example.com/", fetcher=inspector)

    assert result.equivalent is False
    assert result.reason == "insufficient_redirect_evidence"
    if location.startswith("https://"):
        assert requests == ["example.com", "www.example.com"]
    else:
        # HTTPS downgrade never constitutes equivalence even if HOME responds.
        assert requests == ["example.com", "www.example.com", "www.example.com"]


@pytest.mark.parametrize("redirect_target", [
    "https://www.example.com/",
    "https://127.0.0.1/",
])
def test_real_fetcher_rejects_ssrf_before_destination_http_request(redirect_target):
    requests = []
    resolutions = []

    def resolver(hostname, port):
        resolutions.append((hostname, port))
        if hostname == "www.example.com":
            return {"192.168.1.5"}
        return {"93.184.216.34"}

    def handler(request):
        requests.append(request.url.host)
        return httpx.Response(301, headers={"location": redirect_target})

    with real_fetcher(handler, resolver) as inspector:
        result = inspect_www_equivalence("https://example.com/", fetcher=inspector)

    assert result.equivalent is False
    assert result.reason == "insufficient_redirect_evidence"
    assert requests == ["example.com"]
    assert ("example.com", 443) in resolutions
