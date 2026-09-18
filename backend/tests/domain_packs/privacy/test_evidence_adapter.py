import sys
from pathlib import Path

import pytest

BACKEND_SRC = Path(__file__).resolve().parents[3] / "src"
sys.path.insert(0, str(BACKEND_SRC))

from mininode_api.domain_packs.privacy.evaluator import evaluate_control  # noqa: E402
from mininode_api.domain_packs.privacy.evidence_adapter import adapt_evidence  # noqa: E402
from mininode_api.web_inspector.extractor import extract_page  # noqa: E402
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


def form(*, field_type="text", name="message", label="Mensaje", nearby_text="", privacy_links=None, checkboxes=None,
         heading=None, legend=None, introductory_text=None, submit_text=None):
    return FormEvidence(
        "https://example.com/contacto", "https://example.com/send", "post",
        [FieldEvidence(name, field_type, label, False)], checkboxes or [], nearby_text,
        privacy_links or [], heading, legend, introductory_text, submit_text,
    )


def test_internal_form_context_does_not_change_existing_privacy_controls():
    baseline = form(field_type="email", nearby_text="Política de privacidad")
    extended = FormEvidence(
        baseline.source_url, baseline.action, baseline.method, baseline.fields,
        baseline.checkboxes, baseline.nearby_text, baseline.privacy_links,
        "Solicita una cotización", "Datos de contacto",
        "Déjanos tus datos para preparar la propuesta.", "Solicitar cotización",
    )

    baseline_adapted = adapt_evidence(contract(forms=[baseline]))
    extended_adapted = adapt_evidence(contract(forms=[extended]))

    for control_id in ("PRV-101", "PRV-102", "PRV-104"):
        assert evaluate_control(control_id, extended_adapted[control_id]) == evaluate_control(
            control_id, baseline_adapted[control_id]
        )


@pytest.mark.parametrize(("kwargs", "purpose", "result"), [
    ({"heading": "Solicita una cotización"}, "concrete", "detected"),
    ({"introductory_text": "Déjanos tus datos y te contactaremos para preparar una cotización."}, "concrete", "detected"),
    ({"heading": "Request a demo"}, "concrete", "detected"),
    ({"heading": "Contacto"}, "generic", "partial"),
    ({"submit_text": "Enviar"}, "generic", "partial"),
    ({"submit_text": "Continuar"}, "generic", "partial"),
    ({"introductory_text": "All fields required", "submit_text": "Sending"}, "none", "not_detected"),
    ({}, "unknown", "not_evaluable"),
    ({"heading": "Newsletter", "submit_text": "Subscribe"}, "concrete", "detected"),
    ({"legend": "Contact us Form"}, "generic", "partial"),
    ({"legend": "Footer - Get In Touch"}, "generic", "partial"),
    ({"heading": "Contact form"}, "generic", "partial"),
    ({"heading": "Formulario de contacto"}, "generic", "partial"),
    ({"introductory_text": "Complete the form to request a quote"}, "concrete", "detected"),
    ({"introductory_text": "Your message will be reviewed by our team"}, "unknown", "not_evaluable"),
    ({"submit_text": "Send request for a demo"}, "concrete", "detected"),
    ({"submit_text": "Hablemos de tu proyecto"}, "concrete", "detected"),
    ({"submit_text": "Conversemos sobre el proyecto"}, "concrete", "detected"),
    ({"submit_text": "Conversemos"}, "generic", "partial"),
    ({"introductory_text": "Completa este formulario y nos pondremos en contacto contigo"}, "concrete", "detected"),
    ({"submit_text": "Escríbenos"}, "generic", "partial"),
    ({"submit_text": "Enviar mensaje"}, "generic", "partial"),
    ({"submit_text": "Send us a message"}, "generic", "partial"),
    ({"heading": "14-day free trial", "submit_text": "Try for free"}, "concrete", "detected"),
    ({"heading": "Prueba gratuita", "submit_text": "Empezar"}, "concrete", "detected"),
    ({"submit_text": "Empezar"}, "generic", "partial"),
    ({"submit_text": "Contact"}, "generic", "partial"),
    ({"heading": "Contact sales", "submit_text": "Submit"}, "generic", "partial"),
    ({"legend": "I'm interested in", "submit_text": "Contact"}, "generic", "partial"),
    ({"heading": "Transforma tu futuro digital ahora"}, "unknown", "not_evaluable"),
    ({"submit_text": "Suscríbete ya Enviando"}, "concrete", "detected"),
    ({"submit_text": "We'll get back to you"}, "concrete", "detected"),
    ({"submit_text": "We will contact you"}, "concrete", "detected"),
    ({"submit_text": "We'll contact you"}, "concrete", "detected"),
    ({"introductory_text": "All fields required"}, "none", "not_detected"),
    ({"submit_text": "Sending"}, "none", "not_detected"),
])
def test_prv103_classifies_structured_same_form_purpose(kwargs, purpose, result):
    adapted = adapt_evidence(contract(forms=[form(field_type="email", **kwargs)]))
    assert adapted["PRV-103"]["form_purpose"] == purpose
    assert adapted["PRV-103"]["confidence"] == {
        "concrete": "high", "generic": "medium", "none": "high", "unknown": "low",
    }[purpose]
    assert "source_urls" not in adapted["PRV-103"]
    prv101 = evaluate_control("PRV-101", adapted["PRV-101"])
    assert evaluate_control("PRV-103", adapted["PRV-103"], {"PRV-101": prv101})["result"] == result


def test_prv103_qa7_019_general_help_contact_is_generic():
    adapted = adapt_evidence(contract(forms=[form(
        field_type="email",
        heading="¿Tienes dudas o necesitas ayuda?",
        submit_text="Escríbenos",
    )]))
    assert adapted["PRV-103"]["form_purpose"] == "generic"
    prv101 = evaluate_control("PRV-101", adapted["PRV-101"])
    assert evaluate_control(
        "PRV-103", adapted["PRV-103"], {"PRV-101": prv101}
    )["result"] == "partial"


def test_prv103_does_not_infer_from_nearby_fields_or_privacy_evidence():
    privacy = LinkEvidence("https://example.com/privacy", "Privacidad", "https://example.com/contacto")
    candidate = form(
        field_type="email", name="email", label="Correo electrónico",
        nearby_text="Solicita una cotización", privacy_links=[privacy],
    )
    evidence = adapt_evidence(contract(forms=[candidate]))["PRV-103"]
    assert evidence["form_purpose"] == "unknown"


@pytest.mark.parametrize("text", [
    "Hablemos de tu", "Conversemos sobre el", "Proyecto", "Sales", "Free",
])
def test_prv103_does_not_promote_unrecognized_words_to_concrete(text):
    evidence = adapt_evidence(contract(forms=[form(field_type="email", heading=text)]))["PRV-103"]
    assert evidence["form_purpose"] == "unknown"


@pytest.mark.parametrize("text", ["Contact", "Start", "I'm interested"])
def test_prv103_generic_exact_text_is_never_promoted_to_concrete(text):
    evidence = adapt_evidence(contract(forms=[form(field_type="email", heading=text)]))["PRV-103"]
    assert evidence["form_purpose"] == "generic"


@pytest.mark.parametrize("text", [
    "Create a support ticket",
    "Open support ticket",
    "Submit a support request",
    "Create a case",
    "Our team will follow up",
    "We will reply shortly",
    "We'll respond soon",
    "Try the reporting service for free",
    "Start secure analytics for free",
    "Complete the form to access the research report",
    "Fill out this form to download the guide",
    "Para ver el informe, completa el formulario",
    "Completa este formulario para obtener la guía",
    "Para ver las galerías completas, completa el siguiente formulario",
    "Completa el siguiente formulario para descargar la guía",
    "Selecciona los temas que te interesaría recibir",
    "Selecciona los contenidos que quieres recibir",
    "Elige las comunicaciones que deseas recibir",
    "Select the topics you want to receive",
    "Choose the updates you would like to receive",
    "Recibir temas seleccionados",
    "Recibir contenido y comunicaciones",
    "Recibir información",
    "Receive product information",
    "Evalúa tu experiencia",
    "Evaluate your experience",
    "Provide us feedback",
    "Comparte tu opinión",
    "Tell us what you think",
    "Did you find what you were looking for?",
])
def test_prv103_recognizes_generalized_concrete_purposes(text):
    evidence = adapt_evidence(contract(forms=[form(field_type="email", introductory_text=text)]))["PRV-103"]
    assert evidence["form_purpose"] == "concrete"


@pytest.mark.parametrize("kwargs", [
    {"heading": "Cotización para tu proyecto", "submit_text": "Pedir ahora"},
    {"legend": "Product demonstration", "submit_text": "Get yours"},
    {"heading": "Noticias del producto", "submit_text": "Recibir"},
    {"introductory_text": "Appointment with an advisor", "submit_text": "Book now"},
    {"heading": "How can we help?", "submit_text": "Submit a question"},
])
def test_prv103_combines_bounded_actions_and_results_across_form_context(kwargs):
    evidence = adapt_evidence(contract(forms=[form(field_type="email", **kwargs)]))["PRV-103"]
    assert evidence["form_purpose"] == "concrete"


@pytest.mark.parametrize("text", [
    "Learn about pricing",
    "Request a message",
    "Schedule a call",
    "Latest product news",
])
def test_prv103_does_not_promote_unpaired_or_ambiguous_concepts(text):
    evidence = adapt_evidence(contract(forms=[form(field_type="email", heading=text)]))["PRV-103"]
    assert evidence["form_purpose"] == "unknown"


@pytest.mark.parametrize("text", [
    "Contact our team",
    "Contact the team",
    "Talk to our sales team",
    "Speak with our support team",
    "Contacta a nuestro equipo",
    "Habla con nuestro equipo",
    "Habla con ventas",
])
def test_prv103_recognizes_bounded_team_contact_as_generic(text):
    evidence = adapt_evidence(contract(forms=[form(field_type="email", heading=text)]))["PRV-103"]
    assert evidence["form_purpose"] == "generic"


@pytest.mark.parametrize("text", [
    "Send message", "Talk to ExampleCo", "Connect with us", "Contáctanos",
    "Enviar Formulario", "Confirmar", "SUBSCRIBIRME", "Tell us a bit more",
])
def test_prv103_recognizes_qa3_generalized_generic_purposes(text):
    evidence = adapt_evidence(contract(forms=[form(field_type="email", heading=text)]))["PRV-103"]
    assert evidence["form_purpose"] == "generic"


@pytest.mark.parametrize("text", [
    "Iniciar sesión",
    "Sign in",
    "Access my account",
    "Send my question to technical support",
    "Solicita soporte y envía tu consulta",
    "Free 14-day trial - Get started",
    "Sign up for a free trial",
    "Comienza tu prueba gratis",
])
def test_prv103_recognizes_qa3_generalized_concrete_purposes(text):
    evidence = adapt_evidence(contract(forms=[form(field_type="email", heading=text)]))["PRV-103"]
    assert evidence["form_purpose"] == "concrete"


@pytest.mark.parametrize("text", [
    "team", "support", "help", "question", "account", "cuenta", "free", "gratis",
    "trial", "prueba", "ticket", "free resources", "learn for free",
    "experience", "feedback", "opinion", "content", "information", "topics",
    "Complete the form", "El siguiente formulario", "Selecciona los temas",
    "Temas que te interesan", "select topics", "choose content",
    "interested in topics", "A new path for ambitious organizations",
])
def test_prv103_does_not_promote_isolated_or_unknown_semantic_text(text):
    evidence = adapt_evidence(contract(forms=[form(field_type="email", heading=text)]))["PRV-103"]
    assert evidence["form_purpose"] == "unknown"


@pytest.mark.parametrize("text", ["message", "form"])
def test_prv103_keeps_isolated_form_terms_generic_not_concrete(text):
    evidence = adapt_evidence(contract(forms=[form(field_type="email", heading=text)]))["PRV-103"]
    assert evidence["form_purpose"] == "generic"


@pytest.mark.parametrize("text", [
    "Sending", "Enviando", "Loading", "Cargando", "Previous", "Anterior", "Back",
])
def test_prv103_keeps_operational_states_out_of_generic(text):
    evidence = adapt_evidence(contract(forms=[form(field_type="email", submit_text=text)]))["PRV-103"]
    assert evidence["form_purpose"] == "none"


def test_prv103_keeps_operational_noise_none_and_medium_not_evaluable():
    noise = adapt_evidence(contract(forms=[form(field_type="email", submit_text="Sending")]))
    assert noise["PRV-103"]["form_purpose"] == "none"

    medium = adapt_evidence(contract(forms=[form(name="country", label="", heading="Create a support ticket")]))
    assert medium["PRV-101"]["confidence"] == "medium"
    assert medium["PRV-103"] == {"form_purpose": "unknown", "confidence": "low"}


def test_prv103_exposes_only_sanitized_determining_form_urls():
    forms = [
        form(field_type="email", heading="Request a demo"),
        FormEvidence(
            "https://example.com/support?private=value", "https://example.com/send", "post",
            [FieldEvidence("email", "email", "Email", False)], [], "", [],
            None, None, "All fields required", "Sending",
        ),
    ]
    pages = [
        PageEvidence("https://example.com/contacto", 200, "", "text/html"),
        PageEvidence("https://example.com/support?private=value", 200, "", "text/html"),
    ]
    evidence = adapt_evidence(contract(forms=forms, pages=pages))["PRV-103"]
    assert evidence == {
        "form_purpose": "none", "confidence": "high",
        "source_urls": ["https://example.com/support"],
    }


def test_prv103_medium_only_is_unknown_and_high_ignores_medium():
    medium = form(name="country", label="", submit_text="Chile Argentina Perú")
    medium_only = adapt_evidence(contract(forms=[medium]))
    assert medium_only["PRV-101"]["confidence"] == "medium"
    assert medium_only["PRV-103"] == {"form_purpose": "unknown", "confidence": "low"}

    high = form(field_type="email", heading="Solicita una cotización")
    combined = adapt_evidence(contract(forms=[high, medium]))["PRV-103"]
    assert combined["form_purpose"] == "concrete"


@pytest.mark.parametrize(("other", "expected"), [
    ({"heading": "Request support"}, "concrete"),
    ({"heading": "Contacto"}, "generic"),
    ({"submit_text": "Sending"}, "none"),
    ({}, "unknown"),
])
def test_prv103_conservative_multi_high_precedence(other, expected):
    forms = [
        form(field_type="email", heading="Solicita una cotización"),
        form(field_type="email", **other),
    ]
    assert adapt_evidence(contract(forms=forms))["PRV-103"]["form_purpose"] == expected


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


def test_document_controls_ignore_emol_style_chrome_and_form_noise():
    """Clean policy evidence wins over login/header/footer text."""
    url = "https://example.com/privacy"
    link = LinkEvidence(url, "Política de privacidad", "https://example.com/")
    page = PageEvidence(
        url, 200, "Política de privacidad", "text/html",
        visible_text=(
            "Example SpA es responsable. Nombre Apellido Correo electrónico. "
            "Para ejercer derechos escriba a privacidad@example.com. "
            "Compartimos datos con terceros. Derechos de acceso y rectificación. "
            "Acepto el tratamiento basado en consentimiento y puedo revocarlo."
        ),
        content_text=(
            "Política de privacidad. Tratamos datos personales para prestar el servicio."
        ),
    )

    adapted = adapt_evidence(contract(links=[link], pages=[page]))

    assert adapted["PRV-005"]["responsible_identification"] == "none"
    assert adapted["PRV-006"]["rights_channel"] == "none"
    assert adapted["PRV-007"]["data_categories"] == "generic"
    assert adapted["PRV-010"]["data_recipients"] == "none"
    assert adapted["PRV-011"]["data_subject_rights"] == "none"
    assert adapted["PRV-014"]["consent_basis_declared"] is False


def test_document_controls_keep_edusmart_style_policy_signals_not_footer():
    url = "https://example.com/privacy"
    link = LinkEvidence(url, "Política de privacidad", "https://example.com/")
    page = PageEvidence(
        url, 200, "Política de privacidad", "text/html",
        visible_text="Productos Cursos Contacto oficina@example.com teléfonos y direcciones",
        content_text=(
            "Política de privacidad. Recogemos nombre y correo electrónico para enviar "
            "comunicaciones de newsletter. Aplicamos medidas de seguridad y usamos "
            "cookies. Podemos comunicar los datos a proveedores de servicios."
        ),
    )

    adapted = adapt_evidence(contract(links=[link], pages=[page]))

    assert adapted["PRV-007"]["data_categories"] == "concrete"
    assert adapted["PRV-008"]["processing_purposes"] == "concrete"
    assert adapted["PRV-010"]["data_recipients"] == "explicit"
    assert adapted["PRV-006"]["rights_channel"] == "none"


def test_prv014_detects_late_consent_withdrawal_from_content_text():
    url = "https://example.com/privacy"
    link = LinkEvidence(url, "Política de privacidad", "https://example.com/")
    late = (
        "El tratamiento de sus datos se basa en el consentimiento. "
        "Puede revocar el consentimiento en cualquier momento."
    )
    page = PageEvidence(
        url, 200, "Política de privacidad", "text/html",
        visible_text="Contenido introductorio. " + ("x" * 3970),
        content_text="Contenido introductorio. " + ("x" * 4100) + ". " + late,
    )

    adapted = adapt_evidence(contract(links=[link], pages=[page]))
    result = evaluate_control(
        "PRV-014", adapted["PRV-014"], {"PRV-003": "detected"}
    )

    assert adapted["PRV-014"]["consent_withdrawal"] == "explicit"
    assert result["result"] == "detected"


def test_content_text_does_not_create_policy_when_prv003_did_not_find_one():
    page = PageEvidence(
        "https://example.com/", 200, "Inicio", "text/html",
        content_text="Política de privacidad con consentimiento y revocación.",
    )
    adapted = adapt_evidence(contract(pages=[page]))
    prv003 = evaluate_control("PRV-003", adapted["PRV-003"])

    assert prv003["result"] == "not_detected"
    for code in [f"PRV-{number:03d}" for number in range(4, 15)]:
        assert evaluate_control(code, adapted[code], {"PRV-003": prv003})["result"] == "not_applicable"


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
    ("visible_text", "expected_channel", "expected_result"),
    [
        (
            "Para ejercer sus derechos sobre datos personales escriba a privacidad@example.com.",
            "explicit", "detected",
        ),
        ("Consultas: contacto@example.com.", "generic", "partial"),
        ("Para consultas puede contactarnos al +56 2 1234 5678.", "generic", "partial"),
        ("Recogemos nombre y correo electrónico.", "none", "not_detected"),
        ("Tratamos email y teléfono.", "none", "not_detected"),
        (
            "Datos de contacto: nombre, correo electrónico y teléfono.",
            "none", "not_detected",
        ),
        (
            "Esta política describe el tratamiento de datos personales.",
            "none", "not_detected",
        ),
    ],
)
def test_prv006_classifies_channel_only_in_selected_policy(
    visible_text, expected_channel, expected_result
):
    url = "https://example.com/privacy"
    link = LinkEvidence(url, "Privacidad", "https://example.com/")
    page = PageEvidence(url, 200, "Política de privacidad", "text/html", visible_text=visible_text)
    adapted = adapt_evidence(contract(links=[link], pages=[page]))
    prv003 = evaluate_control("PRV-003", adapted["PRV-003"])

    result = evaluate_control("PRV-006", adapted["PRV-006"], {"PRV-003": prv003})

    assert adapted["PRV-006"]["rights_channel"] == expected_channel
    assert result["result"] == expected_result
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


@pytest.mark.parametrize(("visible_text", "classification", "outcome"), [
    ("Tratamos sus datos sobre la base de su consentimiento.", "explicit", "detected"),
    ("El tratamiento es necesario para la ejecución del contrato.", "explicit", "detected"),
    ("Tratamos sus datos para cumplir una obligación legal.", "explicit", "detected"),
    ("Nuestro interés legítimo constituye una base para determinados tratamientos.", "explicit", "detected"),
    ("We process personal data based on your consent.", "explicit", "detected"),
    ("We process data where necessary to perform a contract.", "explicit", "detected"),
    ("We process data to comply with a legal obligation.", "explicit", "detected"),
    ("We rely on our legitimate interests for this processing.", "explicit", "detected"),
    ("Tratamos sus datos cuando existe una base aplicable.", "generic", "partial"),
    ("We process data where permitted.", "generic", "partial"),
    ("Esta política explica cómo protegemos su información.", "none", "not_detected"),
    ("Puede contratar nuestros servicios en línea.", "none", "not_detected"),
    ("Al continuar acepta el uso de cookies.", "none", "not_detected"),
    ("Tratamos los datos proporcionados con su consentimiento.", "explicit", "detected"),
    ("No utilizamos el interés legítimo como base para tratar sus datos.", "none", "not_detected"),
    ("Tratamos datos con su consentimiento, para ejecutar un contrato y para cumplir obligaciones legales.", "explicit", "detected"),
])
def test_prv009_classifies_only_declared_bases_in_processing_context(
    visible_text, classification, outcome
):
    url = "https://example.com/privacy"
    link = LinkEvidence(url, "Política de privacidad", "https://example.com/")
    page = PageEvidence(url, 200, "Política de privacidad", "text/html", visible_text=visible_text)
    adapted = adapt_evidence(contract(links=[link], pages=[page]))
    prv003 = evaluate_control("PRV-003", adapted["PRV-003"])
    result = evaluate_control("PRV-009", adapted["PRV-009"], {"PRV-003": prv003})

    assert adapted["PRV-009"]["declared_processing_basis"] == classification
    assert adapted["PRV-009"]["source_urls"] == [url]
    assert result["result"] == outcome


def test_prv009_gate_and_missing_selected_document_are_not_penalized():
    evidence = {"declared_processing_basis": "explicit"}
    assert evaluate_control("PRV-009", evidence, {"PRV-003": "not_detected"})["result"] == "not_applicable"
    assert evaluate_control("PRV-009", evidence, {"PRV-003": "not_evaluable"})["result"] == "not_evaluable"

    url = "https://example.com/privacy"
    link = LinkEvidence(url, "Política de privacidad", "https://example.com/")
    adapted = adapt_evidence(contract(links=[link], pages=[]))
    assert adapted["PRV-009"]["technical_error"] is True
    assert evaluate_control("PRV-009", adapted["PRV-009"], {"PRV-003": "detected"})["result"] == "not_evaluable"


@pytest.mark.parametrize(("provider_text", "own_text", "expected"), [
    ("We process personal data based on consent.", "Información general de privacidad.", "not_detected"),
    ("Privacy information without a declared basis.", "Tratamos sus datos con su consentimiento.", "detected"),
])
def test_prv009_uses_only_policy_selected_after_provider_candidate(
    provider_text, own_text, expected
):
    provider_url = "https://hcaptcha.com/privacy"
    own_url = "https://example.com/privacy"
    links = [
        LinkEvidence(provider_url, "hCaptcha Privacy", "https://example.com/"),
        LinkEvidence(own_url, "Política de privacidad", "https://example.com/"),
    ]
    pages = [
        PageEvidence(provider_url, 200, "Privacy", "text/html", visible_text=provider_text),
        PageEvidence(own_url, 200, "Política de privacidad", "text/html", visible_text=own_text),
    ]
    adapted = adapt_evidence(contract(links=links, pages=pages))
    prv003 = evaluate_control("PRV-003", adapted["PRV-003"])
    result = evaluate_control("PRV-009", adapted["PRV-009"], {"PRV-003": prv003})

    assert result["result"] == expected
    assert adapted["PRV-009"]["source_urls"] == [own_url]


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


def test_prv201_sufficient_inspection_without_cookies_is_not_detected():
    evidence = adapt_evidence(contract())["PRV-201"]
    assert evidence["cookies_observed"] is False
    assert evidence["relevant_cookies"] is False
    assert evaluate_control("PRV-201", evidence)["result"] == "not_detected"


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


def _adapt_selected_policy(text, *, other_text=None, forms=None):
    url = "https://example.com/privacy"
    link = LinkEvidence(url, "Política de privacidad", "https://example.com/")
    pages = [PageEvidence(url, 200, "Política de privacidad", "text/html", visible_text=text)]
    if other_text is not None:
        pages.append(PageEvidence("https://example.com/otra", 200, "Otra", "text/html", visible_text=other_text))
    return adapt_evidence(contract(links=[link], pages=pages, forms=forms or []))


@pytest.mark.parametrize(("text", "signal", "result"), [
    ("Puede presentar una reclamación ante la Agencia de Protección de Datos Personales.", "explicit", "detected"),
    ("You may lodge a complaint with the data protection authority.", "explicit", "detected"),
    ("En relación con sus datos personales, puede reclamar ante la autoridad competente.", "generic", "partial"),
    ("Esta política explica el tratamiento de datos personales.", "none", "not_detected"),
    ("Agencia de marketing. Autoridades tributarias. Autoridad competente para contratos.", "none", "not_detected"),
])
def test_prv013_classifies_contextual_complaints(text, signal, result):
    adapted = _adapt_selected_policy(text)
    evaluated = evaluate_control("PRV-013", adapted["PRV-013"], {"PRV-003": "detected"})
    assert adapted["PRV-013"]["agency_complaint"] == signal
    assert adapted["PRV-013"]["source_urls"] == ["https://example.com/privacy"]
    assert evaluated["result"] == result


@pytest.mark.parametrize(("text", "basis", "signal", "result"), [
    ("Cuando el tratamiento se base en su consentimiento, podrá retirar su consentimiento.", True, "explicit", "detected"),
    ("Processing of personal data is based on your consent. You may withdraw your consent.", True, "explicit", "detected"),
    ("Tratamos sus datos con su consentimiento. Puede modificar sus preferencias de consentimiento.", True, "generic", "partial"),
    ("Tratamos sus datos con su consentimiento para responder consultas.", True, "none", "not_detected"),
    ("Esta política menciona el consentimiento.", False, "none", "not_applicable"),
    ("Consentimiento de cookies. Acepto los términos.", False, "none", "not_applicable"),
    ("Gestionar preferencias de cookies. Checkbox de consentimiento.", False, "none", "not_applicable"),
    ("Consentimiento para recibir promociones.", False, "none", "not_applicable"),
    ("La ley autoriza el tratamiento de datos personales.", False, "none", "not_applicable"),
    ("Existe autorización legal para el tratamiento de datos personales.", False, "none", "not_applicable"),
    ("El tratamiento se encuentra autorizado por la normativa aplicable.", False, "none", "not_applicable"),
    ("El usuario presta su consentimiento para el tratamiento de sus datos personales.", True, "none", "not_detected"),
    ("Solicitamos su consentimiento para tratar sus datos personales.", True, "none", "not_detected"),
    ("We obtain your consent for the processing of your personal data.", True, "none", "not_detected"),
    ("You consent to the processing of your personal data.", True, "none", "not_detected"),
])
def test_prv014_requires_declared_consent_basis(text, basis, signal, result):
    adapted = _adapt_selected_policy(text)
    evidence = adapted["PRV-014"]
    evaluated = evaluate_control("PRV-014", evidence, {"PRV-003": "detected"})
    assert evidence["consent_basis_declared"] is basis
    assert evidence["consent_withdrawal"] == signal
    assert evidence["source_urls"] == ["https://example.com/privacy"]
    assert evaluated["result"] == result


def test_prv014_detects_emol_style_consent_basis_and_revocation():
    adapted = _adapt_selected_policy(
        "El usuario otorga su consentimiento para el tratamiento de sus datos "
        "personales. La autorización otorgada podrá ser revocada."
    )
    evidence = adapted["PRV-014"]

    assert evidence["consent_basis_declared"] is True
    assert evidence["consent_withdrawal"] == "explicit"
    assert evaluate_control(
        "PRV-014", evidence, {"PRV-003": "detected"}
    )["result"] == "detected"


def test_prv014_treats_preference_management_as_ambiguous_with_declared_basis():
    adapted = _adapt_selected_policy(
        "El usuario otorga su consentimiento para el tratamiento de sus datos "
        "personales y puede gestionar sus preferencias."
    )
    evidence = adapted["PRV-014"]

    assert evidence["consent_basis_declared"] is True
    assert evidence["consent_withdrawal"] == "generic"
    assert evaluate_control(
        "PRV-014", evidence, {"PRV-003": "detected"}
    )["result"] == "partial"


@pytest.mark.parametrize("withdrawal", [
    "Puede revocar la autorización.",
    "Puede retirar la autorización.",
    "La autorización puede ser revocada.",
])
def test_prv014_recognizes_authorization_withdrawal_phrasing(withdrawal):
    adapted = _adapt_selected_policy(
        f"Otorga su consentimiento para el tratamiento de datos personales. {withdrawal}"
    )
    evidence = adapted["PRV-014"]

    assert evidence["consent_basis_declared"] is True
    assert evidence["consent_withdrawal"] == "explicit"
    assert evaluate_control(
        "PRV-014", evidence, {"PRV-003": "detected"}
    )["result"] == "detected"


def test_new_controls_use_only_prv003_selected_policy_and_ignore_forms_and_other_pages():
    noisy_form = form(
        nearby_text="Acepto los términos y retiro mi consentimiento",
        checkboxes=[CheckboxEvidence("consent", "Acepto")],
    )
    adapted = _adapt_selected_policy(
        "Esta política explica cómo usamos datos personales.",
        other_text=("Puede reclamar ante la Agencia de Protección de Datos Personales. "
                    "El tratamiento se basa en consentimiento y puede retirarlo."),
        forms=[noisy_form],
    )
    assert adapted["PRV-013"]["agency_complaint"] == "none"
    assert adapted["PRV-014"]["consent_basis_declared"] is False
    assert adapted["PRV-013"]["source_urls"] == ["https://example.com/privacy"]
    assert adapted["PRV-014"]["source_urls"] == ["https://example.com/privacy"]


def test_new_control_dependency_and_technical_states_are_explicit():
    complaint = {"agency_complaint": "none"}
    withdrawal = {"consent_basis_declared": True, "consent_withdrawal": "none"}
    for code, evidence in (("PRV-013", complaint), ("PRV-014", withdrawal)):
        assert evaluate_control(code, evidence, {"PRV-003": "not_detected"})["result"] == "not_applicable"
        assert evaluate_control(code, evidence, {"PRV-003": "not_evaluable"})["result"] == "not_evaluable"
        assert evaluate_control(code, {**evidence, "technical_error": True}, {"PRV-003": "detected"})["result"] == "not_evaluable"


def _personal_transport_form(
    source_url, action, *, confidence="high", method="post"
):
    field = (
        FieldEvidence("value", "email", "", False)
        if confidence == "high"
        else FieldEvidence("company", "text", "", False)
    )
    return FormEvidence(source_url, action, method, [field], [], "", [])


def _evaluate_prv102(contract_evidence):
    adapted = adapt_evidence(contract_evidence)
    prv101 = evaluate_control("PRV-101", adapted["PRV-101"])
    return adapted["PRV-102"], evaluate_control(
        "PRV-102", adapted["PRV-102"], {"PRV-101": prv101}
    )


@pytest.mark.parametrize(
    ("source", "action", "expected"),
    [
        ("https://example.com/contact", "https://example.com/send", "detected"),
        ("https://example.com/contact", "http://example.com/send", "not_detected"),
        ("http://example.com/contact", "https://example.com/send", "not_detected"),
        ("https://example.com/contact", "mailto:privacy@example.com", "not_evaluable"),
        ("invalid", "https://example.com/send", "not_evaluable"),
    ],
)
def test_prv102_classifies_high_confidence_form_transport(source, action, expected):
    personal = _personal_transport_form(source, action)
    evidence, result = _evaluate_prv102(contract(forms=[personal]))

    assert result["result"] == expected
    assert "action" not in repr(evidence)


def test_prv102_insecure_high_form_precedes_secure_and_unknown_forms():
    forms = [
        _personal_transport_form("https://example.com/secure", "https://example.com/send"),
        _personal_transport_form("https://example.com/unknown", "custom:send"),
        _personal_transport_form("https://example.com/insecure", "http://example.com/send"),
    ]
    pages = [PageEvidence(item.source_url, 200, "Formulario", "text/html") for item in forms]

    evidence, result = _evaluate_prv102(contract(forms=forms, pages=pages))

    assert result["result"] == "not_detected"
    assert evidence["source_urls"] == ["https://example.com/insecure"]


def test_prv102_high_secure_plus_high_unknown_is_not_evaluable():
    forms = [
        _personal_transport_form(
            "https://example.com/secure", "https://example.com/send"
        ),
        _personal_transport_form(
            "https://example.com/unknown", "custom:send"
        ),
    ]

    _, result = _evaluate_prv102(contract(forms=forms))

    assert result["result"] == "not_evaluable"


@pytest.mark.parametrize(
    "medium_action", ["https://example.com/send", "http://example.com/send"]
)
def test_prv102_high_insecure_precedes_medium_candidate(medium_action):
    forms = [
        _personal_transport_form(
            "https://example.com/insecure", "http://example.com/send"
        ),
        _personal_transport_form(
            "https://example.com/medium", medium_action, confidence="medium"
        ),
    ]

    _, result = _evaluate_prv102(contract(forms=forms))

    assert result["result"] == "not_detected"


def test_prv102_accepts_external_https_action():
    personal = _personal_transport_form(
        "https://empresa.cl/contacto",
        "https://forms.vendor.example/submit",
    )

    _, result = _evaluate_prv102(contract(forms=[personal]))

    assert result["result"] == "detected"


def test_prv102_get_method_does_not_change_secure_transport():
    personal = _personal_transport_form(
        "https://example.com/contact",
        "https://example.com/send",
        method="get",
    )

    _, result = _evaluate_prv102(contract(forms=[personal]))

    assert result["result"] == "detected"


@pytest.mark.parametrize(
    ("action_attribute", "expected_action"),
    [
        ('action="/enviar"', "https://example.com/enviar"),
        ("", "https://example.com/contacto"),
        ('action=""', "https://example.com/contacto"),
    ],
)
def test_prv102_uses_extractor_resolution_for_relative_and_empty_actions(
    action_attribute, expected_action
):
    source = "https://example.com/contacto"
    html = (
        f"<form {action_attribute}>"
        '<input type="email" name="email">'
        "</form>"
    )
    extracted_form = extract_page(html, source).forms[0]

    assert extracted_form.action == expected_action
    _, result = _evaluate_prv102(contract(forms=[extracted_form]))
    assert result["result"] == "detected"


def test_prv102_never_exposes_adversarial_action_details():
    source = "https://example.com/contacto?public=trace#form"
    action = "https://user:secret@203.0.113.10/send?token=abc123&query=private"
    personal = _personal_transport_form(source, action)
    page = PageEvidence(source, 200, "Contacto", "text/html")

    evidence, result = _evaluate_prv102(
        contract(forms=[personal], pages=[page])
    )

    assert result["result"] == "detected"
    assert evidence["source_urls"] == ["https://example.com/contacto"]
    serialized = repr(evidence).lower()
    for secret in (
        "action", "user", "secret", "token", "query", "abc123", "?",
        "203.0.113.10",
    ):
        assert secret not in serialized


@pytest.mark.parametrize("with_high", [False, True])
def test_prv102_medium_candidate_prevents_positive_or_negative_score(with_high):
    forms = [
        _personal_transport_form(
            "https://example.com/medium", "http://example.com/send", confidence="medium"
        )
    ]
    if with_high:
        forms.append(_personal_transport_form(
            "https://example.com/secure", "https://example.com/send"
        ))

    _, result = _evaluate_prv102(contract(forms=forms))

    assert result["result"] == "not_evaluable"


def test_prv102_is_not_applicable_without_personal_forms():
    _, result = _evaluate_prv102(contract())
    assert result["result"] == "not_applicable"


def test_prv102_technical_error_is_not_evaluable():
    evidence = {"form_transport": "insecure", "technical_error": True}
    result = evaluate_control("PRV-102", evidence, {"PRV-101": "detected"})
    assert result["result"] == "not_evaluable"
