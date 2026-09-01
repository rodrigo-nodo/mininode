import re
import sys
from pathlib import Path


BACKEND_SRC = Path(__file__).resolve().parents[3] / "src"
sys.path.insert(0, str(BACKEND_SRC))

from mininode_api.domain_packs.privacy.evaluator import (  # noqa: E402
    evaluate_control,
    load_controls,
)
from mininode_api.domain_packs.privacy.prioritization import (  # noqa: E402
    load_actions,
    prioritize_findings,
)


EXPECTED_ACTIONS = {
    "PRV-001": {"not_detected"},
    "PRV-002": {"partial"},
    "PRV-003": {"partial", "not_detected"},
    "PRV-004": {"partial", "not_detected"},
    "PRV-005": {"partial", "not_detected"},
    "PRV-006": {"partial", "not_detected"},
    "PRV-007": {"partial", "not_detected"},
    "PRV-008": {"partial", "not_detected"},
    "PRV-009": {"partial", "not_detected"},
    "PRV-010": {"partial", "not_detected"},
    "PRV-011": {"partial", "not_detected"},
    "PRV-012": {"partial", "not_detected"},
    "PRV-013": {"partial", "not_detected"},
    "PRV-014": {"partial", "not_detected"},
    "PRV-102": {"not_detected"},
    "PRV-104": {"partial", "not_detected"},
    "PRV-201": {"not_detected"},
    "PRV-301": {"not_detected"},
    "PRV-501": {"partial", "not_detected"},
}
LEGACY_FIELDS = {
    "control_code", "name", "priority", "finding", "recommendation",
    "source_url", "evidence_summary",
}


def test_action_catalog_integrity_and_approved_results():
    catalog = load_actions()
    assert catalog["version"]
    assert isinstance(catalog["actions"], dict)
    assert {code: set(results) for code, results in catalog["actions"].items()} == EXPECTED_ACTIONS

    controls = {control["code"]: control for control in load_controls()}
    assert set(catalog["actions"]) <= set(controls)
    assert "PRV-101" not in catalog["actions"]
    for code, outcomes in catalog["actions"].items():
        assert set(outcomes) <= set(controls[code]["criteria"])
        assert set(outcomes) <= {"partial", "not_detected"}
        for action in outcomes.values():
            assert set(action) == {"action_steps", "validation_step"}
            assert 2 <= len(action["action_steps"]) <= 4
            assert all(isinstance(step, str) and step.strip() for step in action["action_steps"])
            assert isinstance(action["validation_step"], str)
            assert action["validation_step"].strip()


def test_every_action_is_actionable_and_reachable_through_active_pipeline():
    catalog = load_actions()["actions"]
    scenarios = {
        "PRV-001": [({"policy_visible": False}, None)],
        "PRV-002": [(
            {"policy_accessible": False, "policy_content_relevant": False},
            {"PRV-001": "detected"},
        )],
        "PRV-003": [
            ({"policy_attribution": "ambiguous"}, None),
            ({"policy_attribution": "third_party"}, None),
        ],
        "PRV-004": [
            ({"policy_document_reference": "ambiguous"}, {"PRV-003": "detected"}),
            ({"policy_document_reference": "none"}, {"PRV-003": "detected"}),
        ],
        "PRV-005": [
            ({"responsible_identification": "ambiguous"}, {"PRV-003": "detected"}),
            ({"responsible_identification": "none"}, {"PRV-003": "detected"}),
        ],
        "PRV-006": [
            ({"rights_channel": "generic"}, {"PRV-003": "detected"}),
            ({"rights_channel": "none"}, {"PRV-003": "detected"}),
        ],
        "PRV-007": [
            ({"data_categories": "generic"}, {"PRV-003": "detected"}),
            ({"data_categories": "none"}, {"PRV-003": "detected"}),
        ],
        "PRV-008": [
            ({"processing_purposes": "generic"}, {"PRV-003": "detected"}),
            ({"processing_purposes": "none"}, {"PRV-003": "detected"}),
        ],
        "PRV-009": [
            ({"declared_processing_basis": "generic"}, {"PRV-003": "detected"}),
            ({"declared_processing_basis": "none"}, {"PRV-003": "detected"}),
        ],
        "PRV-010": [
            ({"data_recipients": "generic"}, {"PRV-003": "detected"}),
            ({"data_recipients": "none"}, {"PRV-003": "detected"}),
        ],
        "PRV-011": [
            ({"data_subject_rights": "generic"}, {"PRV-003": "detected"}),
            ({"data_subject_rights": "none"}, {"PRV-003": "detected"}),
        ],
        "PRV-012": [
            ({"data_retention": "generic"}, {"PRV-003": "detected"}),
            ({"data_retention": "none"}, {"PRV-003": "detected"}),
        ],
        "PRV-013": [
            ({"agency_complaint": "generic"}, {"PRV-003": "detected"}),
            ({"agency_complaint": "none"}, {"PRV-003": "detected"}),
        ],
        "PRV-014": [
            ({"consent_basis_declared": True, "consent_withdrawal": "generic"}, {"PRV-003": "detected"}),
            ({"consent_basis_declared": True, "consent_withdrawal": "none"}, {"PRV-003": "detected"}),
        ],
        "PRV-102": [({"form_transport": "insecure"}, {"PRV-101": "detected"})],
        "PRV-104": [
            ({"privacy_information": False, "consent_mechanism": True}, {"PRV-101": "detected"}),
            ({"privacy_information": False, "consent_mechanism": False}, {"PRV-101": "detected"}),
        ],
        "PRV-201": [({"cookies_observed": True, "cookie_information": False}, None)],
        "PRV-301": [({"contact_channel_visible": False}, None)],
        "PRV-501": [
            ({"https": True, "tls_valid": True, "mixed_content": True}, None),
            ({"https": False, "tls_valid": False}, None),
        ],
    }
    produced = {
        code: {
            evaluate_control(code, evidence, previous)["result"]
            for evidence, previous in cases
        }
        for code, cases in scenarios.items()
    }

    for code, outcomes in catalog.items():
        for outcome in outcomes:
            assert outcome in produced[code]
            if code in {"PRV-004", "PRV-009"}:
                assert prioritize_findings([
                    {"control_code": code, "result": outcome, "confidence": "high"}
                ]) == []
                continue
            prioritized = prioritize_findings([
                {"control_code": code, "result": outcome, "confidence": "high"}
            ])
            assert prioritized and prioritized[0]["control_code"] == code


def test_aligned_action_plans_are_exact():
    actions = load_actions()["actions"]
    assert "not_detected" not in actions["PRV-002"]
    assert "partial" not in actions["PRV-201"]
    assert actions["PRV-002"]["partial"] == {
        "action_steps": [
            "Abrir el enlace o referencia de privacidad detectado.",
            "Comprobar que el destino puede cargarse públicamente y que corresponde a información de privacidad.",
            "Corregir el enlace, redirección o página de destino cuando corresponda.",
        ],
        "validation_step": "Volver a abrir el enlace desde una página pública y comprobar que el destino carga correctamente y presenta información relacionada con privacidad.",
    }
    assert actions["PRV-104"]["partial"] == {
        "action_steps": [
            "Revisar qué información recibe la persona antes de enviar el formulario.",
            "Incorporar junto al formulario información visible sobre el tratamiento de los datos.",
            "Mantener la señal de consentimiento o aceptación separada de esa información y evaluar su uso según el contexto cuando corresponda.",
        ],
        "validation_step": "Abrir la página del formulario y comprobar que la información de privacidad puede identificarse antes del envío y que cualquier señal adicional de consentimiento o aceptación se presenta de forma separada y visible.",
    }
    assert actions["PRV-104"]["not_detected"] == {
        "action_steps": [
            "Definir qué información sobre el tratamiento de datos debe presentarse junto al formulario.",
            "Incorporar esa información de forma visible antes del envío.",
            "Evaluar separadamente si el contexto requiere algún mecanismo adicional de consentimiento o aceptación.",
        ],
        "validation_step": "Abrir la página del formulario y comprobar que la información de privacidad es visible antes del envío y que cualquier mecanismo adicional, cuando corresponda, puede identificarse claramente.",
    }
    assert actions["PRV-201"]["not_detected"] == {
        "action_steps": [
            "Revisar qué cookies o tecnologías asociadas está utilizando el sitio dentro de su funcionamiento real.",
            "Incorporar información visible sobre el uso de cookies cuando corresponda.",
            "Verificar que esa información pueda encontrarse fácilmente durante una visita normal al sitio.",
        ],
        "validation_step": "Visitar el sitio en una sesión nueva y comprobar que, cuando se observan cookies, también puede identificarse información visible relacionada con su uso.",
    }


def test_action_catalog_has_no_placeholders_dynamic_interpolation_or_defensive_terms():
    forbidden_terms = re.compile(
        r"\b(cumple|incumple|ilegal|obligatorio|garantiza)\b"
        r"|\b(?:es|está|queda) certificado\b",
        re.IGNORECASE,
    )
    placeholders = ("{{", "}}", "${", "<%", "%>", "source_url", "evidence_summary")
    unmeasured_terms = ("incomplet", "ambigu", "poco visible")
    for outcomes in load_actions()["actions"].values():
        for action in outcomes.values():
            texts = [*action["action_steps"], action["validation_step"]]
            assert all(not forbidden_terms.search(text) for text in texts)
            assert all(marker not in text for text in texts for marker in placeholders)
            assert all(term not in text.lower() for text in texts for term in unmeasured_terms)


def test_enrichment_preserves_legacy_priority_contract_and_selection():
    sensitive_url = "https://example.com/form?email=secret@example.com#private"
    sensitive_summary = "HTML <textarea>secret</textarea>; cookie=id; IP 192.0.2.1"
    results = [
        {"control_code": "PRV-501", "result": "partial", "confidence": "high"},
        {
            "control_code": "PRV-104", "result": "not_detected", "confidence": "low",
            "source_url": sensitive_url, "evidence_summary": sensitive_summary,
        },
        {"control_code": "PRV-001", "result": "not_detected", "confidence": "high"},
        {"control_code": "PRV-101", "result": "not_detected", "confidence": "high"},
        {"control_code": "PRV-301", "result": "not_detected", "confidence": "high"},
    ]
    priorities = prioritize_findings(results, limit=20)

    assert [priority["control_code"] for priority in priorities] == [
        "PRV-001", "PRV-104", "PRV-501",
    ]
    assert len(priorities) == 3
    assert all({"action_steps", "validation_step"} <= set(priority) for priority in priorities)
    assert "PRV-101" not in {priority["control_code"] for priority in priorities}

    controls = {control["code"]: control for control in load_controls()}
    outcomes = {result["control_code"]: result["result"] for result in results}
    for priority in priorities:
        control = controls[priority["control_code"]]
        legacy = {key: value for key, value in priority.items() if key in LEGACY_FIELDS}
        expected = {
            "control_code": control["code"],
            "name": control["name"],
            "priority": {"muy_alto": "Alta", "alto": "Alta", "medio": "Media", "bajo": "Baja"}[control["impact"]],
            "finding": control["criteria"][outcomes[control["code"]]],
            "recommendation": control["base_recommendation"],
        }
        source = next(item for item in results if item["control_code"] == control["code"])
        for optional in ("source_url", "evidence_summary"):
            if source.get(optional):
                expected[optional] = source[optional]
        assert legacy == expected

        action_text = " ".join([*priority["action_steps"], priority["validation_step"]])
        assert sensitive_url not in action_text
        assert sensitive_summary not in action_text
        assert "secret@example.com" not in action_text


def test_unknown_catalog_lookup_keeps_exact_legacy_shape(monkeypatch):
    monkeypatch.setattr(
        "mininode_api.domain_packs.privacy.prioritization.load_actions",
        lambda: {"version": "1", "actions": {}},
    )
    priority = prioritize_findings([
        {"control_code": "PRV-001", "result": "not_detected", "confidence": "high"}
    ])[0]
    assert set(priority) == {"control_code", "name", "priority", "finding", "recommendation"}
