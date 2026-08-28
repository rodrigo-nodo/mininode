import json

import httpx

from mininode_api.web_inspector.extractor import build_evidence
from mininode_api.web_inspector.fetcher import WebFetcher
from mininode_api.web_inspector.models import FetchPageResult, InspectionFetchResult, PageEvidence


def test_fetcher_preserves_cookie_names_without_values():
    def handler(request):
        if request.url.path == "/robots.txt":
            return httpx.Response(404, headers={"content-type": "text/html"}, text="no")
        return httpx.Response(
            200,
            headers=[("content-type", "text/html"), ("set-cookie", "session=secret; Secure"), ("set-cookie", "prefs=value")],
            text="<title>Home</title>",
        )

    resolver = lambda hostname, port: ["93.184.216.34"]
    with WebFetcher(client=httpx.Client(transport=httpx.MockTransport(handler)), resolver=resolver) as fetcher:
        page = fetcher.fetch("https://example.com", ["https://example.com"]).pages[0]
    assert page.set_cookie_names == ["session", "prefs"]
    assert "secret" not in repr(page.set_cookie_names)


def test_integral_evidence_contract_is_json_compatible_and_observational():
    fetched = InspectionFetchResult(
        target_url="http://example.com/",
        pages_requested=3,
        pages_fetched=3,
        pages=[
            FetchPageResult("http://example.com/", "https://example.com/", 200, "text/html", "<title>Home</title><a href='/privacidad'>Privacidad</a><p>Usamos cookies</p>", set_cookie_names=["session"], tls_valid=True),
            FetchPageResult("https://example.com/privacidad", "https://example.com/privacidad", 200, "text/html", "<title>Privacidad</title>"),
            FetchPageResult("https://example.com/contacto", "https://example.com/contacto", 200, "text/html", "<title>Contacto</title><form><input name='email' type='email' aria-label='Email'></form><a href='mailto:a@example.com'>Mail</a>"),
        ],
    )
    contract = build_evidence(fetched)
    payload = contract.to_dict()
    encoded = json.dumps(payload)

    assert list(payload) == ["target", "inspection", "pages", "transport", "links", "forms", "cookies", "contacts"]
    assert payload["target"]["domain"] == "example.com"
    assert payload["inspection"]["pages_analyzed"] == 3
    assert payload["pages"][0]["requested_url"] == "http://example.com/"
    assert payload["pages"][0]["url"] == "https://example.com/"
    assert payload["transport"] == {"https": True, "tls_valid": True, "http_redirects_to_https": True, "mixed_content": False}
    assert payload["links"][0]["source_url"] == "https://example.com/"
    assert payload["forms"][0]["source_url"] == "https://example.com/contacto"
    assert payload["cookies"]["set_cookie_names"] == ["session"]
    assert payload["contacts"][0]["email"] == "a@example.com"
    assert "<html" not in encoded.lower()
    for forbidden in ("PRV-", "Privacy Score", "cumplimiento legal"):
        assert forbidden not in encoded
    assert "content_text" not in encoded


def test_page_evidence_content_text_is_optional_and_never_serialized():
    legacy = PageEvidence("https://example.com", 200, "Inicio", "text/html")
    fetched = InspectionFetchResult(
        target_url="https://example.com/", pages_requested=1,
        pages=[FetchPageResult(
            "https://example.com/", "https://example.com/", 200, "text/html",
            "<main>Política de privacidad con contenido documental sustantivo.</main>",
        )],
    )

    payload = build_evidence(fetched).to_dict()

    assert legacy.content_text is None
    assert "content_text" not in payload["pages"][0]


def test_page_evidence_preserves_requested_to_final_url_trace():
    requested = "https://example.com/legal/privacy/index.html"
    final = "https://example.com/legal/privacy/"
    fetched = InspectionFetchResult(
        target_url="https://example.com/",
        pages_requested=1,
        pages=[FetchPageResult(
            requested_url=requested,
            final_url=final,
            status_code=200,
            content_type="text/html",
            html="<title>Política de privacidad</title>",
        )],
    )

    page = build_evidence(fetched).pages[0]

    assert page.requested_url == requested
    assert page.url == final


def test_target_transport_uses_only_the_matching_home_result():
    home = FetchPageResult(
        "https://example.com",
        "https://example.com/",
        200,
        "text/html",
        "<title>Home</title>",
        tls_valid=True,
    )
    contact = FetchPageResult(
        "https://example.com/contacto",
        "https://example.com/contacto",
        200,
        "text/html",
        "<title>Contacto</title>",
        tls_valid=True,
    )

    payload = build_evidence(InspectionFetchResult("https://example.com/", 2, pages=[contact, home])).to_dict()

    assert payload["target"]["final_url"] == "https://example.com/"
    assert payload["transport"]["https"] is True
    assert payload["transport"]["tls_valid"] is True


def test_target_redirect_is_derived_from_its_own_result():
    home = FetchPageResult(
        "http://example.com/",
        "https://example.com/",
        200,
        "text/html",
        "<title>Home</title>",
        tls_valid=True,
    )

    payload = build_evidence(InspectionFetchResult("http://example.com/", 1, pages=[home])).to_dict()

    assert payload["target"]["final_url"] == "https://example.com/"
    assert payload["transport"]["http_redirects_to_https"] is True


def test_successful_secondary_page_does_not_replace_failed_target():
    failed_home = FetchPageResult("http://example.com/")
    contact = FetchPageResult(
        "https://example.com/contacto",
        "https://example.com/contacto",
        200,
        "text/html",
        "<title>Contacto</title>",
        tls_valid=True,
    )

    payload = build_evidence(InspectionFetchResult("http://example.com/", 2, pages=[failed_home, contact])).to_dict()

    assert payload["target"]["final_url"] is None
    assert payload["transport"]["https"] is None
    assert payload["transport"]["tls_valid"] is None
    assert payload["transport"]["http_redirects_to_https"] is None


def test_failed_https_home_has_no_final_url_from_successful_contact():
    failed_home = FetchPageResult("https://example.com/")
    contact = FetchPageResult(
        "https://example.com/contacto",
        "https://example.com/contacto",
        200,
        "text/html",
        "<title>Contacto</title>",
        tls_valid=True,
    )

    payload = build_evidence(InspectionFetchResult("https://example.com/", 2, pages=[failed_home, contact])).to_dict()

    assert payload["target"]["final_url"] is None
    assert payload["transport"]["https"] is None
