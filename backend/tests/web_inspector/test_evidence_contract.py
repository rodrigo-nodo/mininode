import json

from mininode_api.web_inspector.extractor import build_evidence
from mininode_api.web_inspector.models import FetchPageResult, InspectionFetchResult


def page(url, title, body, cookies=None):
    return FetchPageResult(
        requested_url=url,
        final_url=url,
        status_code=200,
        content_type="text/html",
        html=f"<html><title>{title}</title><body>{body}</body></html>",
        set_cookie_names=cookies or [],
    )


def test_integral_evidence_contract_is_small_generic_and_json_compatible():
    fetched = InspectionFetchResult(
        target_url="https://example.com/",
        pages_requested=3,
        pages_fetched=3,
        pages=[
            page(
                "https://example.com/",
                "Home",
                '<a href="/privacidad">Privacidad</a><a href="/contacto">Contacto</a>'
                '<div>Cookies <button>Gestionar cookies</button></div>',
                ["session"],
            ),
            page("https://example.com/privacidad", "Privacidad", "Información sobre datos personales."),
            page(
                "https://example.com/contacto",
                "Contacto",
                '<section><p>Responderemos tu consulta.</p><form action="/send">'
                '<label for="email">Correo</label><input id="email" name="email" type="email" required>'
                '<a href="/privacidad">Política de privacidad</a></form></section>'
                '<a href="mailto:hola@example.com">hola@example.com</a>',
            ),
        ],
    )

    contract = build_evidence(fetched)
    data = contract.to_dict()
    serialized = json.dumps(data, sort_keys=True, ensure_ascii=False)

    assert list(data) == ["target", "inspection", "pages", "transport", "links", "forms", "cookies", "contacts"]
    assert data["target"] == {
        "requested_url": "https://example.com/",
        "final_url": "https://example.com/",
        "domain": "example.com",
    }
    assert data["inspection"]["pages_analyzed"] == 3
    assert [item["title"] for item in data["pages"]] == ["Home", "Privacidad", "Contacto"]
    assert data["transport"] == {
        "https": True,
        "tls_valid": True,
        "http_redirects_to_https": False,
        "mixed_content": False,
    }
    assert data["cookies"] == {
        "detected": True,
        "set_cookie_names": ["session"],
        "banner_detected": True,
        "preferences_detected": True,
    }
    assert data["forms"][0]["source_url"] == "https://example.com/contacto"
    assert data["contacts"][0]["source_url"] == "https://example.com/contacto"
    assert "<html" not in serialized.lower()
    assert "prv-" not in serialized.lower()
    assert "privacy score" not in serialized.lower()
    assert "cumplimiento" not in serialized.lower()
