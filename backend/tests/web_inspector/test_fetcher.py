from __future__ import annotations

import httpx

from mininode_api.web_inspector.fetcher import MAX_RESPONSE_BYTES, USER_AGENT, WebFetcher, normalize_url


def public_resolver(hostname: str, port: int) -> set[str]:
    return {"93.184.216.34"}


def client_for(handler) -> httpx.Client:
    return httpx.Client(transport=httpx.MockTransport(handler), follow_redirects=False)


def test_normalization_removes_fragment_tracking_and_default_port():
    assert normalize_url("HTTPS://EXAMPLE.COM:443/path?utm_source=x&id=7#top") == "https://example.com/path?id=7"


def test_caps_at_five_and_deduplicates_urls():
    requested = []

    def handler(request):
        requested.append(str(request.url))
        if request.url.path == "/robots.txt":
            return httpx.Response(404, headers={"content-type": "text/plain"})
        return httpx.Response(200, text="<html></html>", headers={"content-type": "text/html"})

    urls = ["https://example.com/", "https://example.com/#copy", "https://example.com/a", "https://example.com/b", "https://example.com/c", "https://example.com/d"]
    result = WebFetcher(client=client_for(handler), resolver=public_resolver).fetch(urls[0], urls)

    assert result.limited is True
    assert result.pages_requested == 4
    assert result.pages_fetched == 4
    assert requested == ["https://example.com/robots.txt", "https://example.com/", "https://example.com/a", "https://example.com/b", "https://example.com/c"]


def test_rejects_external_hostname_and_subdomain_without_requesting_them():
    paths = []

    def handler(request):
        paths.append(str(request.url))
        return httpx.Response(404, headers={"content-type": "text/plain"})

    result = WebFetcher(client=client_for(handler), resolver=public_resolver).fetch(
        "https://example.com", ["https://other.example/a", "https://blog.example.com/b"]
    )
    assert [page.error.code for page in result.pages] == ["hostname_mismatch", "hostname_mismatch"]
    assert paths == ["https://example.com/robots.txt"]


def test_timeout_is_controlled_and_secondary_error_does_not_abort():
    def handler(request):
        if request.url.path == "/robots.txt":
            return httpx.Response(404, headers={"content-type": "text/plain"})
        if request.url.path == "/slow":
            raise httpx.ReadTimeout("slow", request=request)
        return httpx.Response(200, text="ok", headers={"content-type": "text/html"})

    result = WebFetcher(client=client_for(handler), resolver=public_resolver).fetch(
        "https://example.com", ["https://example.com/slow", "https://example.com/ok"]
    )
    assert result.pages[0].error.code == "timeout"
    assert result.pages[1].html == "ok"
    assert result.pages_fetched == 1


def test_rejects_non_html_and_oversized_responses():
    def handler(request):
        if request.url.path == "/robots.txt":
            return httpx.Response(404, headers={"content-type": "text/plain"})
        if request.url.path == "/document":
            return httpx.Response(200, content=b"pdf", headers={"content-type": "application/pdf"})
        return httpx.Response(200, headers={"content-type": "text/html", "content-length": str(MAX_RESPONSE_BYTES + 1)})

    result = WebFetcher(client=client_for(handler), resolver=public_resolver).fetch(
        "https://example.com", ["https://example.com/document", "https://example.com/huge"]
    )
    assert [page.error.code for page in result.pages] == ["unsupported_content_type", "response_too_large"]


def test_rejects_stream_that_exceeds_limit_without_content_length():
    huge = b"x" * (MAX_RESPONSE_BYTES + 1)

    def handler(request):
        if request.url.path == "/robots.txt":
            return httpx.Response(404, headers={"content-type": "text/plain"})
        return httpx.Response(200, content=huge, headers={"content-type": "text/html"})

    result = WebFetcher(client=client_for(handler), resolver=public_resolver).fetch("https://example.com", ["https://example.com/huge"])
    assert result.pages[0].error.code == "response_too_large"


def test_sets_declared_user_agent_and_fetches_sequentially():
    order = []

    def handler(request):
        order.append((request.url.path, request.headers["user-agent"]))
        content_type = "text/plain" if request.url.path == "/robots.txt" else "text/html"
        status = 404 if request.url.path == "/robots.txt" else 200
        return httpx.Response(status, text="", headers={"content-type": content_type})

    WebFetcher(client=client_for(handler), resolver=public_resolver).fetch(
        "https://example.com", ["https://example.com/one", "https://example.com/two"]
    )
    assert order == [("/robots.txt", USER_AGENT), ("/one", USER_AGENT), ("/two", USER_AGENT)]


def test_stops_after_five_redirects():
    def handler(request):
        if request.url.path == "/robots.txt":
            return httpx.Response(404, headers={"content-type": "text/plain"})
        number = int(request.url.path.removeprefix("/r"))
        return httpx.Response(302, headers={"location": f"/r{number + 1}"})

    result = WebFetcher(client=client_for(handler), resolver=public_resolver).fetch("https://example.com", ["https://example.com/r0"])
    assert result.pages[0].error.code == "too_many_redirects"
    assert result.pages[0].redirect_count == 5


def test_revalidates_and_rejects_public_to_private_redirect():
    calls = []

    def resolver(hostname, port):
        calls.append(hostname)
        return {"93.184.216.34"}

    def handler(request):
        if request.url.path == "/robots.txt":
            return httpx.Response(404, headers={"content-type": "text/plain"})
        return httpx.Response(302, headers={"location": "http://127.0.0.1/admin"})

    result = WebFetcher(client=client_for(handler), resolver=resolver).fetch("https://example.com", ["https://example.com/start"])
    assert result.pages[0].error.code == "blocked_by_ssrf"
    assert result.pages[0].redirect_count == 1
    assert calls.count("example.com") >= 3
