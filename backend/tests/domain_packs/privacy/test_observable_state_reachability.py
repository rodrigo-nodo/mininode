"""Integral reachability tests for observable Privacy V1 outcomes."""

import sys
from pathlib import Path

BACKEND_SRC = Path(__file__).resolve().parents[3] / "src"
sys.path.insert(0, str(BACKEND_SRC))

from mininode_api.domain_packs.privacy.evaluator import evaluate_control
from mininode_api.domain_packs.privacy.evidence_adapter import adapt_evidence
from mininode_api.web_inspector.extractor import build_evidence
from mininode_api.web_inspector.models import (
    FetchError,
    FetchPageResult,
    InspectionFetchResult,
)


def inspect(*pages: FetchPageResult, target_url: str | None = None, errors=None):
    target = target_url or pages[0].requested_url
    fetched = InspectionFetchResult(
        target_url=target,
        pages_requested=len(pages),
        pages_fetched=sum(page.error is None for page in pages),
        pages=list(pages),
        errors=errors or [],
    )
    contract = build_evidence(fetched)
    adapted = adapt_evidence(contract)
    results = {}
    for code in adapted:
        results[code] = evaluate_control(code, adapted[code], results)
    return contract, adapted, results


def page(
    requested_url="https://example.com/",
    final_url="https://example.com/",
    html="<title>Inicio</title>",
    *,
    cookies=None,
    tls_valid=True,
):
    return FetchPageResult(
        requested_url=requested_url,
        final_url=final_url,
        status_code=200,
        content_type="text/html",
        html=html,
        set_cookie_names=cookies or [],
        tls_valid=tls_valid,
    )


def failed_page(code, *, tls_valid=None, error_class=None):
    url = "https://example.com/"
    return FetchPageResult(
        requested_url=url,
        final_url=url,
        error=FetchError(code, code, url),
        tls_valid=tls_valid,
        transport_error_class=error_class,
    )


def test_prv104_detected_from_nearby_privacy_information():
    html = """
        <form><input type="email" name="email">
        <p>Información sobre tratamiento de datos personales.</p></form>
    """
    _, evidence, results = inspect(page(html=html))

    assert evidence["PRV-104"]["privacy_information"] is True
    assert results["PRV-104"]["result"] == "detected"


def test_prv104_detected_from_nearby_privacy_link():
    html = """
        <form><input type="email" name="email">
        <a href="/privacidad">Política de privacidad</a></form>
    """
    _, evidence, results = inspect(page(html=html))

    assert evidence["PRV-104"]["privacy_link"] is True
    assert results["PRV-104"]["result"] == "detected"


def test_prv104_partial_from_complementary_consent_signal_only():
    html = """
        <form><input type="email" name="email">
        <label><input type="checkbox" name="accept">Acepto</label></form>
    """
    _, evidence, results = inspect(page(html=html))

    assert evidence["PRV-104"]["privacy_information"] is False
    assert evidence["PRV-104"]["consent_mechanism"] is True
    assert results["PRV-104"]["result"] == "partial"


def test_prv104_not_detected_without_observable_associated_signal():
    _, _, results = inspect(page(html='<form><input type="email" name="email"></form>'))
    assert results["PRV-104"]["result"] == "not_detected"


def test_prv104_not_applicable_without_personal_form():
    _, _, results = inspect(page())
    assert results["PRV-104"]["result"] == "not_applicable"


def test_prv104_not_evaluable_when_inspection_is_insufficient():
    _, _, results = inspect(failed_page("timeout", error_class="ConnectTimeout"))
    assert results["PRV-104"]["result"] == "not_evaluable"


def test_prv201_detected_from_observed_cookie_and_banner():
    _, evidence, results = inspect(
        page(html="<p>Usamos cookies para recordar la sesión.</p>", cookies=["session"])
    )

    assert evidence["PRV-201"]["relevant_cookies"] is True
    assert results["PRV-201"]["result"] == "detected"


def test_prv201_not_detected_from_observed_cookie_without_banner():
    _, _, results = inspect(page(cookies=["session"]))
    assert results["PRV-201"]["result"] == "not_detected"


def test_prv201_not_applicable_without_observed_cookie():
    _, _, results = inspect(page())
    assert results["PRV-201"]["result"] == "not_applicable"


def test_prv201_not_evaluable_when_inspection_is_insufficient():
    _, _, results = inspect(failed_page("timeout", error_class="ConnectTimeout"))
    assert results["PRV-201"]["result"] == "not_evaluable"


def test_prv201_preferences_are_complementary_and_do_not_change_result():
    _, evidence, results = inspect(
        page(html="<p>Puede gestionar cookies.</p>", cookies=["session"])
    )

    assert evidence["PRV-201"]["preference_mechanism"] is True
    assert evidence["PRV-201"]["cookie_banner"] is False
    assert results["PRV-201"]["result"] == "not_detected"


def policy_results(*secondary_pages, title="Política de privacidad"):
    policy_url = "https://example.com/privacy"
    home = page(html=f'<a href="{policy_url}">Privacidad</a>')
    pages = [home, *secondary_pages]
    errors = [item.error for item in secondary_pages if item.error]
    _, _, results = inspect(*pages, errors=errors)
    return results


def test_prv002_detected_from_accessible_corroborated_candidate():
    result = policy_results(page("https://example.com/privacy", "https://example.com/privacy", "<title>Privacidad</title>"))
    assert result["PRV-002"]["result"] == "detected"


def test_prv002_partial_from_failed_candidate_access():
    url = "https://example.com/privacy"
    failed = FetchPageResult(url, url, error=FetchError("http_error", "failed", url))
    assert policy_results(failed)["PRV-002"]["result"] == "partial"


def test_prv002_partial_from_uncorroborated_candidate_title():
    generic = page("https://example.com/privacy", "https://example.com/privacy", "<title>Inicio</title>")
    assert policy_results(generic)["PRV-002"]["result"] == "partial"


def test_prv002_not_applicable_without_policy_candidate():
    _, _, results = inspect(page())
    assert results["PRV-002"]["result"] == "not_applicable"


def test_prv002_not_evaluable_when_candidate_was_not_checked():
    _, _, results = inspect(page(html='<a href="/privacy">Privacidad</a>'))
    assert results["PRV-002"]["result"] == "not_evaluable"


def test_prv002_adapter_outputs_never_produce_removed_not_detected_state():
    url = "https://example.com/privacy"
    failed = FetchPageResult(url, url, error=FetchError("http_error", "failed", url))
    scenarios = [
        inspect(page())[2],
        policy_results(page(url, url, "<title>Privacidad</title>")),
        policy_results(page(url, url, "<title>Inicio</title>")),
        policy_results(failed),
        inspect(page(html='<a href="/privacy">Privacidad</a>'))[2],
    ]

    assert {results["PRV-002"]["result"] for results in scenarios} == {
        "detected", "partial", "not_applicable", "not_evaluable"
    }


def test_prv501_detected_from_verified_https_without_mixed_content():
    _, _, results = inspect(page())
    assert results["PRV-501"]["result"] == "detected"


def test_prv501_partial_from_verified_https_with_mixed_content():
    _, _, results = inspect(page(html='<img src="http://cdn.example/image.png">'))
    assert results["PRV-501"]["result"] == "partial"


def test_prv501_not_detected_from_confirmed_http():
    http = page("http://example.com/", "http://example.com/", tls_valid=None)
    contract, _, results = inspect(http)

    assert contract.transport.https is False
    assert contract.transport.tls_valid is None
    assert results["PRV-501"]["result"] == "not_detected"


def test_prv501_not_detected_from_explicit_certificate_failure():
    contract, _, results = inspect(
        failed_page("http_error", tls_valid=False, error_class="ConnectError")
    )

    assert contract.transport.https is True
    assert contract.transport.tls_valid is False
    assert results["PRV-501"]["result"] == "not_detected"


def test_prv501_timeout_is_not_evaluable():
    _, _, results = inspect(failed_page("timeout", error_class="ConnectTimeout"))
    assert results["PRV-501"]["result"] == "not_evaluable"


def test_prv501_dns_failure_is_not_evaluable():
    _, _, results = inspect(failed_page("dns_failure"))
    assert results["PRV-501"]["result"] == "not_evaluable"


def test_prv501_generic_connect_error_is_not_evaluable():
    _, _, results = inspect(failed_page("http_error", error_class="ConnectError"))
    assert results["PRV-501"]["result"] == "not_evaluable"


def test_prv501_detected_after_confirmed_http_to_https_redirect():
    redirected = page("http://example.com/", "https://example.com/", tls_valid=True)
    contract, _, results = inspect(redirected, target_url="http://example.com/")

    assert contract.transport.http_redirects_to_https is True
    assert results["PRV-501"]["result"] == "detected"
