import json
import logging
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


def page(url, html, *, cookies=None, requested_url=None):
    return FetchPageResult(
        requested_url=requested_url or url,
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
        self.target_calls = []
        self.inspection_budgets = []

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return None

    def fetch(self, target_url, candidate_urls):
        requested = list(candidate_urls)
        self.calls.append(requested)
        self.target_calls.append(target_url)
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

    def factory(**kwargs):
        fake.inspection_budgets.append(kwargs["inspection_budget"])
        return fake

    monkeypatch.setattr(service, "WebFetcher", factory)
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


def test_static_include_data_rel_links_are_selected_but_fragment_is_not_a_page(monkeypatch):
    footer = "https://example.com/partials/footer.html"
    contact = "https://example.com/contact/index.html"
    privacy = "https://example.com/legal/privacy/index.html"
    privacy_final = "https://example.com/legal/privacy/"
    client, fake = client_with(
        monkeypatch,
        {
            HOME: page(HOME, '<div data-include="partials/footer.html"></div>'),
            footer: page(
                footer,
                '<a href="#" data-rel="contact/index.html">Contacto</a>'
                '<a href="#" data-rel="legal/privacy/index.html">Política de privacidad</a>',
            ),
            contact: page(
                contact,
                '<title>Contacto</title><form>'
                '<label>Nombre <input name="name"></label>'
                '<label>Email <input name="email" type="email"></label>'
                '<label>Mensaje <textarea name="message"></textarea></label>'
                '</form>',
            ),
            privacy: page(
                privacy_final,
                "<title>Política de privacidad</title>",
                requested_url=privacy,
            ),
        },
    )
    response = client.post("/privacy/diagnose", json={"url": HOME})

    assert response.status_code == 200
    assert fake.calls == [[HOME], [footer], [privacy, contact]]
    assert response.json()["scope"] == {
        "pages_requested": 3,
        "pages_analyzed": 3,
        "limited": False,
    }
    controls = {item["control_code"]: item for item in response.json()["controls"]}
    assert controls["PRV-001"]["result"] == "detected"
    assert controls["PRV-002"]["result"] == "detected"
    assert controls["PRV-101"]["result"] == "detected"
    assert controls["PRV-301"]["result"] == "detected"
    assert response.json()["coverage"] == 100


def test_privacy_response_is_utf8_json_with_exact_spanish_text(monkeypatch):
    client, _ = client_with(
        monkeypatch,
        {HOME: page(HOME, "<html><title>Inicio</title></html>")},
    )
    expected = (
        "Política de privacidad",
        "Preparación avanzada",
        "páginas públicas",
        "Información o consentimiento",
    )
    monkeypatch.setattr(
        service,
        "run_privacy_diagnostic",
        lambda contract: {"unicode_samples": list(expected)},
    )

    response = client.post("/privacy/diagnose", json={"url": HOME})

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/json")
    decoded = response.content.decode("utf-8")
    body = response.json()
    serialized = str(body)
    for text in expected:
        assert text in decoded
        assert text in serialized
    assert "PolÃtica" not in decoded
    assert "PreparaciÃ³n" not in decoded


def test_include_failure_does_not_abort_valid_home_diagnostic(monkeypatch):
    footer = "https://example.com/footer.html"
    client, fake = client_with(
        monkeypatch,
        {
            HOME: page(HOME, '<div data-include="/footer.html"></div>'),
            footer: failed_page(footer),
        },
    )

    response = client.post("/privacy/diagnose", json={"url": HOME})

    assert response.status_code == 200
    assert fake.calls == [[HOME], [footer]]
    assert response.json()["scope"] == {
        "pages_requested": 1,
        "pages_analyzed": 1,
        "limited": False,
    }


def test_include_discovery_and_secondary_fetch_share_total_budget(monkeypatch):
    footer = "https://example.com/footer.html"
    privacy = "https://example.com/privacy"
    client, fake = client_with(
        monkeypatch,
        {
            HOME: page(HOME, '<div data-include="/footer.html"></div>'),
            footer: page(footer, f'<a href="{privacy}">Privacidad</a>'),
            privacy: page(privacy, "<title>Privacidad</title>"),
        },
    )
    ticks = iter([0.0, 10.0, 25.0])
    monkeypatch.setattr(service, "monotonic", lambda: next(ticks))

    response = client.post("/privacy/diagnose", json={"url": HOME})

    assert response.status_code == 200
    assert fake.inspection_budgets == [30.0, 20.0, 5.0]


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


def test_contact_form_priority_serializes_sanitized_optional_source_url(monkeypatch):
    contact_requested = "https://example.com/contacto?email=test@example.com#form"
    contact_inspected = "https://example.com/contacto?email=test%40example.com"
    contact_public = "https://example.com/contacto"
    client, _ = client_with(
        monkeypatch,
        {
            HOME: page(HOME, f'<a href="{contact_requested}">Contacto</a>'),
            contact_inspected: page(
                contact_requested,
                '<form><input name="email" type="email"></form>',
            ),
        },
    )

    response = client.post("/privacy/diagnose", json={"url": HOME})

    assert response.status_code == 200
    body = response.json()
    priority = next(item for item in body["priorities"] if item["control_code"] == "PRV-104")
    assert priority["source_url"] == contact_public
    assert {"control_code", "name", "priority", "finding", "recommendation"} <= priority.keys()
    assert "?" not in priority["source_url"]
    assert "#" not in priority["source_url"]


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


def test_total_budget_is_not_reset_before_secondary_fetch(monkeypatch):
    privacy = "https://example.com/privacidad"
    client, fake = client_with(
        monkeypatch,
        {
            HOME: page(HOME, f'<a href="{privacy}">Privacidad</a>'),
            privacy: page(privacy, "<title>Privacidad</title>"),
        },
    )
    ticks = iter([0.0, 25.0])
    monkeypatch.setattr(service, "monotonic", lambda: next(ticks))

    response = client.post("/privacy/diagnose", json={"url": HOME})

    assert response.status_code == 200
    assert fake.inspection_budgets == [30.0, 5.0]


def test_exhausted_total_budget_does_not_start_secondary_fetch(monkeypatch):
    privacy = "https://example.com/privacidad"
    client, fake = client_with(
        monkeypatch,
        {HOME: page(HOME, f'<a href="{privacy}">Privacidad</a>')},
    )
    ticks = iter([0.0, 30.0])
    monkeypatch.setattr(service, "monotonic", lambda: next(ticks))

    response = client.post("/privacy/diagnose", json={"url": HOME})

    assert response.status_code == 200
    assert fake.calls == [[HOME]]
    assert fake.inspection_budgets == [30.0]
    assert response.json()["scope"]["pages_analyzed"] == 1


def test_redirected_home_is_effective_base_and_original_target_is_preserved(monkeypatch):
    original = "http://example.com"
    privacy = "https://example.com/privacidad"
    contact = "https://example.com/contacto"
    client, fake = client_with(
        monkeypatch,
        {
            original: page(
                HOME,
                '<a href="/privacidad">Privacidad</a><a href="/contacto">Contacto</a>',
                requested_url=original,
            ),
            privacy: page(privacy, "<title>Privacidad</title>"),
            contact: page(contact, "<title>Contacto</title>"),
        },
    )
    captured = {}

    def diagnostic_with_capture(contract):
        captured["contract"] = contract
        return real_privacy_diagnostic(contract)

    monkeypatch.setattr(service, "run_privacy_diagnostic", diagnostic_with_capture)

    response = client.post("/privacy/diagnose", json={"url": original})

    assert response.status_code == 200
    assert fake.calls == [[original], [privacy, contact]]
    assert fake.target_calls == [original, HOME]
    assert captured["contract"].target.requested_url == original
    assert captured["contract"].target.final_url == HOME
    assert captured["contract"].transport.http_redirects_to_https is True


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


def test_home_failure_logs_one_safe_structured_event(monkeypatch, caplog):
    secret = "super-secret-api-key"
    pinned_ip = "203.0.113.42"
    raw_socket_message = "connection refused on socket"
    html = "<html>private body</html>"
    cookie = "session=private-cookie"
    failed = failed_page(f"{HOME}?token=private-query", "dns_failure")
    failed.elapsed_ms = 123
    failed.redirect_count = 1
    failed.status_code = 503
    failed.network_family = "ipv6"
    failed.transport_error_class = "ConnectError"
    failed.html = html
    failed.set_cookie_names = [cookie]
    failed.error = FetchError(
        "dns_failure",
        f"must not log {secret} {pinned_ip} {raw_socket_message} {html} {cookie}",
        failed.requested_url,
    )
    client, _ = client_with(monkeypatch, {HOME: failed})

    with caplog.at_level(logging.WARNING, logger=service.__name__):
        response = client.post(
            "/privacy/diagnose",
            json={"url": HOME},
            headers={"X-Api-Key": secret},
        )

    events = [
        json.loads(record.message)
        for record in caplog.records
        if "privacy_home_inspection_failed" in record.message
    ]
    assert response.status_code == 422
    assert response.json() == {
        "error": "inspection_failed",
        "message": "No fue posible inspeccionar el sitio solicitado.",
    }
    assert events == [
        {
            "elapsed_ms": 123,
            "error_code": "dns_failure",
            "event": "privacy_home_inspection_failed",
            "failure_class": "controlled_fetch_error",
            "hostname": "example.com",
            "network_family": "ipv6",
            "phase": "home_fetch",
            "redirect_count": 1,
            "status_code": 503,
            "transport_error_class": "ConnectError",
        }
    ]
    rendered = " ".join(record.message for record in caplog.records)
    for sensitive_value in (
        secret,
        pinned_ip,
        raw_socket_message,
        html,
        cookie,
        "token",
        "private-query",
    ):
        assert sensitive_value not in rendered


def test_success_does_not_log_home_failure(monkeypatch, caplog):
    client, _ = client_with(monkeypatch, {HOME: page(HOME, "<title>Inicio</title>")})

    with caplog.at_level(logging.WARNING, logger=service.__name__):
        response = client.post("/privacy/diagnose", json={"url": HOME})

    assert response.status_code == 200
    assert not any("privacy_home_inspection_failed" in record.message for record in caplog.records)


def test_secondary_timeout_preserves_partial_evidence(monkeypatch, caplog):
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

    with caplog.at_level(logging.WARNING, logger=service.__name__):
        response = client.post("/privacy/diagnose", json={"url": HOME})

    assert response.status_code == 200
    body = response.json()
    assert len(body["controls"]) == 7
    assert body["scope"] == {"pages_requested": 3, "pages_analyzed": 2, "limited": False}
    assert captured["contract"].inspection.errors[0]["code"] == "timeout"
    controls = {item["control_code"]: item for item in body["controls"]}
    assert controls["PRV-002"]["result"] == "partial"
    assert body["coverage"] <= 100
    assert not any("privacy_home_inspection_failed" in record.message for record in caplog.records)


def test_api_key_mechanism_is_reused(monkeypatch):
    monkeypatch.setenv("API_KEY", "secret")
    fake = FakeFetcher({HOME: page(HOME, "<title>Inicio</title>")})
    monkeypatch.setattr(
        service,
        "WebFetcher",
        lambda **kwargs: fake.inspection_budgets.append(kwargs["inspection_budget"]) or fake,
    )
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
