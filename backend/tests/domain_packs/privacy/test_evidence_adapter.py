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


def test_prv003_same_site_policy_is_own():
    link = LinkEvidence("https://example.com/privacy", "Privacidad", "https://example.com/")
    evidence = adapt_evidence(contract(links=[link]))["PRV-003"]
    assert evidence["policy_attribution"] == "own"
    assert evaluate_control("PRV-003", evidence)["result"] == "detected"


@pytest.mark.parametrize("url", [
    "https://hcaptcha.com/privacy",
    "https://www.google.com/policies/privacy/",
])
def test_prv003_known_provider_general_policy_is_third_party_despite_anchor(url):
    link = LinkEvidence(
        url, "Política de privacidad utilizada por Example", "https://example.com/"
    )
    evidence = adapt_evidence(contract(links=[link]))["PRV-003"]
    assert evidence["policy_attribution"] == "third_party"
    assert evidence["attribution_signals"] == ["known_provider_general_policy"]
    assert evaluate_control("PRV-003", evidence)["result"] == "not_detected"


def test_prv003_external_document_with_clear_attribution_is_own():
    url = "https://policies.example.net/customer/privacy"
    link = LinkEvidence(url, "Privacidad", "https://example.com/")
    page = PageEvidence(
        url, 200, "Política de privacidad", "text/html", visible_text=(
            "Esta política de privacidad describe el tratamiento de datos de Example."
        )
    )
    evidence = adapt_evidence(contract(links=[link], pages=[page]))["PRV-003"]
    assert evidence["policy_attribution"] == "own"
    assert evaluate_control("PRV-003", evidence)["result"] == "detected"


def test_prv003_external_document_without_clear_attribution_is_partial():
    url = "https://policies.example.net/privacy"
    link = LinkEvidence(url, "Privacidad", "https://example.com/")
    page = PageEvidence(url, 200, "Política de privacidad", "text/html")
    evidence = adapt_evidence(contract(links=[link], pages=[page]))["PRV-003"]
    assert evidence["policy_attribution"] == "ambiguous"
    assert evaluate_control("PRV-003", evidence)["result"] == "partial"


def test_prv003_no_policy_is_not_detected_and_failed_inspection_is_not_evaluable():
    absent = adapt_evidence(contract())["PRV-003"]
    failed = adapt_evidence(contract(final_url=None, pages=[], pages_analyzed=0))["PRV-003"]
    assert evaluate_control("PRV-003", absent)["result"] == "not_detected"
    assert evaluate_control("PRV-003", failed)["result"] == "not_evaluable"


@pytest.mark.parametrize(
    ("visible_text", "expected"),
    [
        ("Esta política corresponde a Example SpA.", "detected"),
        ("Esta política describe cómo nuestra organización trata los datos.", "partial"),
        ("Esta política describe el tratamiento de datos personales.", "not_detected"),
    ],
)
def test_prv005_identifies_responsible_in_selected_policy(visible_text, expected):
    url = "https://example.com/privacy"
    link = LinkEvidence(url, "Privacidad", "https://example.com/")
    page = PageEvidence(
        url, 200, "Política de privacidad", "text/html", visible_text=visible_text
    )
    adapted = adapt_evidence(contract(links=[link], pages=[page]))
    prv003 = evaluate_control("PRV-003", adapted["PRV-003"])

    result = evaluate_control("PRV-005", adapted["PRV-005"], {"PRV-003": prv003})

    assert result["result"] == expected
    assert adapted["PRV-005"]["source_urls"] == [url]


def test_prv005_gate_follows_prv003_without_cascade_penalty():
    evidence = {"responsible_identification": "none", "confidence": "high"}
    assert evaluate_control(
        "PRV-005", evidence, {"PRV-003": "not_detected"}
    )["result"] == "not_applicable"
    assert evaluate_control(
        "PRV-005", evidence, {"PRV-003": "not_evaluable"}
    )["result"] == "not_evaluable"


def test_prv005_uninspected_selected_policy_is_not_evaluable():
    link = LinkEvidence(
        "https://example.com/privacy", "Privacidad", "https://example.com/"
    )
    adapted = adapt_evidence(contract(links=[link]))
    prv003 = evaluate_control("PRV-003", adapted["PRV-003"])

    result = evaluate_control("PRV-005", adapted["PRV-005"], {"PRV-003": prv003})

    assert result["result"] == "not_evaluable"


def test_prv005_uses_own_policy_selected_after_provider_candidate():
    own_url = "https://example.com/privacy"
    links = [
        LinkEvidence("https://hcaptcha.com/privacy", "Privacy", "https://example.com/"),
        LinkEvidence(own_url, "Política de privacidad", "https://example.com/"),
    ]
    pages = [
        PageEvidence(
            "https://hcaptcha.com/privacy", 200, "Privacy", "text/html",
            visible_text="hCaptcha is operated by Intuition Machines, Inc.",
        ),
        PageEvidence(
            own_url, 200, "Política de privacidad", "text/html",
            visible_text="Example SpA es responsable de este sitio.",
        ),
    ]
    adapted = adapt_evidence(contract(links=links, pages=pages))
    prv003 = evaluate_control("PRV-003", adapted["PRV-003"])
    result = evaluate_control("PRV-005", adapted["PRV-005"], {"PRV-003": prv003})

    assert prv003["result"] == "detected"
    assert result["result"] == "detected"
    assert adapted["PRV-005"]["source_urls"] == [own_url]


@pytest.mark.parametrize(
    ("visible_text", "expected"),
    [
        ("Para ejercer sus derechos sobre datos personales escriba a privacidad@example.com.", "detected"),
        ("Consultas: contacto@example.com.", "partial"),
        ("Esta política describe el tratamiento de datos personales.", "not_detected"),
    ],
)
def test_prv006_classifies_channel_only_in_selected_policy(visible_text, expected):
    url = "https://example.com/privacy"
    link = LinkEvidence(url, "Privacidad", "https://example.com/")
    page = PageEvidence(url, 200, "Política de privacidad", "text/html", visible_text=visible_text)
    adapted = adapt_evidence(contract(links=[link], pages=[page]))
    prv003 = evaluate_control("PRV-003", adapted["PRV-003"])

    result = evaluate_control("PRV-006", adapted["PRV-006"], {"PRV-003": prv003})

    assert result["result"] == expected
    assert adapted["PRV-006"]["source_urls"] == [url]


def test_prv006_gate_follows_prv003_without_cascade_penalty():
    evidence = {"rights_channel": "none", "confidence": "high"}
    assert evaluate_control("PRV-006", evidence, {"PRV-003": "not_detected"})["result"] == "not_applicable"
    assert evaluate_control("PRV-006", evidence, {"PRV-003": "not_evaluable"})["result"] == "not_evaluable"


def test_prv006_does_not_reuse_general_contact_and_uses_policy_after_provider():
    own_url = "https://example.com/privacy"
    links = [
        LinkEvidence("https://hcaptcha.com/privacy", "Privacy", "https://example.com/"),
        LinkEvidence(own_url, "Política de privacidad", "https://example.com/"),
    ]
    pages = [
        PageEvidence("https://hcaptcha.com/privacy", 200, "Privacy", "text/html", visible_text="Privacy requests: privacy@hcaptcha.com"),
        PageEvidence(own_url, 200, "Política de privacidad", "text/html", visible_text="Información sobre tratamiento de datos."),
    ]
    contact = ContactEvidence("https://example.com/contact", email="general@example.com")
    adapted = adapt_evidence(contract(links=links, pages=pages, contacts=[contact]))
    prv003 = evaluate_control("PRV-003", adapted["PRV-003"])

    result = evaluate_control("PRV-006", adapted["PRV-006"], {"PRV-003": prv003})

    assert result["result"] == "not_detected"
    assert adapted["PRV-006"]["source_urls"] == [own_url]
    assert evaluate_control("PRV-301", adapted["PRV-301"])["result"] == "detected"


@pytest.mark.parametrize(
    ("visible_text", "expected"),
    [
        ("Tratamos su nombre, correo electrónico y teléfono.", "detected"),
        ("Tratamos sus datos personales.", "partial"),
        ("Esta política explica nuestras prácticas de privacidad.", "not_detected"),
    ],
)
def test_prv007_classifies_categories_only_in_selected_policy(visible_text, expected):
    url = "https://example.com/privacy"
    link = LinkEvidence(url, "Privacidad", "https://example.com/")
    page = PageEvidence(url, 200, "Política de privacidad", "text/html", visible_text=visible_text)
    adapted = adapt_evidence(contract(links=[link], pages=[page]))
    prv003 = evaluate_control("PRV-003", adapted["PRV-003"])

    result = evaluate_control("PRV-007", adapted["PRV-007"], {"PRV-003": prv003})

    assert result["result"] == expected
    assert adapted["PRV-007"]["source_urls"] == [url]


def test_prv007_gate_follows_prv003_without_cascade_penalty():
    evidence = {"data_categories": "none", "confidence": "high"}
    assert evaluate_control("PRV-007", evidence, {"PRV-003": "not_detected"})["result"] == "not_applicable"
    assert evaluate_control("PRV-007", evidence, {"PRV-003": "not_evaluable"})["result"] == "not_evaluable"


def test_prv007_uses_own_policy_selected_after_provider_candidate():
    own_url = "https://example.com/privacy"
    links = [
        LinkEvidence("https://hcaptcha.com/privacy", "Privacy", "https://example.com/"),
        LinkEvidence(own_url, "Política de privacidad", "https://example.com/"),
    ]
    pages = [
        PageEvidence("https://hcaptcha.com/privacy", 200, "Privacy", "text/html", visible_text="We collect names and email addresses."),
        PageEvidence(own_url, 200, "Política de privacidad", "text/html", visible_text="Tratamos datos personales."),
    ]
    adapted = adapt_evidence(contract(links=links, pages=pages))
    prv003 = evaluate_control("PRV-003", adapted["PRV-003"])

    result = evaluate_control("PRV-007", adapted["PRV-007"], {"PRV-003": prv003})

    assert result["result"] == "partial"
    assert adapted["PRV-007"]["source_urls"] == [own_url]


@pytest.mark.parametrize(
    ("visible_text", "expected"),
    [
        ("Usamos sus datos para responder consultas.", "detected"),
        ("Tratamos datos para gestionar cuentas, procesar pagos y prestar servicios.", "detected"),
        ("Tratamos sus datos personales.", "partial"),
        ("Esta política explica nuestras prácticas de privacidad.", "not_detected"),
    ],
)
def test_prv008_classifies_purposes_only_in_selected_policy(visible_text, expected):
    url = "https://example.com/privacy"
    link = LinkEvidence(url, "Privacidad", "https://example.com/")
    page = PageEvidence(url, 200, "Política de privacidad", "text/html", visible_text=visible_text)
    adapted = adapt_evidence(contract(links=[link], pages=[page]))
    prv003 = evaluate_control("PRV-003", adapted["PRV-003"])

    result = evaluate_control("PRV-008", adapted["PRV-008"], {"PRV-003": prv003})

    assert result["result"] == expected
    assert adapted["PRV-008"]["source_urls"] == [url]


def test_prv008_gate_follows_prv003_without_cascade_penalty():
    evidence = {"processing_purposes": "none", "confidence": "high"}
    assert evaluate_control("PRV-008", evidence, {"PRV-003": "not_detected"})["result"] == "not_applicable"
    assert evaluate_control("PRV-008", evidence, {"PRV-003": "not_evaluable"})["result"] == "not_evaluable"


def test_prv008_uses_own_policy_selected_after_provider_candidate():
    own_url = "https://example.com/privacy"
    links = [
        LinkEvidence("https://hcaptcha.com/privacy", "Privacy", "https://example.com/"),
        LinkEvidence(own_url, "Política de privacidad", "https://example.com/"),
    ]
    pages = [
        PageEvidence("https://hcaptcha.com/privacy", 200, "Privacy", "text/html", visible_text="We process data to prevent fraud."),
        PageEvidence(own_url, 200, "Política de privacidad", "text/html", visible_text="Tratamos sus datos personales."),
    ]
    adapted = adapt_evidence(contract(links=links, pages=pages))
    prv003 = evaluate_control("PRV-003", adapted["PRV-003"])

    result = evaluate_control("PRV-008", adapted["PRV-008"], {"PRV-003": prv003})

    assert result["result"] == "partial"
    assert adapted["PRV-008"]["source_urls"] == [own_url]


@pytest.mark.parametrize(
    ("visible_text", "expected"),
    [
        ("Puede ejercer sus derechos de acceso, rectificación y eliminación.", "detected"),
        ("Derechos del titular: puede solicitar el acceso a sus datos.", "detected"),
        ("Puede solicitar la eliminación de sus datos.", "partial"),
        ("Contáctenos para ejercer sus derechos.", "partial"),
        ("Esta política explica nuestras prácticas de privacidad.", "not_detected"),
    ],
)
def test_prv011_classifies_rights_only_in_selected_policy(visible_text, expected):
    url = "https://example.com/privacy"
    link = LinkEvidence(url, "Privacidad", "https://example.com/")
    page = PageEvidence(url, 200, "Política de privacidad", "text/html", visible_text=visible_text)
    adapted = adapt_evidence(contract(links=[link], pages=[page]))
    prv003 = evaluate_control("PRV-003", adapted["PRV-003"])

    result = evaluate_control("PRV-011", adapted["PRV-011"], {"PRV-003": prv003})

    assert result["result"] == expected
    assert adapted["PRV-011"]["source_urls"] == [url]


def test_prv011_gate_follows_prv003_without_cascade_penalty():
    evidence = {"data_subject_rights": "none", "confidence": "high"}
    assert evaluate_control("PRV-011", evidence, {"PRV-003": "not_detected"})["result"] == "not_applicable"
    assert evaluate_control("PRV-011", evidence, {"PRV-003": "not_evaluable"})["result"] == "not_evaluable"


@pytest.mark.parametrize(
    ("visible_text", "expected_evidence", "expected_result"),
    [
        ("No compartimos datos personales con terceros.", "explicit_none", "detected"),
        ("We do not share personal data with third parties.", "explicit_none", "detected"),
        ("We don't disclose personal information to third parties.", "explicit_none", "detected"),
        ("Podemos compartir información con terceros.", "generic", "partial"),
        ("Compartimos datos con proveedores de servicios de pago y hosting.", "explicit", "detected"),
        ("We disclose personal data to service providers and processors.", "explicit", "detected"),
        (
            "En general no compartimos datos con terceros. Podemos compartirlos con proveedores de pago.",
            "explicit",
            "detected",
        ),
        ("Nuestros proveedores ofrecen servicios. No vendemos datos.", "none", "not_detected"),
        ("Esta política explica nuestras prácticas de privacidad.", "none", "not_detected"),
    ],
)
def test_prv010_classifies_recipients_only_in_selected_policy(
    visible_text, expected_evidence, expected_result
):
    url = "https://example.com/privacy"
    link = LinkEvidence(url, "Privacidad", "https://example.com/")
    page = PageEvidence(url, 200, "Política de privacidad", "text/html", visible_text=visible_text)
    adapted = adapt_evidence(contract(links=[link], pages=[page]))
    prv003 = evaluate_control("PRV-003", adapted["PRV-003"])

    result = evaluate_control("PRV-010", adapted["PRV-010"], {"PRV-003": prv003})

    assert adapted["PRV-010"]["data_recipients"] == expected_evidence
    assert result["result"] == expected_result
    assert adapted["PRV-010"]["source_urls"] == [url]


def test_prv010_gate_and_missing_selected_document_are_not_penalized():
    evidence = {"data_recipients": "none", "confidence": "high"}
    assert evaluate_control("PRV-010", evidence, {"PRV-003": "not_detected"})["result"] == "not_applicable"
    assert evaluate_control("PRV-010", evidence, {"PRV-003": "not_evaluable"})["result"] == "not_evaluable"

    url = "https://example.com/privacy"
    adapted = adapt_evidence(contract(links=[LinkEvidence(url, "Privacidad", "https://example.com/")]))
    assert adapted["PRV-010"]["source_urls"] == [url]
    assert evaluate_control("PRV-010", adapted["PRV-010"], {"PRV-003": "detected"})["result"] == "not_evaluable"


def test_prv010_uses_only_own_policy_selected_after_hcaptcha_candidate():
    own_url = "https://example.com/privacy"
    links = [
        LinkEvidence("https://hcaptcha.com/privacy", "Privacy", "https://example.com/"),
        LinkEvidence(own_url, "Política de privacidad", "https://example.com/"),
    ]
    pages = [
        PageEvidence("https://hcaptcha.com/privacy", 200, "Privacy", "text/html", visible_text="We disclose data to service providers and processors."),
        PageEvidence(own_url, 200, "Política de privacidad", "text/html", visible_text="Podemos compartir información con terceros."),
    ]
    adapted = adapt_evidence(contract(links=links, pages=pages))
    prv003 = evaluate_control("PRV-003", adapted["PRV-003"])

    result = evaluate_control("PRV-010", adapted["PRV-010"], {"PRV-003": prv003})

    assert result["result"] == "partial"
    assert adapted["PRV-010"]["source_urls"] == [own_url]


def test_prv011_uses_own_policy_selected_after_provider_candidate():
    own_url = "https://example.com/privacy"
    links = [
        LinkEvidence("https://hcaptcha.com/privacy", "Privacy", "https://example.com/"),
        LinkEvidence(own_url, "Política de privacidad", "https://example.com/"),
    ]
    pages = [
        PageEvidence("https://hcaptcha.com/privacy", 200, "Privacy", "text/html", visible_text="You have rights of access, rectification, deletion and portability."),
        PageEvidence(own_url, 200, "Política de privacidad", "text/html", visible_text="Puede ejercer sus derechos."),
    ]
    adapted = adapt_evidence(contract(links=links, pages=pages))
    prv003 = evaluate_control("PRV-003", adapted["PRV-003"])

    result = evaluate_control("PRV-011", adapted["PRV-011"], {"PRV-003": prv003})

    assert result["result"] == "partial"
    assert adapted["PRV-011"]["source_urls"] == [own_url]


@pytest.mark.parametrize(
    ("visible_text", "expected_evidence", "expected_result"),
    [
        ("Conservaremos sus datos durante 12 meses.", "explicit", "detected"),
        ("Los datos se conservarán mientras exista una relación contractual.", "explicit", "detected"),
        ("Conservaremos los datos mientras sean necesarios para prestar el servicio.", "explicit", "detected"),
        ("Los datos se conservarán durante el plazo exigido por la normativa aplicable.", "explicit", "detected"),
        ("We retain personal data for 24 months.", "explicit", "detected"),
        ("We retain your data while your account is active.", "explicit", "detected"),
        ("Conservamos sus datos de forma segura.", "generic", "partial"),
        ("Podemos almacenar información personal.", "generic", "partial"),
        ("Esta política explica nuestras prácticas de privacidad.", "none", "not_detected"),
        ("Eliminaremos sus datos 30 días después de cerrar la cuenta.", "explicit", "detected"),
        ("Podemos eliminar información.", "generic", "partial"),
    ],
)
def test_prv012_classifies_retention_only_in_selected_policy(
    visible_text, expected_evidence, expected_result
):
    url = "https://example.com/privacy"
    link = LinkEvidence(url, "Privacidad", "https://example.com/")
    page = PageEvidence(url, 200, "Política de privacidad", "text/html", visible_text=visible_text)
    adapted = adapt_evidence(contract(links=[link], pages=[page]))
    prv003 = evaluate_control("PRV-003", adapted["PRV-003"])

    result = evaluate_control("PRV-012", adapted["PRV-012"], {"PRV-003": prv003})

    assert adapted["PRV-012"]["data_retention"] == expected_evidence
    assert result["result"] == expected_result
    assert adapted["PRV-012"]["source_urls"] == [url]


def test_prv012_gate_and_missing_selected_document_are_not_penalized():
    evidence = {"data_retention": "none", "confidence": "high"}
    assert evaluate_control("PRV-012", evidence, {"PRV-003": "not_detected"})["result"] == "not_applicable"
    assert evaluate_control("PRV-012", evidence, {"PRV-003": "not_evaluable"})["result"] == "not_evaluable"

    url = "https://example.com/privacy"
    adapted = adapt_evidence(contract(links=[LinkEvidence(url, "Privacidad", "https://example.com/")]))
    assert adapted["PRV-012"]["source_urls"] == [url]
    assert evaluate_control("PRV-012", adapted["PRV-012"], {"PRV-003": "detected"})["result"] == "not_evaluable"


def test_prv012_uses_only_own_policy_selected_after_hcaptcha_candidate():
    own_url = "https://example.com/privacy"
    links = [
        LinkEvidence("https://hcaptcha.com/privacy", "Privacy", "https://example.com/"),
        LinkEvidence(own_url, "Política de privacidad", "https://example.com/"),
    ]
    pages = [
        PageEvidence("https://hcaptcha.com/privacy", 200, "Privacy", "text/html", visible_text="We retain personal data for 24 months."),
        PageEvidence(own_url, 200, "Política de privacidad", "text/html", visible_text="Conservamos sus datos de forma segura."),
    ]
    adapted = adapt_evidence(contract(links=links, pages=pages))
    prv003 = evaluate_control("PRV-003", adapted["PRV-003"])

    result = evaluate_control("PRV-012", adapted["PRV-012"], {"PRV-003": prv003})

    assert result["result"] == "partial"
    assert adapted["PRV-012"]["source_urls"] == [own_url]


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
    assert "test@example.com" not in repr(adapted)
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
    assert evidence["visible_evidence"]["source_url"] == "https://example.com/a-contact"


def test_visible_evidence_uses_known_categories_from_selected_source_only():
    selected = FormEvidence(
        "https://example.com/a-contact?token=secret#form", "https://example.com/send", "post",
        [
            FieldEvidence("full_name", "text", "Persona privada", False),
            FieldEvidence("email", "email", "persona@example.com", True),
            FieldEvidence("message", "textarea", "<b>Mensaje</b>", False),
        ], [], "header: secret", [],
    )
    other = FormEvidence(
        "https://example.com/z-register", "https://example.com/send", "post",
        [FieldEvidence("phone", "tel", "+56 9 1234 5678", False)], [], "", [],
    )
    pages = [
        PageEvidence(selected.source_url, 200, "Contacto", "text/html"),
        PageEvidence(other.source_url, 200, "Registro", "text/html"),
    ]

    adapted = adapt_evidence(contract(forms=[other, selected], pages=pages))
    visible = adapted["PRV-101"]["visible_evidence"]

    assert visible == {
        "type": "personal_data_form",
        "fields": ["email", "message", "name"],
        "privacy_link": False,
        "privacy_information": False,
        "consent_mechanism": False,
        "source_url": "https://example.com/a-contact",
    }
    serialized = repr(visible)
    for secret in ("persona@example.com", "+56 9 1234 5678", "<b>", "secret", "?", "#"):
        assert secret not in serialized


def test_visible_evidence_summaries_are_conservative_and_control_scoped():
    source = "https://example.com/contact"
    page = PageEvidence(source, 200, "Contacto", "text/html")
    privacy_link = LinkEvidence("https://example.com/privacy", "Privacidad", source)
    known = FormEvidence(
        source, source, "post",
        [FieldEvidence("email", "email", "", False), FieldEvidence("message", "textarea", "", False)],
        [], "", [privacy_link],
    )
    adapted = adapt_evidence(contract(forms=[known], pages=[page]))

    prv101 = evaluate_control("PRV-101", adapted["PRV-101"])
    prv104 = evaluate_control("PRV-104", adapted["PRV-104"], {"PRV-101": prv101})
    assert prv101["evidence_summary"] == "Formulario que solicita correo electrónico y mensaje."
    assert prv104["evidence_summary"] == "Se detectó un formulario con un enlace visible relacionado con privacidad."
    assert prv101["source_url"] == adapted["PRV-101"]["visible_evidence"]["source_url"]

    unknown = FormEvidence(
        source, source, "post", [FieldEvidence("customer", "text", "Correo", False)], [], "", [],
    )
    unknown_evidence = adapt_evidence(contract(forms=[unknown], pages=[page]))["PRV-101"]
    assert evaluate_control("PRV-101", unknown_evidence)["evidence_summary"] == (
        "Se detectó un formulario que solicita datos potencialmente personales."
    )

    for code in ("PRV-001", "PRV-002", "PRV-201", "PRV-301", "PRV-501"):
        assert "evidence_summary" not in evaluate_control(code, adapted[code])


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

@pytest.mark.parametrize("visible_text", [
    "Última actualización: 15 de marzo de 2026",
    "Actualizado el 15/03/2026",
    "Vigente desde enero de 2026",
    "Versión 2.1",
    "Last updated: March 15, 2026",
    "Effective date: January 1, 2026",
    "Privacy Policy v3",
])
def test_prv004_detects_contextual_date_or_version(visible_text):
    url = "https://example.com/privacy"
    link = LinkEvidence(url, "Política de privacidad", "https://example.com/")
    page = PageEvidence(url, 200, "Política de privacidad", "text/html", visible_text=visible_text)
    adapted = adapt_evidence(contract(links=[link], pages=[page]))
    prv003 = evaluate_control("PRV-003", adapted["PRV-003"])
    result = evaluate_control("PRV-004", adapted["PRV-004"], {"PRV-003": prv003})
    assert result["result"] == "detected"
    assert adapted["PRV-004"]["source_urls"] == [url]


@pytest.mark.parametrize("visible_text", [
    "© 2026 Example SpA",
    "Esta política explica cómo tratamos sus datos personales.",
    "15/03/2026",
])
def test_prv004_does_not_treat_uncontextualized_dates_as_document_dates(visible_text):
    url = "https://example.com/privacy"
    link = LinkEvidence(url, "Política de privacidad", "https://example.com/")
    page = PageEvidence(url, 200, "Política de privacidad", "text/html", visible_text=visible_text)
    adapted = adapt_evidence(contract(links=[link], pages=[page]))
    assert evaluate_control("PRV-004", adapted["PRV-004"], {"PRV-003": "detected"})["result"] == "not_detected"


def test_prv004_uses_gate_and_requires_selected_document():
    evidence = {"policy_document_reference": "none", "confidence": "high"}
    assert evaluate_control("PRV-004", evidence, {"PRV-003": "not_detected"})["result"] == "not_applicable"
    assert evaluate_control("PRV-004", evidence, {"PRV-003": "not_evaluable"})["result"] == "not_evaluable"
    url = "https://example.com/privacy"
    adapted = adapt_evidence(contract(
        links=[LinkEvidence(url, "Privacidad", "https://example.com/")]
    ))
    assert evaluate_control("PRV-004", adapted["PRV-004"], {"PRV-003": "detected"})["result"] == "not_evaluable"


@pytest.mark.parametrize(("provider_text", "own_text", "expected"), [
    ("Last updated: March 15, 2026", "Política sobre datos personales.", "not_detected"),
    ("Privacy policy without a date.", "Última actualización: 2026-01-10", "detected"),
])
def test_prv004_uses_only_policy_selected_after_hcaptcha(provider_text, own_text, expected):
    provider_url = "https://www.hcaptcha.com/privacy"
    own_url = "https://example.com/privacy"
    links = [
        LinkEvidence(provider_url, "Privacy", "https://example.com/"),
        LinkEvidence(own_url, "Política de privacidad", "https://example.com/"),
    ]
    pages = [
        PageEvidence(provider_url, 200, "hCaptcha Privacy", "text/html", visible_text=provider_text),
        PageEvidence(own_url, 200, "Política de privacidad", "text/html", visible_text=own_text),
    ]
    adapted = adapt_evidence(contract(links=links, pages=pages))
    prv003 = evaluate_control("PRV-003", adapted["PRV-003"])
    result = evaluate_control("PRV-004", adapted["PRV-004"], {"PRV-003": prv003})
    assert result["result"] == expected
    assert adapted["PRV-004"]["source_urls"] == [own_url]
