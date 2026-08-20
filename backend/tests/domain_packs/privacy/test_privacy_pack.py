import json
import sys
from pathlib import Path

import pytest


BACKEND_SRC = Path(__file__).resolve().parents[3] / "src"
sys.path.insert(0, str(BACKEND_SRC))

from mininode_api.domain_packs.privacy.evaluator import (  # noqa: E402
    evaluate_control,
    load_controls,
)
from mininode_api.domain_packs.privacy.prioritization import (  # noqa: E402
    prioritize_findings,
)
from mininode_api.domain_packs.privacy.scoring import (  # noqa: E402
    load_scoring,
    score_privacy,
)


EXPECTED = {
    "PRV-001": ("Política de privacidad visible", "muy_alto", "evaluation"),
    "PRV-002": ("Política de privacidad accesible", "medio", "conditional_evaluation"),
    "PRV-003": ("Política propia del responsable", "muy_alto", "evaluation"),
    "PRV-005": ("Identificación del responsable", "alto", "conditional_evaluation"),
    "PRV-006": ("Canal para ejercer derechos", "muy_alto", "conditional_evaluation"),
    "PRV-007": ("Categorías de datos tratados", "alto", "conditional_evaluation"),
    "PRV-008": ("Finalidades del tratamiento", "muy_alto", "conditional_evaluation"),
    "PRV-011": ("Derechos del titular", "muy_alto", "conditional_evaluation"),
    "PRV-101": ("Formularios que recopilan datos personales", "alto", "context"),
    "PRV-104": ("Información de privacidad asociada al formulario", "muy_alto", "conditional_evaluation"),
    "PRV-201": ("Información visible sobre cookies", "medio", "conditional_evaluation"),
    "PRV-301": ("Canal de contacto visible", "bajo", "evaluation"),
    "PRV-501": ("Uso de HTTPS", "muy_alto", "evaluation"),
}


def evaluated_scenario():
    results = {}
    results["PRV-001"] = evaluate_control("PRV-001", {"policy_visible": True})
    results["PRV-002"] = evaluate_control(
        "PRV-002",
        {"policy_link_found": True, "policy_accessible": True},
        results,
    )
    results["PRV-003"] = evaluate_control(
        "PRV-003", {"policy_attribution": "own"}
    )
    results["PRV-101"] = evaluate_control(
        "PRV-101", {"personal_data_form": True}
    )
    results["PRV-104"] = evaluate_control(
        "PRV-104", {"privacy_information": False}, results
    )
    results["PRV-201"] = evaluate_control(
        "PRV-201", {"relevant_cookies": False}
    )
    results["PRV-301"] = evaluate_control(
        "PRV-301", {"contact_channel_visible": True}
    )
    results["PRV-501"] = evaluate_control(
        "PRV-501", {"https": True, "tls_valid": True}
    )
    return results


def test_catalog_matches_the_approved_controls_exactly():
    controls = load_controls()
    assert len(controls) == 13
    assert {
        control["code"]: (control["name"], control["impact"], control["type"])
        for control in controls
    } == EXPECTED


def test_catalog_contains_required_metadata_and_dependencies():
    controls = {control["code"]: control for control in load_controls()}
    assert controls["PRV-101"]["type"] == "context"
    assert controls["PRV-101"]["score_weight"] == 0
    assert controls["PRV-002"]["dependency"] == "PRV-001"
    assert controls["PRV-104"]["dependency"] == "PRV-101"
    for code in ("PRV-005", "PRV-006", "PRV-007", "PRV-008", "PRV-011"):
        assert controls[code]["dependency"] == "PRV-003"
    for control in controls.values():
        assert control["expected_evidence"]
        assert control["base_recommendation"]
        assert control["criteria"]


def test_catalog_criteria_match_active_evaluator_results():
    active_results = {
        "PRV-001": {"detected", "not_detected", "not_evaluable"},
        "PRV-002": {"detected", "partial", "not_applicable", "not_evaluable"},
        "PRV-003": {"detected", "partial", "not_detected", "not_evaluable"},
        **{
            code: {"detected", "partial", "not_detected", "not_applicable", "not_evaluable"}
            for code in ("PRV-005", "PRV-006", "PRV-007", "PRV-008", "PRV-011")
        },
        "PRV-101": {"detected", "not_detected", "not_evaluable"},
        "PRV-104": {
            "detected", "partial", "not_detected", "not_applicable",
            "not_evaluable",
        },
        "PRV-201": {"detected", "not_detected", "not_applicable", "not_evaluable"},
        "PRV-301": {"detected", "not_detected", "not_evaluable"},
        "PRV-501": {"detected", "partial", "not_detected", "not_evaluable"},
    }
    controls = {control["code"]: control for control in load_controls()}

    assert {
        code: set(control["criteria"]) for code, control in controls.items()
    } == active_results


def test_observable_findings_avoid_unmeasured_claims():
    controls = {control["code"]: control for control in load_controls()}
    prv104 = controls["PRV-104"]["criteria"]
    prv201 = controls["PRV-201"]["criteria"]

    assert all(term not in prv104["detected"].lower() for term in (
        "clara", "completa", "consentimiento cuando corresponda",
    ))
    assert all(term not in prv104["partial"].lower() for term in (
        "incomplet", "ambigu", "poco visible",
    ))
    assert all(term not in prv201["detected"].lower() for term in (
        "preferencias", "completa",
    ))
    assert "no existe mecanismo" not in prv201["not_detected"].lower()
    assert "no se observaron" in prv201["not_applicable"].lower()
    assert "no usa cookies" not in prv201["not_applicable"].lower()
    assert "not_detected" not in controls["PRV-002"]["criteria"]
    assert "partial" not in prv201


def test_evaluator_accepts_structured_evidence_and_returns_approved_shape():
    result = evaluate_control(
        "PRV-001",
        {
            "policy_visible": True,
            "confidence": "high",
            "evidence": [{"url": "/privacidad"}],
        },
    )
    assert result == {
        "control_code": "PRV-001",
        "result": "detected",
        "confidence": "high",
        "evidence": [{"url": "/privacidad"}],
        "reason": load_controls()[0]["criteria"]["detected"],
    }


def test_dependencies_produce_not_applicable():
    policy = evaluate_control("PRV-001", {"policy_visible": False})
    forms = evaluate_control("PRV-101", {"personal_data_form": False})
    assert evaluate_control(
        "PRV-002", {}, {"PRV-001": policy}
    )["result"] == "not_applicable"
    assert evaluate_control(
        "PRV-104", {}, {"PRV-101": forms}
    )["result"] == "not_applicable"


@pytest.mark.parametrize(
    ("code", "detected", "partial"),
    [
        ("PRV-005", {"responsible_identification": "clear"}, {"responsible_identification": "ambiguous"}),
        ("PRV-006", {"rights_channel": "explicit"}, {"rights_channel": "generic"}),
        ("PRV-007", {"data_categories": ["nombre"]}, {"generic_personal_data": True}),
        ("PRV-008", {"treatment_purposes": ["responder consultas"]}, {"generic_data_use": True}),
        ("PRV-011", {"holder_rights": ["acceso", "rectificacion"]}, {"holder_rights": ["acceso"]}),
    ],
)
def test_b1_substantive_evaluator_states(code, detected, partial):
    previous = {"PRV-003": "detected"}
    assert evaluate_control(code, detected, previous)["result"] == "detected"
    assert evaluate_control(code, partial, previous)["result"] == "partial"
    assert evaluate_control(code, {}, previous)["result"] == "not_detected"
    assert evaluate_control(code, {}, {"PRV-003": "not_detected"})["result"] == "not_applicable"
    assert evaluate_control(code, {}, {"PRV-003": "not_evaluable"})["result"] == "not_evaluable"


def test_cookies_can_be_not_applicable():
    assert evaluate_control(
        "PRV-201", {"relevant_cookies": False}
    )["result"] == "not_applicable"


@pytest.mark.parametrize(
    ("result", "expected_score"),
    [("detected", 100), ("partial", 50), ("not_detected", 0)],
)
def test_result_factors_are_applied(result, expected_score):
    assert score_privacy([{"control_code": "PRV-501", "result": result}])[
        "score"
    ] == expected_score


def test_prv104_observable_detection_changes_only_its_score_contribution():
    unchanged = [
        {"control_code": "PRV-001", "result": "detected"},
        {"control_code": "PRV-201", "result": "not_detected"},
        {"control_code": "PRV-501", "result": "detected"},
    ]
    before = score_privacy([
        *unchanged, {"control_code": "PRV-104", "result": "partial"}
    ])
    after = score_privacy([
        *unchanged, {"control_code": "PRV-104", "result": "detected"}
    ])

    assert before == {
        "score": 71,
        "status": "Preparación avanzada",
        "coverage": 100,
        "evaluated_controls": 4,
        "applicable_controls": 4,
    }
    assert after == {
        "score": 86,
        "status": "Alta preparación visible",
        "coverage": 100,
        "evaluated_controls": 4,
        "applicable_controls": 4,
    }


def test_not_applicable_does_not_affect_score():
    detected = {"control_code": "PRV-001", "result": "detected"}
    assert score_privacy([detected]) == score_privacy(
        [detected, {"control_code": "PRV-201", "result": "not_applicable"}]
    )


def test_not_evaluable_is_unscored_and_reduces_coverage():
    results = list(evaluated_scenario().values())
    results[-1] = {"control_code": "PRV-501", "result": "not_evaluable"}
    scored = score_privacy(results)
    assert scored["evaluated_controls"] == 5
    assert scored["applicable_controls"] == 6
    assert scored["coverage"] == 83


def test_context_never_scores():
    detected = score_privacy(
        [{"control_code": "PRV-101", "result": "detected"}]
    )
    not_detected = score_privacy(
        [{"control_code": "PRV-101", "result": "not_detected"}]
    )
    assert detected == not_detected


def test_integral_scenario_returns_the_approved_result():
    assert score_privacy(evaluated_scenario().values()) == {
        "score": 74,
        "status": "Preparación avanzada",
        "coverage": 100,
        "evaluated_controls": 6,
        "applicable_controls": 6,
    }


def test_prioritization_is_consumer_facing_limited_and_excludes_context():
    results = [
        {"control_code": code, "result": "not_detected", "confidence": "high"}
        for code in EXPECTED
    ]
    priorities = prioritize_findings(results, limit=20)
    assert len(priorities) == 3
    assert all(
        set(priority)
        == {
            "control_code", "name", "priority", "finding", "recommendation",
            "action_steps", "validation_step",
        }
        for priority in priorities
    )
    assert "PRV-101" not in {priority["control_code"] for priority in priorities}


def test_priority_order_is_impact_result_confidence_then_code():
    results = [
        {"control_code": "PRV-501", "result": "partial", "confidence": "high"},
        {"control_code": "PRV-104", "result": "not_detected", "confidence": "low"},
        {"control_code": "PRV-001", "result": "not_detected", "confidence": "high"},
    ]
    assert [item["control_code"] for item in prioritize_findings(results)] == [
        "PRV-001",
        "PRV-104",
        "PRV-501",
    ]


def test_optional_source_trace_preserves_priority_shape_order_and_count():
    results = [
        {"control_code": "PRV-001", "result": "not_detected", "confidence": "high"},
        {
            "control_code": "PRV-104", "result": "not_detected", "confidence": "high",
            "source_url": "https://example.com/contact",
        },
        {"control_code": "PRV-501", "result": "partial", "confidence": "high"},
    ]
    without_trace = [{key: value for key, value in result.items() if key != "source_url"} for result in results]

    priorities = prioritize_findings(results)
    baseline = prioritize_findings(without_trace)

    assert [item["control_code"] for item in priorities] == [item["control_code"] for item in baseline]
    assert len(priorities) == len(baseline)
    assert priorities[1]["source_url"] == "https://example.com/contact"
    assert set(priorities[1]) == {
        "control_code", "name", "priority", "finding", "recommendation", "source_url",
        "action_steps", "validation_step",
    }
    assert set(priorities[0]) == {
        "control_code", "name", "priority", "finding", "recommendation",
        "action_steps", "validation_step",
    }


def test_optional_visible_summary_preserves_priority_order_and_count():
    results = [
        {"control_code": "PRV-001", "result": "not_detected", "confidence": "high"},
        {
            "control_code": "PRV-104", "result": "not_detected", "confidence": "high",
            "source_url": "https://example.com/contact",
            "evidence_summary": "En el formulario revisado no se identificaron señales visibles de información de privacidad ni de consentimiento o aceptación.",
        },
        {"control_code": "PRV-501", "result": "partial", "confidence": "high"},
    ]
    baseline = prioritize_findings([
        {key: value for key, value in result.items() if key != "evidence_summary"}
        for result in results
    ])
    priorities = prioritize_findings(results)

    assert [item["control_code"] for item in priorities] == [item["control_code"] for item in baseline]
    assert len(priorities) == len(baseline)
    assert priorities[1]["evidence_summary"] == (
        "En el formulario revisado no se identificaron señales visibles de información de privacidad ni de consentimiento o aceptación."
    )


def test_scoring_disclaimers_are_literal():
    assert load_scoring()["disclaimers"] == [
        "Privacy Score es un indicador desarrollado por Mininode que estima el nivel de preparación de un sitio web a partir de señales públicas, documentación visible y buenas prácticas relacionadas con la protección de datos personales. No constituye una certificación legal ni una auditoría completa.",
        "No representa un porcentaje de cumplimiento de la ley.",
    ]


def test_invalid_control_evidence_and_confidence_are_rejected():
    with pytest.raises(ValueError, match="Unknown privacy control"):
        evaluate_control("PRV-999", {})
    with pytest.raises(TypeError, match="evidence must be a mapping"):
        evaluate_control("PRV-001", [])
    with pytest.raises(ValueError, match="Invalid confidence"):
        evaluate_control("PRV-001", {"confidence": "certain"})


def test_json_files_are_valid_utf8_json():
    privacy_dir = BACKEND_SRC / "mininode_api" / "domain_packs" / "privacy"
    for filename in ("controls.json", "scoring.json", "actions.json"):
        with (privacy_dir / filename).open(encoding="utf-8") as source:
            assert isinstance(json.load(source), dict)

@pytest.mark.parametrize(
    ("visible", "expected_result", "expected_summary"),
    [
        (
            {"privacy_link": True, "privacy_information": True},
            "detected",
            "Se detectó un formulario con un enlace visible relacionado con privacidad.",
        ),
        (
            {"privacy_information": True},
            "detected",
            "Se detectó información visible relacionada con privacidad asociada al formulario.",
        ),
        (
            {"privacy_information": False, "consent_mechanism": True},
            "partial",
            "Se detectó una señal visible de consentimiento o aceptación asociada al formulario, sin información de privacidad reconocida en el contexto revisado.",
        ),
        (
            {"privacy_information": False, "consent_mechanism": False},
            "not_detected",
            "En el formulario revisado no se identificaron señales visibles de información de privacidad ni de consentimiento o aceptación.",
        ),
    ],
)
def test_prv104_evidence_summary_matches_observable_state(
    visible, expected_result, expected_summary
):
    source_url = "https://example.com/contact"
    evidence = {
        **visible,
        "source_urls": [source_url],
        "visible_evidence": {
            "type": "personal_data_form",
            "source_url": source_url,
            **visible,
        },
    }
    result = evaluate_control(
        "PRV-104", evidence, {"PRV-101": "detected"}
    )

    assert result["result"] == expected_result
    assert result["evidence_summary"] == expected_summary
