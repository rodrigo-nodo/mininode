import json
import logging
import sys
from copy import deepcopy
from pathlib import Path

import pytest
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
        self.deadlines = []

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return None

    def fetch(self, target_url, candidate_urls, *, deadline=None):
        requested = list(candidate_urls)
        self.calls.append(requested)
        self.target_calls.append(target_url)
        self.deadlines.append(deadline)
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


def adaptive_result(**outcomes):
    defaults = {
        "PRV-001": "detected", "PRV-002": "detected",
        "PRV-101": "detected", "PRV-104": "detected",
        "PRV-201": "not_detected", "PRV-301": "detected",
        "PRV-501": "not_detected",
    }
    defaults.update(outcomes)
    return {
        "controls": [
            {"control_code": code, "result": result}
            for code, result in defaults.items()
        ],
        "coverage": 100,
    }


def sequenced_diagnostic(monkeypatch, *results):
    calls = []

    def diagnostic(contract):
        calls.append(contract)
        return results[min(len(calls) - 1, len(results) - 1)]

    monkeypatch.setattr(service, "run_privacy_diagnostic", diagnostic)
    return calls


@pytest.mark.parametrize(
    ("control", "result", "categories"),
    [
        ("PRV-002", "not_evaluable", {"privacy"}),
        ("PRV-301", "not_evaluable", {"contact"}),
        ("PRV-101", "not_evaluable", {"contact", "action"}),
        ("PRV-104", "not_evaluable", {"contact", "action"}),
        ("PRV-002", "detected", set()),
        ("PRV-002", "not_detected", set()),
        ("PRV-301", "not_applicable", set()),
        ("PRV-101", "detected", set()),
        ("PRV-104", "not_applicable", set()),
        ("PRV-001", "not_evaluable", set()),
        ("PRV-201", "not_evaluable", set()),
        ("PRV-201", "not_detected", set()),
        ("PRV-501", "not_evaluable", set()),
    ],
)
def test_gap_policy_is_control_and_state_specific(control, result, categories):
    diagnostic = adaptive_result()
    for item in diagnostic["controls"]:
        if item["control_code"] == control:
            item["result"] = result

    assert service._needed_categories(diagnostic) == categories


def test_remaining_gap_telemetry_reuses_policy_without_mutating_diagnostic():
    diagnostic = adaptive_result(
        **{
            "PRV-001": "not_evaluable",
            "PRV-002": "partial",
            "PRV-104": "not_detected",
            "PRV-201": "not_evaluable",
            "PRV-501": "not_evaluable",
        }
    )
    diagnostic.update(
        score=42,
        coverage=57,
        status="insufficient_evidence",
        priorities=[{"control_code": "PRV-104"}],
        source_url="https://example.com/private?token=secret",
        evidence_summary="private evidence",
    )
    before = deepcopy(diagnostic)

    gaps = service._remaining_adaptive_gaps(diagnostic)

    assert list(gaps) == ["PRV-002", "PRV-104"]
    assert service._needed_categories(diagnostic) == {"privacy", "contact", "action"}
    assert diagnostic == before


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


def test_adaptive_home_sufficient_does_not_fetch_existing_candidates(monkeypatch, caplog):
    privacy, contact, signup = (f"{HOME}{path}" for path in ("privacy", "contact", "signup"))
    html = (
        f'<a href="{privacy}">Privacy</a><a href="{contact}">Contact</a>'
        f'<a href="{signup}">Signup</a>'
    )
    client, fake = client_with(monkeypatch, {HOME: page(HOME, html)})
    sequenced_diagnostic(monkeypatch, adaptive_result())

    with caplog.at_level(logging.INFO, logger=service.__name__):
        response = client.post("/privacy/diagnose", json={"url": HOME})

    assert response.status_code == 200
    assert fake.calls == [[HOME]]
    event = json.loads(next(record.message for record in caplog.records if "privacy_adaptive_scope_completed" in record.message))
    assert (event["pages_attempted"], event["pages_analyzed"]) == (1, 1)
    assert event["expansion_triggered"] is False
    assert event["stop_reason"] == "no_resolvable_gaps"
    assert event["remaining_gap_controls"] == []
    assert event["remaining_gap_categories"] == []


def test_adaptive_completion_logs_once_without_sensitive_page_data(monkeypatch, caplog):
    target = f"{HOME}private/path?token=private-query"
    private_html = (
        "<html>email private@example.com; phone +1-555-0100; "
        "IP 192.0.2.42; socket connection refused</html>"
    )
    client, _ = client_with(
        monkeypatch,
        {target: page(target, private_html, cookies=["private_session_cookie"])},
    )
    sequenced_diagnostic(monkeypatch, adaptive_result())

    with caplog.at_level(logging.INFO, logger=service.__name__):
        response = client.post("/privacy/diagnose", json={"url": target})

    events = [
        record.message
        for record in caplog.records
        if "privacy_adaptive_scope_completed" in record.message
    ]
    assert response.status_code == 200
    assert len(events) == 1
    assert json.loads(events[0])["hostname"] == "example.com"
    for sensitive_value in (
        "private/path",
        "token",
        "private-query",
        private_html,
        "private@example.com",
        "+1-555-0100",
        "private_session_cookie",
        "192.0.2.42",
        "socket connection refused",
    ):
        assert sensitive_value not in events[0]


def test_coverage_100_does_not_stop_real_privacy_gap(monkeypatch):
    privacy, contact = f"{HOME}privacy", f"{HOME}contact"
    client, fake = client_with(monkeypatch, {
        HOME: page(HOME, f'<a href="{privacy}">Privacy</a><a href="{contact}">Contact</a>'),
        privacy: page(privacy, "<h1>Privacy policy</h1>"),
    })
    sequenced_diagnostic(
        monkeypatch,
        adaptive_result(**{"PRV-002": "partial"}),
        adaptive_result(),
    )

    assert client.post("/privacy/diagnose", json={"url": HOME}).status_code == 200
    assert fake.calls == [[HOME], [privacy]]


def test_failed_privacy_candidate_is_replaced_and_consumes_attempt(monkeypatch, caplog):
    first, second = f"{HOME}privacy-a", f"{HOME}privacy-b"
    client, fake = client_with(monkeypatch, {
        HOME: page(HOME, f'<a href="{second}">Privacy B</a><a href="{first}">Privacy A</a>'),
        first: failed_page(first, "robots_disallowed"),
        second: page(second, "<title>Privacy policy</title>"),
    })
    contracts = []

    def diagnostic_with_capture(contract):
        contracts.append(contract)
        return real_privacy_diagnostic(contract)

    monkeypatch.setattr(service, "run_privacy_diagnostic", diagnostic_with_capture)

    with caplog.at_level(logging.INFO, logger=service.__name__):
        response = client.post("/privacy/diagnose", json={"url": HOME})

    assert response.status_code == 200
    assert fake.calls == [[HOME], [first], [second]]
    assert len(contracts) == 3
    outcomes = [
        next(
            control["result"]
            for control in result["controls"]
            if control["control_code"] == "PRV-002"
        )
        for result in map(real_privacy_diagnostic, contracts)
    ]
    assert outcomes == ["not_evaluable", "partial", "detected"]
    assert contracts[1].inspection.errors[0]["code"] == "robots_disallowed"
    assert contracts[1].inspection.pages_analyzed == 1
    assert contracts[-1].inspection.pages_requested == 3
    assert contracts[-1].inspection.pages_analyzed == 2
    event = json.loads(next(record.message for record in caplog.records if "privacy_adaptive_scope_completed" in record.message))
    assert event["categories_attempted"] == ["privacy", "privacy"]


def test_not_evaluable_without_compatible_candidate_stops_as_no_candidates(
    monkeypatch, caplog
):
    client, fake = client_with(monkeypatch, {HOME: page(HOME, "<title>Home</title>")})
    sequenced_diagnostic(monkeypatch, adaptive_result(**{"PRV-002": "not_evaluable"}))

    with caplog.at_level(logging.INFO, logger=service.__name__):
        response = client.post("/privacy/diagnose", json={"url": HOME})

    assert response.status_code == 200
    assert fake.calls == [[HOME]]
    event = json.loads(
        next(
            record.message
            for record in caplog.records
            if "privacy_adaptive_scope_completed" in record.message
        )
    )
    assert event["stop_reason"] == "no_candidates"
    assert event["remaining_gap_controls"] == ["PRV-002"]
    assert event["remaining_gap_categories"] == ["privacy"]


def test_form_gap_prefers_contact_then_one_action(monkeypatch):
    contact, signup, checkout = f"{HOME}contact", f"{HOME}signup", f"{HOME}checkout"
    html = "".join(f'<a href="{url}">{label}</a>' for url, label in (
        (checkout, "Checkout"), (signup, "Signup"), (contact, "Contact")))
    client, fake = client_with(monkeypatch, {
        HOME: page(HOME, html), contact: page(contact, "Contact"),
        signup: page(signup, "Signup"), checkout: page(checkout, "Checkout"),
    })
    gap = adaptive_result(**{"PRV-101": "not_detected"})
    sequenced_diagnostic(monkeypatch, gap, gap, adaptive_result())

    assert client.post("/privacy/diagnose", json={"url": HOME}).status_code == 200
    assert fake.calls == [[HOME], [contact], [checkout]]


def test_action_cannot_replace_contact_only_gap(monkeypatch):
    contact, signup = f"{HOME}contact", f"{HOME}signup"
    client, fake = client_with(monkeypatch, {
        HOME: page(HOME, f'<a href="{contact}">Contact</a><a href="{signup}">Signup</a>'),
        contact: failed_page(contact), signup: page(signup, "Signup"),
    })
    sequenced_diagnostic(monkeypatch, adaptive_result(**{"PRV-301": "not_detected"}))

    assert client.post("/privacy/diagnose", json={"url": HOME}).status_code == 200
    assert fake.calls == [[HOME], [contact]]


@pytest.mark.parametrize(("initial_score", "final_score"), [(90, 40), (40, 90)])
def test_successful_secondary_evidence_is_never_rolled_back_by_score(
    monkeypatch, initial_score, final_score
):
    contact = f"{HOME}contact"
    client, fake = client_with(monkeypatch, {
        HOME: page(HOME, f'<a href="{contact}">Contact</a>'),
        contact: page(contact, '<img src="http://example.com/tracker.png">', cookies=["session"]),
    })
    calls = []

    def diagnostic(contract):
        calls.append(contract)
        if len(calls) == 1:
            return {
                **adaptive_result(**{"PRV-301": "not_detected"}),
                "score": initial_score,
            }
        result = real_privacy_diagnostic(contract)
        result["score"] = final_score
        return result

    monkeypatch.setattr(service, "run_privacy_diagnostic", diagnostic)

    response = client.post("/privacy/diagnose", json={"url": HOME})

    assert response.status_code == 200
    assert fake.calls == [[HOME], [contact]]
    assert response.json()["score"] == final_score
    assert calls[-1].inspection.pages_analyzed == 2
    assert calls[-1].cookies.detected is True
    assert calls[-1].transport.mixed_content is True


def test_maximum_is_five_attempts_including_failed_candidates(monkeypatch, caplog):
    urls = [f"{HOME}privacy-{letter}" for letter in "abcdef"]
    html = "".join(f'<a href="{url}">Privacy {index}</a>' for index, url in enumerate(urls))
    client, fake = client_with(monkeypatch, {
        HOME: page(HOME, html), **{url: failed_page(url) for url in urls},
    })
    sequenced_diagnostic(monkeypatch, adaptive_result(**{"PRV-002": "partial"}))

    with caplog.at_level(logging.INFO, logger=service.__name__):
        response = client.post("/privacy/diagnose", json={"url": HOME})

    assert response.status_code == 200
    assert fake.calls == [[HOME], *[[url] for url in urls[:4]]]
    event = json.loads(next(record.message for record in caplog.records if "privacy_adaptive_scope_completed" in record.message))
    assert event["pages_attempted"] == 5
    assert event["pages_analyzed"] == 1
    assert event["stop_reason"] == "max_pages"
    assert event["remaining_gap_controls"] == ["PRV-002"]
    assert event["remaining_gap_categories"] == ["privacy"]


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
    assert response.json()["scope"] == {
        "pages_requested": 2,
        "pages_analyzed": 2,
        "limited": False,
    }
    controls = {item["control_code"]: item for item in response.json()["controls"]}
    assert controls["PRV-002"]["result"] == "detected"


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
    assert fake.calls == [[HOME], [footer], [privacy], [contact]]
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
        "Información de privacidad",
    )
    def diagnostic_with_samples(contract):
        return {**real_privacy_diagnostic(contract), "unicode_samples": list(expected)}

    monkeypatch.setattr(service, "run_privacy_diagnostic", diagnostic_with_samples)

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
    monkeypatch.setattr(service, "monotonic", lambda: next(ticks, 25.0))
    sequenced_diagnostic(
        monkeypatch,
        adaptive_result(**{"PRV-002": "partial"}),
        adaptive_result(),
    )

    response = client.post("/privacy/diagnose", json={"url": HOME})

    assert response.status_code == 200
    assert fake.inspection_budgets == [30.0]
    assert fake.deadlines == [30.0, 30.0, 30.0]


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
                '<form><input name="email" type="email" value="persona@example.com">'
                '<textarea name="message">contenido privado</textarea></form>',
            ),
        },
    )

    response = client.post("/privacy/diagnose", json={"url": HOME})

    assert response.status_code == 200
    body = response.json()
    priority = next(item for item in body["priorities"] if item["control_code"] == "PRV-104")
    assert priority["source_url"] == contact_public
    assert {"control_code", "name", "priority", "finding", "recommendation"} <= priority.keys()
    assert {"action_steps", "validation_step"} <= priority.keys()
    assert len(priority["action_steps"]) == 3
    assert all("example.com" not in text for text in [*priority["action_steps"], priority["validation_step"]])
    assert "?" not in priority["source_url"]
    assert "#" not in priority["source_url"]
    assert priority["evidence_summary"] == (
        "En el formulario revisado no se identificaron señales visibles de información de privacidad ni de consentimiento o aceptación."
    )
    serialized = str(body)
    assert "persona@example.com" not in serialized
    assert "contenido privado" not in serialized
    assert "<form" not in serialized
    assert "?" not in priority["evidence_summary"]


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
    assert all(len(call) == 1 for call in fake.calls)
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
    monkeypatch.setattr(service, "monotonic", lambda: next(ticks, 25.0))
    sequenced_diagnostic(
        monkeypatch,
        adaptive_result(**{"PRV-002": "partial"}),
        adaptive_result(),
    )

    response = client.post("/privacy/diagnose", json={"url": HOME})

    assert response.status_code == 200
    assert fake.inspection_budgets == [30.0]
    assert fake.deadlines == [30.0, 30.0]


def test_exhausted_total_budget_does_not_start_secondary_fetch(monkeypatch, caplog):
    privacy = "https://example.com/privacidad"
    client, fake = client_with(
        monkeypatch,
        {HOME: page(HOME, f'<a href="{privacy}">Privacidad</a>')},
    )
    ticks = iter([0.0, 30.0])
    monkeypatch.setattr(service, "monotonic", lambda: next(ticks, 30.0))
    sequenced_diagnostic(monkeypatch, adaptive_result(**{"PRV-002": "partial"}))

    with caplog.at_level(logging.INFO, logger=service.__name__):
        response = client.post("/privacy/diagnose", json={"url": HOME})

    assert response.status_code == 200
    assert fake.calls == [[HOME]]
    assert fake.inspection_budgets == [30.0]
    event = json.loads(next(record.message for record in caplog.records if "privacy_adaptive_scope_completed" in record.message))
    assert event["pages_analyzed"] == 1
    assert event["stop_reason"] == "deadline"
    assert event["remaining_gap_controls"] == ["PRV-002"]
    assert event["remaining_gap_categories"] == ["privacy"]


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
    assert fake.calls == [[original], [privacy], [contact]]
    assert fake.target_calls == [original, HOME, HOME]
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
        "error": "request_timeout",
        "message": "El sitio no respondió dentro del tiempo permitido.",
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
        "error": "dns_resolution_failed",
        "message": "No fue posible resolver el hostname solicitado.",
    }
    assert events == [
        {
            "attempted_addresses": [],
            "elapsed_ms": 123,
            "error_code": "dns_failure",
            "event": "privacy_home_inspection_failed",
            "failure_class": "controlled_fetch_error",
            "hostname": "example.com",
            "network_family": "ipv6",
            "phase": "home_fetch",
            "rejected_addresses": [],
            "redirect_rejected_reason": None,
            "redirect_count": 1,
            "resolved_addresses": [],
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


@pytest.mark.parametrize(
    ("internal_code", "public_code"),
    [
        ("dns_failure", "dns_resolution_failed"),
        ("timeout", "request_timeout"),
        ("tls_certificate_error", "tls_failure"),
        ("tls_error", "tls_failure"),
        ("http_error", "http_fetch_failed"),
        ("unsupported_content_type", "unsupported_content_type"),
        ("unexpected", "inspection_failed"),
    ],
)
def test_home_fetch_failure_classes_are_preserved(monkeypatch, internal_code, public_code):
    client, _ = client_with(monkeypatch, {HOME: failed_page(HOME, internal_code)})

    response = client.post("/privacy/diagnose", json={"url": HOME})

    assert response.status_code == 422
    assert response.json()["error"] == public_code


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
