import json

import httpx

from mininode_api.web_inspector.extractor import build_evidence
from mininode_api.web_inspector.fetcher import WebFetcher
from mininode_api.web_inspector.models import FetchPageResult, InspectionFetchResult


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
    assert payload["transport"] == {"https": True, "tls_valid": True, "http_redirects_to_https": True, "mixed_content": False}
    assert payload["links"][0]["source_url"] == "https://example.com/"
    assert payload["forms"][0]["source_url"] == "https://example.com/contacto"
    assert payload["cookies"]["set_cookie_names"] == ["session"]
    assert payload["contacts"][0]["email"] == "a@example.com"
    assert "<html" not in encoded.lower()
    for forbidden in ("PRV-", "Privacy Score", "cumplimiento legal"):
        assert forbidden not in encoded
