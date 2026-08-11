import sys
from pathlib import Path

from fastapi.testclient import TestClient

BACKEND_SRC = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(BACKEND_SRC))

from mininode_api.domain_packs.privacy.diagnostic import (  # noqa: E402
    run_privacy_diagnostic as real_privacy_diagnostic,
)
from mininode_api.main import create_app  # noqa: E402
from mininode_api.services import privacy_diagnostic as service  # noqa: E402
from mininode_api.web_inspector.models import (  # noqa: E402
    FetchError,
    FetchPageResult,
    InspectionFetchResult,
)

HOME = "https://example.com/"


def page(url, html, *, cookies=None):
    return FetchPageResult(
        requested_url=url,
        final_url=url,
        status_code=200,
        content_type="text/html",
        html=html,
        set_cookie_names=cookies or [],
        tls_valid=True,
    )


def failed_page(url, code="timeout"):
    return FetchPageResult(
        requested_url=url,
        final_url=url,
        error=FetchError(code, "technical detail", url),
    )


class FakeFetcher:
    def __init__(self, pages):
        self.pages = pages
        self.calls = []

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return None

    def fetch(self, target_url, candidate_urls):
        requested = list(candidate_urls)
        self.calls.append(requested)
        results = [self.pages[url] for url in requested]
        errors = [item.error for item in results if item.error]
        return InspectionFetchResult(
            target_url=target_url,
            pages_requested=len(requested),
            pages_fetched=sum(item.error is None for item in results),
            pages=results,
            errors=errors,
        )


def client_with(monkeypatch, pages):
    fake = FakeFetcher(pages)
    monkeypatch.setattr(service, "WebFetcher", lambda: fake)
    monkeypatch.delenv("API_KEY", raising=False)
    monkeypatch.delenv("API_KEYS", raising=False)
    return TestClient(create_app()), fake


def test_valid_simple_site_runs_full_pipeline(monkeypatch):
    client, fake = client_with(
        monkeypatch,
        {HOME: page(HOME, "<html><title>Inicio</title><p>Empresa</p></html>")},
    )

    response = client.post("/privacy/diagnose", json={"url": HOME})

    assert response.status_code == 200
    body = response.json()
    assert len(body["controls"]) == 7
    assert isinstance(body["score"], int)
    assert isinstance(body["status"], str)
    assert 0 <= body["coverage"] <= 100
    assert len(body["priorities"]) <= 3
    assert body["scope"] == {"pages_requested": 1, "pages_analyzed": 1, "limited": False}
    assert fake.calls == [[HOME]]


def test_home_and_privacy_are_selected_without_refetching_home(monkeypatch):
    privacy = "https://example.com/privacidad"
    home_html = f'<a href="{privacy}">Política de privacidad</a>'
    client, fake = client_with(
        monkeypatch,
        {
            HOME: page(HOME, home_html),
            privacy: page(privacy, "<title>Política de privacidad</title>"),
        },
    )

    response = client.post("/privacy/diagnose", json={"url": HOME})

    assert response.status_code == 200
    assert fake.calls == [[HOME], [privacy]]
    assert response.json()["scope"]["pages_analyzed"] == 2


def test_contact_form_is_analyzed(monkeypatch):
    contact = "https://example.com/contacto"
    client, _ = client_with(
        monkeypatch,
        {
            HOME: page(HOME, f'<a href="{contact}">Contacto</a>'),
            contact: page(
                contact,
                '<form><label for="email">Correo</label><input id="email" name="email" type="email"></form>',
            ),
        },
    )

    response = client.post("/privacy/diagnose", json={"url": HOME})

    assert response.status_code == 200
    controls = {item["control_code"]: item for item in response.json()["controls"]}
    assert controls["PRV-101"]["result"] == "detected"


def test_selection_is_bounded_to_five_pages(monkeypatch):
    paths = ["privacidad", "contacto", "newsletter", "cotizar", "registro"]
    labels = ["Privacidad", "Contacto", "Newsletter", "Cotizar", "Registro"]
    urls = [f"https://example.com/{path}" for path in paths]
    html = "".join(f'<a href="{url}">{label}</a>' for url, label in zip(urls, labels))
    pages = {HOME: page(HOME, html), **{url: page(url, "<title>Page</title>") for url in urls}}
    client, fake = client_with(monkeypatch, pages)

    response = client.post("/privacy/diagnose", json={"url": HOME})

    assert response.status_code == 200
    assert sum(len(call) for call in fake.calls) == 5
    assert len(fake.calls[1]) == 4
    assert response.json()["scope"]["pages_requested"] == 5
    assert response.json()["scope"]["limited"] is True


def test_invalid_url_returns_stable_400(monkeypatch):
    client, fake = client_with(monkeypatch, {})

    response = client.post("/privacy/diagnose", json={"url": "file:///etc/passwd"})

    assert response.status_code == 400
    assert response.json()["error"] == "invalid_url"
    assert fake.calls == []


def test_ssrf_block_and_robots_block_have_controlled_errors(monkeypatch):
    for inspector_code, api_code, status in (
        ("blocked_by_ssrf", "unsafe_target", 400),
        ("robots_disallowed", "inspection_blocked", 422),
    ):
        client, _ = client_with(monkeypatch, {HOME: failed_page(HOME, inspector_code)})
        response = client.post("/privacy/diagnose", json={"url": HOME})
        assert response.status_code == status
        assert response.json()["error"] == api_code


def test_home_timeout_returns_no_artificial_diagnostic(monkeypatch):
    client, _ = client_with(monkeypatch, {HOME: failed_page(HOME)})

    response = client.post("/privacy/diagnose", json={"url": HOME})

    assert response.status_code == 422
    assert response.json() == {
        "error": "inspection_failed",
        "message": "No fue posible inspeccionar el sitio solicitado.",
    }
    assert "score" not in response.json()
    assert "traceback" not in response.text.lower()


def test_secondary_timeout_preserves_partial_evidence(monkeypatch):
    privacy = "https://example.com/privacidad"
    contact = "https://example.com/contacto"
    html = f'<a href="{privacy}">Privacidad</a><a href="{contact}">Contacto</a>'
    client, _ = client_with(
        monkeypatch,
        {
            HOME: page(HOME, html),
            privacy: failed_page(privacy),
            contact: page(contact, '<a href="mailto:hello@example.com">Email</a>'),
        },
    )
    captured = {}

    def diagnostic_with_capture(contract):
        captured["contract"] = contract
        return real_privacy_diagnostic(contract)

    monkeypatch.setattr(service, "run_privacy_diagnostic", diagnostic_with_capture)

    response = client.post("/privacy/diagnose", json={"url": HOME})

    assert response.status_code == 200
    body = response.json()
    assert len(body["controls"]) == 7
    assert body["scope"] == {"pages_requested": 3, "pages_analyzed": 2, "limited": False}
    assert captured["contract"].inspection.errors[0]["code"] == "timeout"
    controls = {item["control_code"]: item for item in body["controls"]}
    assert controls["PRV-002"]["result"] in {"partial", "not_evaluable", "not_detected"}
    assert body["coverage"] <= 100


def test_api_key_mechanism_is_reused(monkeypatch):
    monkeypatch.setenv("API_KEY", "secret")
    fake = FakeFetcher({HOME: page(HOME, "<title>Inicio</title>")})
    monkeypatch.setattr(service, "WebFetcher", lambda: fake)
    client = TestClient(create_app())

    assert client.post("/privacy/diagnose", json={"url": HOME}).status_code == 401
    assert client.post(
        "/privacy/diagnose", json={"url": HOME}, headers={"X-Api-Key": "secret"}
    ).status_code == 200


def test_unexpected_error_is_sanitized(monkeypatch):
    client, _ = client_with(monkeypatch, {HOME: page(HOME, "<title>Inicio</title>")})
    monkeypatch.setattr(service, "run_privacy_diagnostic", lambda contract: 1 / 0)

    response = client.post("/privacy/diagnose", json={"url": HOME})

    assert response.status_code == 500
    assert response.json()["error"] == "internal_error"
    assert "division" not in response.text.lower()
