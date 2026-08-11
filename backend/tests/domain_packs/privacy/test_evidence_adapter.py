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
    assert adapt_evidence(contract(contacts=[contact]))["PRV-301"] == {"confidence": "high", "contact_channel_visible": True}


def test_prv301_distinguishes_absence_from_insufficient_evidence():
    assert adapt_evidence(contract())["PRV-301"]["contact_channel_visible"] is False
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
