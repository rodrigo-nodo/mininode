import sys
from pathlib import Path

import pytest

BACKEND_SRC = Path(__file__).resolve().parents[3] / "src"
sys.path.insert(0, str(BACKEND_SRC))

from mininode_api.domain_packs.privacy.evaluator import evaluate_control  # noqa: E402
from mininode_api.domain_packs.privacy.evidence_adapter import adapt_evidence  # noqa: E402
from mininode_api.web_inspector.models import (  # noqa: E402
    CheckboxEvidence, ContactEvidence, CookieEvidence, EvidenceContract,
    FieldEvidence, FormEvidence, InspectionEvidence, LinkEvidence, PageEvidence,
    TargetEvidence, TransportEvidence,
)


def contract(*, links=None, pages=None, forms=None, cookies=None, contacts=None,
             final_url="https://example.com/", pages_requested=1, pages_analyzed=1,
             errors=None, transport=None, limited=False):
    return EvidenceContract(
        target=TargetEvidence("https://example.com/", final_url, "example.com"),
        inspection=InspectionEvidence(pages_requested, pages_analyzed, limited, errors or []),
        pages=pages if pages is not None else [PageEvidence("https://example.com/", 200, "Inicio", "text/html")],
        transport=transport or TransportEvidence(True, True, None, False),
        links=links or [], forms=forms or [],
        cookies=cookies or CookieEvidence(False, [], False, False),
        contacts=contacts or [],
    )


def form(*, field_type="text", name="message", label="Mensaje", nearby_text="", privacy_links=None, checkboxes=None):
    return FormEvidence(
        "https://example.com/contacto", "https://example.com/send", "post",
        [FieldEvidence(name, field_type, label, False)], checkboxes or [], nearby_text,
        privacy_links or [],
    )


def test_prv001_explicit_text_is_high_confidence():
    link = LinkEvidence("https://example.com/legal", "Política de privacidad", "https://example.com/")
    evidence = adapt_evidence(contract(links=[link]))["PRV-001"]
    assert evidence["policy_visible"] is True
    assert evidence["confidence"] == "high"


def test_prv001_url_only_is_medium_confidence():
    link = LinkEvidence("https://example.com/privacy/", "Legal", "https://example.com/")
    evidence = adapt_evidence(contract(links=[link]))["PRV-001"]
    assert evidence["policy_visible"] is True
    assert evidence["confidence"] == "medium"


def test_prv001_no_policy_after_successful_inspection_is_false():
    assert adapt_evidence(contract())["PRV-001"]["policy_visible"] is False


def test_prv001_insufficient_evidence_is_not_evaluable():
    evidence = adapt_evidence(contract(final_url=None, pages=[], pages_analyzed=0))["PRV-001"]
    assert evidence["technical_error"] is True
    assert "policy_visible" not in evidence
    assert evaluate_control("PRV-001", evidence)["result"] == "not_evaluable"


def test_prv002_obtained_relevant_policy_is_accessible_and_relevant():
    link = LinkEvidence("https://example.com/legal/privacy/", "Política de privacidad", "https://example.com/")
    page = PageEvidence("https://example.com/legal/privacy", 200, "Política de privacidad", "text/html")
    evidence = adapt_evidence(contract(links=[link], pages=[page]))["PRV-002"]
    assert evidence["policy_accessible"] is True
    assert evidence["policy_content_relevant"] is True


def test_prv002_matches_policy_candidate_to_redirected_final_page():
    requested = "https://example.com/legal/privacy/index.html"
    final = "https://example.com/legal/privacy/"
    link = LinkEvidence(requested, "Política de privacidad", "https://example.com/")
    page = PageEvidence(final, 200, "Política de privacidad", "text/html", requested)

    adapted = adapt_evidence(contract(links=[link], pages=[page]))
    evidence = adapted["PRV-002"]

    assert evidence["policy_link_found"] is True
    assert evidence["policy_accessible"] is True
    assert evidence["policy_content_relevant"] is True
    assert evaluate_control("PRV-002", evidence, {
        "PRV-001": evaluate_control("PRV-001", adapted["PRV-001"]),
    })["result"] == "detected"


def test_prv002_attempted_failed_policy_is_inaccessible():
    url = "https://example.com/privacy"
    link = LinkEvidence(url, "Privacy", "https://example.com/")
    evidence = adapt_evidence(contract(links=[link], errors=[{"code": "timeout", "message": "timeout", "url": url}]))["PRV-002"]
    assert evidence["policy_accessible"] is False
    assert evidence["policy_content_relevant"] is False


def test_prv002_generic_success_does_not_make_content_relevant():
    # The candidate text is intentionally empty; URL detection establishes the link,
    # while a generic title alone cannot establish relevance beyond URL evidence.
    link = LinkEvidence("https://example.com/privacy", "", "https://example.com/")
    page = PageEvidence("https://example.com/privacy", 200, "Inicio", "text/html")
    evidence = adapt_evidence(contract(links=[link], pages=[page]))["PRV-002"]
    assert evidence["policy_accessible"] is True
    assert evidence["policy_content_relevant"] is False


def test_prv002_uninspected_policy_does_not_fake_inaccessibility():
    link = LinkEvidence("https://example.com/privacy", "Privacy", "https://example.com/")
    evidence = adapt_evidence(contract(links=[link]))["PRV-002"]
    assert evidence["technical_error"] is True
    assert "policy_accessible" not in evidence


@pytest.mark.parametrize(
    ("field_type", "name", "label"),
    [
        ("email", "value", ""), ("tel", "value", ""), ("textarea", "value", ""),
        ("text", "value", "nombre"), ("text", "value", "correo electrónico"),
        ("text", "value", "e-mail"), ("text", "value", "celular"),
        ("text", "value", "fono"), ("text", "value", "comuna"),
        ("text", "value", "país"), ("text", "value", "pais"),
        ("text", "value", "CORREO ELECTRÓNICO"), ("text", "value", "Teléfono"),
        ("text", "value", "PAÍS"), ("text", "value", "E-MAIL"),
    ],
)
def test_prv101_detects_personal_fields(field_type, name, label):
    assert adapt_evidence(contract(forms=[form(field_type=field_type, name=name, label=label)]))["PRV-101"]["personal_data_form"] is True


def test_prv101_name_identifier_is_medium_confidence():
    evidence = adapt_evidence(contract(forms=[form(name="company", label="")]))["PRV-101"]
    assert evidence == {"confidence": "medium", "personal_data_form": True}


def test_prv101_technical_only_form_is_not_personal():
    assert adapt_evidence(contract(forms=[form(field_type="hidden", name="csrf", label="")]))["PRV-101"]["personal_data_form"] is False


def test_personal_form_trace_uses_only_inspected_final_page_and_sanitizes_url():
    source = "https://example.com/contact?email=test@example.com#form"
    traced_form = FormEvidence(
        source, "https://example.com/send", "post",
        [FieldEvidence("email", "email", "Correo", True)], [], "", [],
    )
    page = PageEvidence(source, 200, "Contacto", "text/html")

    adapted = adapt_evidence(contract(forms=[traced_form], pages=[page]))

    assert adapted["PRV-101"]["source_urls"] == ["https://example.com/contact"]
    assert adapted["PRV-104"]["source_urls"] == ["https://example.com/contact"]
    assert "email" not in repr(adapted)
    assert "#form" not in repr(adapted)


def test_personal_form_trace_is_deterministic_for_multiple_inspected_pages():
    sources = ["https://example.com/z-contact", "https://example.com/a-contact"]
    forms = [
        FormEvidence(
            source, source, "post",
            [FieldEvidence("email", "email", "Correo", True)], [], "", [],
        )
        for source in sources
    ]
    pages = [PageEvidence(source, 200, "Contacto", "text/html") for source in sources]

    evidence = adapt_evidence(contract(forms=forms, pages=pages))["PRV-104"]

    assert evidence["source_urls"] == [
        "https://example.com/a-contact",
        "https://example.com/z-contact",
    ]


def test_personal_form_trace_supports_home_and_rejects_uninspected_source():
    home_form = FormEvidence(
        "https://example.com/", "https://example.com/send", "post",
        [FieldEvidence("email", "email", "Correo", True)], [], "", [],
    )
    invented_form = FormEvidence(
        "https://example.com/not-inspected", "https://example.com/send", "post",
        [FieldEvidence("email", "email", "Correo", True)], [], "", [],
    )

    traced = adapt_evidence(contract(forms=[home_form]))["PRV-101"]
    untraced = adapt_evidence(contract(forms=[invented_form]))["PRV-101"]

    assert traced["source_urls"] == ["https://example.com/"]
    assert "source_urls" not in untraced


def test_personal_form_trace_never_exposes_userinfo_or_ip_literal():
    credentialed = "https://user:secret@example.com/contact"
    pinned_ip = "https://203.0.113.10/contact"
    forms = [
        FormEvidence(
            source, source, "post",
            [FieldEvidence("email", "email", "Correo", True)], [], "", [],
        )
        for source in (credentialed, pinned_ip)
    ]
    pages = [
        PageEvidence(source, 200, "Contacto", "text/html")
        for source in (credentialed, pinned_ip)
    ]

    evidence = adapt_evidence(contract(forms=forms, pages=pages))["PRV-104"]

    assert evidence["source_urls"] == ["https://example.com/contact"]
    assert "user" not in repr(evidence)
    assert "secret" not in repr(evidence)
    assert "203.0.113.10" not in repr(evidence)


def test_prv104_maps_privacy_link_and_information():
    privacy_link = LinkEvidence("https://example.com/privacy", "Privacy", "https://example.com/contacto")
    evidence = adapt_evidence(contract(forms=[form(field_type="email", privacy_links=[privacy_link])]))["PRV-104"]
    assert evidence["privacy_link"] is True
    assert evidence["privacy_information"] is True
    assert evidence["information_complete"] is False


def test_prv104_maps_nearby_privacy_information():
    evidence = adapt_evidence(contract(forms=[form(field_type="email", nearby_text="Tratamiento de datos personales")]))["PRV-104"]
    assert evidence["privacy_information"] is True


def test_prv104_requires_explicit_consent_checkbox_text():
    explicit = form(field_type="email", checkboxes=[CheckboxEvidence("privacy", "Acepto la política de privacidad")])
    generic = form(field_type="email", checkboxes=[CheckboxEvidence("news", "Quiero recibir novedades")])
    explicit_evidence = adapt_evidence(contract(forms=[explicit]))["PRV-104"]
    generic_evidence = adapt_evidence(contract(forms=[generic]))["PRV-104"]
    assert explicit_evidence["consent_mechanism"] is True
    assert explicit_evidence["consent_required"] is True
    assert generic_evidence["consent_mechanism"] is False
    assert generic_evidence["privacy_information"] is False


def test_prv104_is_not_applicable_when_no_personal_forms():
    adapted = adapt_evidence(contract())
    previous = {"PRV-101": evaluate_control("PRV-101", adapted["PRV-101"])}
    assert evaluate_control("PRV-104", adapted["PRV-104"], previous)["result"] == "not_applicable"


def test_prv201_maps_minimized_cookie_observations():
    evidence = adapt_evidence(contract(cookies=CookieEvidence(True, ["session"], True, True)))["PRV-201"]
    assert evidence["relevant_cookies"] is True
    assert evidence["cookie_banner"] is True
    assert evidence["cookie_information"] is True
    assert evidence["preference_mechanism"] is True
    assert "session" not in repr(evidence)


def test_prv201_sufficient_inspection_without_cookies_is_not_applicable():
    evidence = adapt_evidence(contract())["PRV-201"]
    assert evidence["relevant_cookies"] is False
    assert evaluate_control("PRV-201", evidence)["result"] == "not_applicable"


def test_prv201_insufficient_inspection_is_not_evaluable():
    evidence = adapt_evidence(contract(final_url=None, pages=[], pages_analyzed=0))["PRV-201"]
    assert evaluate_control("PRV-201", evidence)["result"] == "not_evaluable"


@pytest.mark.parametrize("contact", [ContactEvidence("https://example.com", email="a@example.com"), ContactEvidence("https://example.com", phone="+56 2 1234 5678")])
def test_prv301_detects_explicit_contact(contact):
    evidence = adapt_evidence(contract(contacts=[contact]))["PRV-301"]
    assert evidence == {"confidence": "high", "contact_channel_visible": True}
    assert evaluate_control("PRV-301", evidence)["result"] == "detected"


def test_prv301_detects_contact_page_form():
    contact_form = FormEvidence(
        "https://example.com/contact/", "https://example.com/contact/send", "post",
        [
            FieldEvidence("name", "text", "Nombre", True),
            FieldEvidence("email", "email", "Email", True),
            FieldEvidence("message", "textarea", "Mensaje", True),
        ], [], "Nombre Email Mensaje", [],
    )
    page = PageEvidence("https://example.com/contact/", 200, "Contacto — Mininode", "text/html")

    evidence = adapt_evidence(contract(forms=[contact_form], pages=[page]))["PRV-301"]

    assert evidence["contact_channel_visible"] is True
    assert evaluate_control("PRV-301", evidence)["result"] == "detected"


@pytest.mark.parametrize(
    "source_url,title,fields",
    [
        (
            "https://example.com/login/", "Iniciar sesión",
            [FieldEvidence("email", "email", "Email", True), FieldEvidence("password", "password", "Contraseña", True)],
        ),
        (
            "https://example.com/newsletter/", "Newsletter",
            [FieldEvidence("email", "email", "Email", True)],
        ),
    ],
)
def test_prv301_does_not_treat_unrelated_forms_as_contact(source_url, title, fields):
    unrelated = FormEvidence(source_url, source_url, "post", fields, [], title, [])
    page = PageEvidence(source_url, 200, title, "text/html")

    evidence = adapt_evidence(contract(forms=[unrelated], pages=[page]))["PRV-301"]

    assert evidence["contact_channel_visible"] is False
    assert evaluate_control("PRV-301", evidence)["result"] == "not_detected"


def test_prv301_distinguishes_absence_from_insufficient_evidence():
    absent = adapt_evidence(contract())["PRV-301"]
    assert absent["contact_channel_visible"] is False
    assert evaluate_control("PRV-301", absent)["result"] == "not_detected"
    failed = adapt_evidence(contract(final_url=None, pages=[], pages_analyzed=0))["PRV-301"]
    assert failed["technical_error"] is True
    assert "contact_channel_visible" not in failed


def test_prv501_maps_target_transport_only_and_preserves_mixed_content():
    transport = TransportEvidence(True, True, None, True)
    evidence = adapt_evidence(contract(transport=transport))["PRV-501"]
    assert evidence == {"https": True, "tls_valid": True, "mixed_content": True, "inconsistent_redirects": False, "confidence": "high"}


@pytest.mark.parametrize("transport", [TransportEvidence(None, None, None, None), TransportEvidence(True, None, None, False)])
def test_prv501_missing_target_transport_is_technical_error(transport):
    evidence = adapt_evidence(contract(transport=transport))["PRV-501"]
    assert evidence["technical_error"] is True
    assert evaluate_control("PRV-501", evidence)["result"] == "not_evaluable"
