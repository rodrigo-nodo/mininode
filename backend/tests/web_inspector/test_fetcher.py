from __future__ import annotations

import ssl

import httpx
import pytest

from mininode_api.web_inspector import fetcher as fetcher_module
from mininode_api.web_inspector.fetcher import MAX_RESPONSE_BYTES, USER_AGENT, WebFetcher, normalize_url, same_site_hostname
from mininode_api.web_inspector.transport import VALIDATED_IP_EXTENSION


def public_resolver(hostname: str, port: int) -> set[str]:
    return {"93.184.216.34"}


def client_for(handler) -> httpx.Client:
    return httpx.Client(transport=httpx.MockTransport(handler), follow_redirects=False)


def test_robots_is_cached_once_per_origin_in_a_fetcher_session():
    requested = []

    def handler(request):
        requested.append(str(request.url))
        status = 200
        content_type = "text/plain" if request.url.path == "/robots.txt" else "text/html"
        return httpx.Response(status, text="ok", headers={"content-type": content_type})

    fetcher = WebFetcher(client=client_for(handler), resolver=public_resolver)
    fetcher.fetch("https://example.com", ["https://example.com/one"])
    fetcher.fetch("https://example.com", ["https://example.com/two"])

    assert requested.count("https://example.com/robots.txt") == 1


def test_failed_robots_result_is_cached_and_origins_are_independent():
    robots = []

    def handler(request):
        if request.url.path == "/robots.txt":
            robots.append(str(request.url))
            return httpx.Response(500, headers={"content-type": "text/plain"})
        return httpx.Response(200, text="ok", headers={"content-type": "text/html"})

    fetcher = WebFetcher(client=client_for(handler), resolver=public_resolver)
    fetcher.fetch("https://example.com", ["https://example.com/one"])
    fetcher.fetch("https://example.com", ["https://example.com/two"])
    fetcher.fetch("https://other.example", ["https://other.example/one"])

    assert robots == [
        "https://example.com/robots.txt",
        "https://other.example/robots.txt",
    ]


def test_shared_deadline_does_not_reset_and_later_fetch_uses_remaining(monkeypatch):
    now = [0.0]
    observed = []
    monkeypatch.setattr(fetcher_module.time, "monotonic", lambda: now[0])

    def handler(request):
        observed.append((request.url.path, request.extensions["timeout"]["connect"]))
        if request.url.path == "/one":
            now[0] = 26.0
        status = 404 if request.url.path == "/robots.txt" else 200
        content_type = "text/plain" if request.url.path == "/robots.txt" else "text/html"
        return httpx.Response(status, text="ok", headers={"content-type": content_type})

    fetcher = WebFetcher(client=client_for(handler), resolver=public_resolver)
    fetcher.fetch("https://example.com", ["https://example.com/one"], deadline=30.0)
    fetcher.fetch("https://example.com", ["https://example.com/two"], deadline=30.0)

    assert observed[-1] == ("/two", 4.0)


def test_exhausted_shared_deadline_starts_no_new_network_request(monkeypatch):
    requested = []
    monkeypatch.setattr(fetcher_module.time, "monotonic", lambda: 30.0)
    fetcher = WebFetcher(
        client=client_for(lambda request: requested.append(request)), resolver=public_resolver
    )

    result = fetcher.fetch(
        "https://example.com", ["https://example.com/late"], deadline=30.0
    )

    assert requested == []
    assert result.pages[0].error.code == "timeout"


@pytest.mark.parametrize(
    ("pinned_ip", "expected_family"),
    [("93.184.216.34", "ipv4"), ("2606:2800:220:1:248:1893:25c8:1946", "ipv6")],
)
def test_records_pinned_network_family_without_retaining_address(pinned_ip, expected_family):
    def resolver(hostname, port):
        return {pinned_ip}

    fetcher = WebFetcher(
        client=client_for(lambda request: httpx.Response(200, text="ok", headers={"content-type": "text/html"})),
        resolver=resolver,
    )

    page = fetcher._fetch_page("https://example.com/", "example.com")

    assert page.network_family == expected_family
    assert pinned_ip not in repr(page)


@pytest.mark.parametrize("error_type", [httpx.ConnectError, httpx.ConnectTimeout])
def test_records_safe_transport_error_class(error_type):
    raw_message = "socket detail secret=private"

    def handler(request):
        raise error_type(raw_message, request=request)

    page = WebFetcher(client=client_for(handler), resolver=public_resolver)._fetch_page(
        "https://example.com/", "example.com"
    )

    assert page.network_family == "ipv4"
    assert page.transport_error_class == error_type.__name__
    assert raw_message not in page.transport_error_class


@pytest.mark.parametrize(
    ("addresses", "expected_attempts", "expected_family"),
    [
        (
            {"2606:2800:220:1:248:1893:25c8:1946", "93.184.216.34"},
            ["2606:2800:220:1:248:1893:25c8:1946", "93.184.216.34"],
            "ipv4",
        ),
        (
            {"93.184.216.34", "93.184.216.33"},
            ["93.184.216.33", "93.184.216.34"],
            "ipv4",
        ),
    ],
)
def test_retries_validated_addresses_in_sorted_order(
    addresses, expected_attempts, expected_family
):
    attempts = []

    def handler(request):
        attempts.append(request.extensions[VALIDATED_IP_EXTENSION])
        if len(attempts) == 1:
            raise httpx.ConnectError("unreachable", request=request)
        return httpx.Response(200, text="ok", headers={"content-type": "text/html"})

    page = WebFetcher(
        client=client_for(handler), resolver=lambda hostname, port: addresses
    )._fetch_page("https://example.com/", "example.com")

    assert page.html == "ok"
    assert page.network_family == expected_family
    assert attempts == expected_attempts


def test_returns_last_connection_failure_after_each_validated_address_once():
    attempts = []

    def handler(request):
        attempts.append(request.extensions[VALIDATED_IP_EXTENSION])
        raise httpx.ConnectError("unreachable", request=request)

    page = WebFetcher(
        client=client_for(handler),
        resolver=lambda hostname, port: {"93.184.216.34", "93.184.216.33"},
    )._fetch_page("https://example.com/", "example.com")

    assert page.error.code == "http_error"
    assert page.network_family == "ipv4"
    assert page.transport_error_class == "ConnectError"
    assert attempts == ["93.184.216.33", "93.184.216.34"]


@pytest.mark.parametrize("status_code", [403, 500])
def test_does_not_try_another_address_after_http_response(status_code):
    attempts = []

    def handler(request):
        attempts.append(request.extensions[VALIDATED_IP_EXTENSION])
        return httpx.Response(
            status_code, text="error", headers={"content-type": "text/html"}
        )

    page = WebFetcher(
        client=client_for(handler),
        resolver=lambda hostname, port: {"93.184.216.34", "93.184.216.33"},
    )._fetch_page("https://example.com/", "example.com")

    assert page.status_code == status_code
    assert page.error.code == "http_error"
    assert attempts == ["93.184.216.33"]


def test_mixed_dns_is_blocked_before_any_address_attempt():
    attempts = []
    page = WebFetcher(
        client=client_for(lambda request: attempts.append(request)),
        resolver=lambda hostname, port: {"93.184.216.34", "127.0.0.1"},
    )._fetch_page("https://example.com/", "example.com")

    assert page.error.code == "blocked_by_ssrf"
    assert attempts == []


def test_connect_timeout_falls_back_while_budget_remains():
    attempts = []

    def handler(request):
        attempts.append(request.extensions[VALIDATED_IP_EXTENSION])
        if len(attempts) == 1:
            raise httpx.ConnectTimeout("timed out", request=request)
        return httpx.Response(200, text="ok", headers={"content-type": "text/html"})

    page = WebFetcher(
        client=client_for(handler),
        resolver=lambda hostname, port: {"93.184.216.34", "93.184.216.33"},
    )._fetch_page("https://example.com/", "example.com")

    assert page.html == "ok"
    assert attempts == ["93.184.216.33", "93.184.216.34"]


def test_does_not_start_fallback_after_inspection_budget_expires(monkeypatch):
    now = [0.0]
    attempts = []
    monkeypatch.setattr(fetcher_module.time, "monotonic", lambda: now[0])

    def handler(request):
        attempts.append(request.extensions[VALIDATED_IP_EXTENSION])
        now[0] = 31.0
        raise httpx.ConnectError("unreachable", request=request)

    page = WebFetcher(
        client=client_for(handler),
        resolver=lambda hostname, port: {"93.184.216.34", "93.184.216.33"},
        inspection_budget=30.0,
    )._fetch_page("https://example.com/", "example.com")

    assert page.error.code == "timeout"
    assert page.transport_error_class == "ConnectError"
    assert attempts == ["93.184.216.33"]


def test_second_attempt_uses_only_remaining_inspection_budget(monkeypatch):
    now = [0.0]
    timeouts = []
    monkeypatch.setattr(fetcher_module.time, "monotonic", lambda: now[0])

    def handler(request):
        timeouts.append(request.extensions["timeout"]["connect"])
        if len(timeouts) == 1:
            now[0] = 25.0
            raise httpx.ConnectError("unreachable", request=request)
        return httpx.Response(200, text="ok", headers={"content-type": "text/html"})

    page = WebFetcher(
        client=client_for(handler),
        resolver=lambda hostname, port: {"93.184.216.34", "93.184.216.33"},
        inspection_budget=30.0,
    )._fetch_page("https://example.com/", "example.com")

    assert page.html == "ok"
    assert timeouts == [10.0, 5.0]
    assert timeouts[1] <= 30.0 - now[0]


def test_certificate_connect_error_does_not_fall_back():
    attempts = []

    def handler(request):
        attempts.append(request.extensions[VALIDATED_IP_EXTENSION])
        certificate_error = ssl.SSLCertVerificationError("hostname mismatch")
        raise httpx.ConnectError("TLS failed", request=request) from certificate_error

    page = WebFetcher(
        client=client_for(handler),
        resolver=lambda hostname, port: {"93.184.216.34", "93.184.216.33"},
    )._fetch_page("https://example.com/", "example.com")

    assert page.error.code == "http_error"
    assert page.transport_error_class == "ConnectError"
    assert attempts == ["93.184.216.33"]


@pytest.mark.parametrize(
    ("error_type", "expected_code"),
    [(httpx.ReadTimeout, "timeout"), (httpx.ReadError, "http_error")],
)
def test_post_connection_read_error_does_not_fall_back(error_type, expected_code):
    attempts = []

    def handler(request):
        attempts.append(request.extensions[VALIDATED_IP_EXTENSION])
        raise error_type("read failed", request=request)

    page = WebFetcher(
        client=client_for(handler),
        resolver=lambda hostname, port: {"93.184.216.34", "93.184.216.33"},
    )._fetch_page("https://example.com/", "example.com")

    assert page.error.code == expected_code
    assert page.transport_error_class == error_type.__name__
    assert attempts == ["93.184.216.33"]


def test_each_fallback_attempt_preserves_hostname_host_header_and_pin():
    observed = []

    def handler(request):
        observed.append(
            (
                str(request.url),
                request.headers["host"],
                request.extensions[VALIDATED_IP_EXTENSION],
            )
        )
        if len(observed) == 1:
            raise httpx.ConnectError("unreachable", request=request)
        return httpx.Response(200, text="ok", headers={"content-type": "text/html"})

    page = WebFetcher(
        client=client_for(handler),
        resolver=lambda hostname, port: {"93.184.216.34", "93.184.216.33"},
    )._fetch_page("https://example.com/path", "example.com")

    assert page.html == "ok"
    assert observed == [
        ("https://example.com/path", "example.com", "93.184.216.33"),
        ("https://example.com/path", "example.com", "93.184.216.34"),
    ]


def test_redirect_fallback_uses_only_new_host_validated_addresses():
    observed = []

    def resolver(hostname, port):
        if hostname == "www.example.com":
            return {"93.184.216.36", "93.184.216.35"}
        return {"93.184.216.34", "93.184.216.33"}

    def handler(request):
        pin = request.extensions[VALIDATED_IP_EXTENSION]
        observed.append((request.url.host, pin))
        if request.url.host == "example.com":
            return httpx.Response(
                302, headers={"location": "https://www.example.com/final"}
            )
        if pin == "93.184.216.35":
            raise httpx.ConnectError("unreachable", request=request)
        return httpx.Response(200, text="ok", headers={"content-type": "text/html"})

    page = WebFetcher(client=client_for(handler), resolver=resolver)._fetch_page(
        "https://example.com/start", "example.com"
    )

    assert page.html == "ok"
    assert observed == [
        ("example.com", "93.184.216.33"),
        ("www.example.com", "93.184.216.35"),
        ("www.example.com", "93.184.216.36"),
    ]
def test_normalization_removes_fragment_tracking_and_default_port():
    assert normalize_url("HTTPS://EXAMPLE.COM:443/path?utm_source=x&id=7#top") == "https://example.com/path?id=7"


@pytest.mark.parametrize(
    ("a", "b", "expected"),
    [
        ("example.com", "example.com", True),
        ("example.com", "www.example.com", True),
        ("www.example.com", "example.com", True),
        ("www.example.com", "www.example.com", True),
        ("example.com", "www.blog.example.com", False),
        ("www.example.com", "www.www.example.com", False),
        ("foo.example.com", "bar.example.com", False),
        ("foo.example.com", "www.bar.example.com", False),
        ("127.0.0.1", "www.127.0.0.1", False),
        ("www.127.0.0.1", "127.0.0.1", False),
        (None, None, False),
        (None, "example.com", False),
        ("example.com", None, False),
        ("", "", False),
        ("", "example.com", False),
        (".", ".", False),
        ("WWW.EXAMPLE.COM.", "example.com.", True),
        ("EXAMPLE.COM.", "www.example.com", True),
    ],
)
def test_same_site_hostname_defensive_boundaries(a, b, expected):
    assert same_site_hostname(a, b) is expected


def test_same_site_hostname_documents_literal_rule_for_initial_subdomain():
    # Current behavior is deliberately literal: an initial subdomain and its
    # one leading www variant are equivalent, without trusting sibling hosts.
    assert same_site_hostname("foo.example.com", "www.foo.example.com")


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


def test_rejects_non_www_subdomains_and_external_redirects():
    destinations = ["blog.example.com", "api.example.com", "login.example.com", "evil.com"]

    for destination in destinations:
        requested_hosts = []

        def handler(request):
            requested_hosts.append(request.url.host)
            if request.url.path == "/robots.txt":
                return httpx.Response(404, headers={"content-type": "text/plain"})
            return httpx.Response(302, headers={"location": f"https://{destination}/final"})

        result = WebFetcher(client=client_for(handler), resolver=public_resolver).fetch(
            "https://example.com", ["https://example.com/start"]
        )

        assert result.pages[0].error.code == "blocked_by_ssrf"
        assert requested_hosts == ["example.com", "example.com"]

    def www_handler(request):
        if request.url.path == "/robots.txt":
            return httpx.Response(404, headers={"content-type": "text/plain"})
        return httpx.Response(302, headers={"location": "https://shop.example.com/final"})

    result = WebFetcher(client=client_for(www_handler), resolver=public_resolver).fetch(
        "https://www.example.com", ["https://www.example.com/start"]
    )
    assert result.pages[0].error.code == "blocked_by_ssrf"


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


def test_request_carries_validated_ip_and_original_host_header():
    observed = []

    def handler(request):
        observed.append(
            (
                request.url.path,
                request.extensions[VALIDATED_IP_EXTENSION],
                request.headers["host"],
            )
        )
        content_type = "text/plain" if request.url.path == "/robots.txt" else "text/html"
        status = 404 if request.url.path == "/robots.txt" else 200
        return httpx.Response(status, text="ok", headers={"content-type": content_type})

    result = WebFetcher(client=client_for(handler), resolver=public_resolver).fetch(
        "https://example.com", ["https://example.com/page"]
    )

    assert result.pages_fetched == 1
    assert observed == [
        ("/robots.txt", "93.184.216.34", "example.com"),
        ("/page", "93.184.216.34", "example.com"),
    ]


def test_redirect_revalidates_and_pins_each_destination():
    answers = iter(
        [
            {"93.184.216.30"},  # initial target validation
            {"93.184.216.31"},  # robots.txt request
            {"93.184.216.32"},  # first page request
            {"93.184.216.33"},  # redirected request
        ]
    )
    observed = []

    def resolver(hostname, port):
        return next(answers)

    def handler(request):
        observed.append((request.url.path, request.extensions[VALIDATED_IP_EXTENSION]))
        if request.url.path == "/robots.txt":
            return httpx.Response(404, headers={"content-type": "text/plain"})
        if request.url.path == "/start":
            return httpx.Response(302, headers={"location": "/final"})
        return httpx.Response(200, text="ok", headers={"content-type": "text/html"})

    result = WebFetcher(client=client_for(handler), resolver=resolver).fetch(
        "https://example.com", ["https://example.com/start"]
    )

    assert result.pages_fetched == 1
    assert observed == [
        ("/robots.txt", "93.184.216.31"),
        ("/start", "93.184.216.32"),
        ("/final", "93.184.216.33"),
    ]


def test_apex_to_www_redirect_revalidates_and_pins_effective_hostname():
    calls = []
    observed = []

    def resolver(hostname, port):
        calls.append(hostname)
        return {"93.184.216.35" if hostname == "www.example.com" else "93.184.216.34"}

    def handler(request):
        observed.append((request.url.host, request.url.path, request.extensions[VALIDATED_IP_EXTENSION], request.headers["host"]))
        if request.url.path == "/robots.txt":
            return httpx.Response(404, headers={"content-type": "text/plain"})
        if request.url.path == "/start":
            return httpx.Response(302, headers={"location": "https://www.example.com/final"})
        return httpx.Response(200, text="ok", headers={"content-type": "text/html"})

    result = WebFetcher(client=client_for(handler), resolver=resolver).fetch(
        "https://example.com/start", ["https://example.com/start"]
    )

    assert result.pages_fetched == 1
    assert result.pages[0].final_url == "https://www.example.com/final"
    assert result.pages[0].error is None
    assert calls[-1] == "www.example.com"
    assert observed[-1] == ("www.example.com", "/final", "93.184.216.35", "www.example.com")


def test_www_to_apex_redirect_succeeds_with_revalidation():
    calls = []

    def resolver(hostname, port):
        calls.append(hostname)
        return {"93.184.216.34"}

    def handler(request):
        if request.url.path == "/robots.txt":
            return httpx.Response(404, headers={"content-type": "text/plain"})
        if request.url.path == "/start":
            return httpx.Response(302, headers={"location": "https://example.com/final"})
        return httpx.Response(200, text="ok", headers={"content-type": "text/html"})

    result = WebFetcher(client=client_for(handler), resolver=resolver).fetch(
        "https://www.example.com/start", ["https://www.example.com/start"]
    )

    assert result.pages_fetched == 1
    assert result.pages[0].final_url == "https://example.com/final"
    assert result.pages[0].error is None
    assert calls[-1] == "example.com"


def test_www_redirect_to_private_or_mixed_dns_is_blocked_without_connection():
    for www_answers in ({"127.0.0.1"}, {"93.184.216.34", "127.0.0.1"}):
        requested_hosts = []

        def resolver(hostname, port):
            return www_answers if hostname == "www.example.com" else {"93.184.216.34"}

        def handler(request):
            requested_hosts.append(request.url.host)
            if request.url.path == "/robots.txt":
                return httpx.Response(404, headers={"content-type": "text/plain"})
            return httpx.Response(302, headers={"location": "https://www.example.com/final"})

        result = WebFetcher(client=client_for(handler), resolver=resolver).fetch(
            "https://example.com", ["https://example.com/start"]
        )

        assert result.pages[0].error.code == "blocked_by_ssrf"
        assert requested_hosts == ["example.com", "example.com"]


def test_www_candidate_pages_are_allowed_after_home_redirect():
    requested = []

    def handler(request):
        requested.append(str(request.url))
        if request.url.host == "example.com" and request.url.path == "/robots.txt":
            return httpx.Response(302, headers={"location": "https://www.example.com/robots.txt"})
        if request.url.host == "www.example.com" and request.url.path == "/robots.txt":
            return httpx.Response(404, headers={"content-type": "text/plain"})
        if request.url.host == "example.com" and request.url.path == "/":
            return httpx.Response(302, headers={"location": "https://www.example.com/"})
        return httpx.Response(200, text="ok", headers={"content-type": "text/html"})

    result = WebFetcher(client=client_for(handler), resolver=public_resolver).fetch(
        "https://example.com", [
            "https://example.com/",
            "https://www.example.com/privacy",
            "https://www.example.com/contact",
        ]
    )

    assert result.pages_fetched == 3
    assert not result.errors
    assert "https://www.example.com/privacy" in requested
    assert "https://www.example.com/contact" in requested


def test_preserves_deduplicated_cookie_names_across_redirects():
    def handler(request):
        if request.url.path == "/robots.txt":
            return httpx.Response(404, headers={"content-type": "text/plain"})
        if request.url.path == "/start":
            return httpx.Response(302, headers={"location": "/middle", "set-cookie": "cookie_a=secret"})
        if request.url.path == "/middle":
            return httpx.Response(301, headers={"location": "/final", "set-cookie": "cookie_b=value"})
        return httpx.Response(
            200,
            text="ok",
            headers={"content-type": "text/html", "set-cookie": "cookie_a=different"},
        )

    result = WebFetcher(client=client_for(handler), resolver=public_resolver).fetch(
        "https://example.com", ["https://example.com/start"]
    )

    assert result.pages[0].set_cookie_names == ["cookie_a", "cookie_b"]
    assert "secret" not in repr(result.pages[0].set_cookie_names)
