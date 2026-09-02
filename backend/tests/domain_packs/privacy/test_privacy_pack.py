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
    "PRV-004": ("Fecha o versión de la política", "bajo", "context"),
    "PRV-005": ("Identificación del responsable", "alto", "conditional_evaluation"),
    "PRV-006": ("Canal para ejercer derechos", "muy_alto", "conditional_evaluation"),
    "PRV-007": ("Categorías de datos tratados", "alto", "conditional_evaluation"),
    "PRV-008": ("Finalidades del tratamiento", "muy_alto", "conditional_evaluation"),
    "PRV-009": ("Base declarada del tratamiento", "bajo", "context"),
    "PRV-010": ("Destinatarios o terceros", "alto", "conditional_evaluation"),
    "PRV-011": ("Derechos del titular", "muy_alto", "conditional_evaluation"),
    "PRV-012": ("Conservación de datos", "medio", "conditional_evaluation"),
    "PRV-013": ("Reclamo ante la Agencia", "alto", "conditional_evaluation"),
    "PRV-014": ("Retiro del consentimiento", "alto", "conditional_evaluation"),
    "PRV-101": ("Formularios que recopilan datos personales", "alto", "context"),
    "PRV-102": ("Envío seguro del formulario", "medio", "conditional_evaluation"),
    "PRV-103": ("Finalidad visible del formulario", "bajo", "context"),
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
    results["PRV-005"] = evaluate_control(
        "PRV-005", {"responsible_identification": "clear"}, results
    )
    results["PRV-006"] = evaluate_control(
        "PRV-006", {"rights_channel": "explicit"}, results
    )
    results["PRV-007"] = evaluate_control(
        "PRV-007", {"data_categories": "concrete"}, results
    )
    results["PRV-010"] = evaluate_control(
        "PRV-010", {"data_recipients": "explicit"}, results
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
    assert len(controls) == 21
    assert {
        control["code"]: (control["name"], control["impact"], control["type"])
        for control in controls
    } == EXPECTED


def test_documental_framework_matches_productive_catalog():
    framework_path = (
        BACKEND_SRC.parents[1]
        / "frontend"
        / "privacy"
        / "data"
        / "privacy-framework-v0.6.json"
    )
    framework_controls = json.loads(framework_path.read_text(encoding="utf-8"))[
        "framework"
    ]["controls"]
    productive_controls = load_controls()

    assert {control["code"] for control in framework_controls} == {
        control["code"] for control in productive_controls
    }
    productive_by_code = {control["code"]: control for control in productive_controls}
    for documented in framework_controls:
        productive = productive_by_code[documented["code"]]
        for shared_field in ("name", "domain", "type", "score_weight", "dependency"):
            assert documented.get(shared_field) == productive.get(shared_field)


def test_documental_framework_keeps_history_and_publishes_v06():
    framework_directory = (
        BACKEND_SRC.parents[1] / "frontend" / "privacy" / "data"
    )
    historical_path = framework_directory / "privacy-framework-v0.1.json"
    v02_path = framework_directory / "privacy-framework-v0.2.json"
    v03_path = framework_directory / "privacy-framework-v0.3.json"
    v04_path = framework_directory / "privacy-framework-v0.4.json"
    v05_path = framework_directory / "privacy-framework-v0.5.json"
    current_path = framework_directory / "privacy-framework-v0.6.json"

    assert historical_path.is_file()
    assert v04_path.is_file()
    historical = json.loads(historical_path.read_text(encoding="utf-8"))["framework"]
    v02 = json.loads(v02_path.read_text(encoding="utf-8"))["framework"]
    v03 = json.loads(v03_path.read_text(encoding="utf-8"))["framework"]
    v04 = json.loads(v04_path.read_text(encoding="utf-8"))["framework"]
    v05 = json.loads(v05_path.read_text(encoding="utf-8"))["framework"]
    current = json.loads(current_path.read_text(encoding="utf-8"))["framework"]

    assert historical["version"] == "0.1"
    assert v02["version"] == "0.2"
    assert v03["version"] == "0.3"
    assert v04["version"] == "0.4"
    assert v05["version"] == "0.5"
    assert current["version"] == "0.6"
    assert "PRV-102" not in {control["code"] for control in historical["controls"]}
    assert "PRV-102" in {control["code"] for control in v02["controls"]}
    assert "PRV-103" not in {control["code"] for control in historical["controls"]}
    assert "PRV-103" not in {control["code"] for control in v02["controls"]}
    assert "PRV-103" in {control["code"] for control in v03["controls"]}
    assert "PRV-103" in {control["code"] for control in v04["controls"]}
    assert "PRV-103" in {control["code"] for control in v05["controls"]}
    assert {"PRV-102", "PRV-103"} <= {control["code"] for control in current["controls"]}


def test_catalog_contains_required_metadata_and_dependencies():
    controls = {control["code"]: control for control in load_controls()}
    assert controls["PRV-101"]["type"] == "context"
    assert controls["PRV-101"]["score_weight"] == 0
    assert controls["PRV-102"]["impact"] == "medio"
    assert controls["PRV-102"]["score_weight"] == 1
    assert controls["PRV-103"]["type"] == "context"
    assert controls["PRV-103"]["score_weight"] == 0
    assert controls["PRV-103"]["dependency"] == "PRV-101"
    assert controls["PRV-004"]["score_weight"] == 0
    assert controls["PRV-004"]["dependency"] == "PRV-003"
    assert controls["PRV-009"]["type"] == "context"
    assert controls["PRV-009"]["score_weight"] == 0
    assert controls["PRV-009"]["dependency"] == "PRV-003"
    assert controls["PRV-002"]["dependency"] == "PRV-001"
    assert controls["PRV-005"]["dependency"] == "PRV-003"
    assert controls["PRV-006"]["dependency"] == "PRV-003"
    assert controls["PRV-007"]["dependency"] == "PRV-003"
    assert controls["PRV-010"]["dependency"] == "PRV-003"
    assert controls["PRV-012"]["dependency"] == "PRV-003"
    assert controls["PRV-013"]["dependency"] == "PRV-003"
    assert controls["PRV-014"]["dependency"] == "PRV-003"
    assert controls["PRV-104"]["dependency"] == "PRV-101"
    for control in controls.values():
        assert control["expected_evidence"]
        assert control["base_recommendation"]
        assert control["criteria"]


def test_catalog_criteria_match_active_evaluator_results():
    active_results = {
        "PRV-001": {"detected", "not_detected", "not_evaluable"},
        "PRV-002": {"detected", "partial", "not_applicable", "not_evaluable"},
        "PRV-003": {"detected", "partial", "not_detected", "not_evaluable"},
        "PRV-004": {"detected", "partial", "not_detected", "not_applicable", "not_evaluable"},
        "PRV-005": {
            "detected", "partial", "not_detected", "not_applicable",
            "not_evaluable",
        },
        "PRV-006": {
            "detected", "partial", "not_detected", "not_applicable",
            "not_evaluable",
        },
        "PRV-007": {
            "detected", "partial", "not_detected", "not_applicable",
            "not_evaluable",
        },
        "PRV-008": {
            "detected", "partial", "not_detected", "not_applicable",
            "not_evaluable",
        },
        "PRV-009": {
            "detected", "partial", "not_detected", "not_applicable",
            "not_evaluable",
        },
        "PRV-010": {
            "detected", "partial", "not_detected", "not_applicable",
            "not_evaluable",
        },
        "PRV-011": {
            "detected", "partial", "not_detected", "not_applicable",
            "not_evaluable",
        },
        "PRV-012": {
            "detected", "partial", "not_detected", "not_applicable",
            "not_evaluable",
        },
        "PRV-013": {
            "detected", "partial", "not_detected", "not_applicable",
            "not_evaluable",
        },
        "PRV-014": {
            "detected", "partial", "not_detected", "not_applicable",
            "not_evaluable",
        },
        "PRV-101": {"detected", "not_detected", "not_evaluable"},
        "PRV-102": {"detected", "not_detected", "not_applicable", "not_evaluable"},
        "PRV-103": {"detected", "partial", "not_detected", "not_applicable", "not_evaluable"},
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
    assert evaluate_control(
        "PRV-102", {"form_transport": "secure"}, {"PRV-101": forms}
    )["result"] == "not_applicable"


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
    assert scored["evaluated_controls"] == 9
    assert scored["applicable_controls"] == 10
    assert scored["coverage"] == 90


@pytest.mark.parametrize(
    ("result", "expected_score"),
    [("detected", 100), ("not_detected", 0)],
)
def test_prv102_score_contribution(result, expected_score):
    scored = score_privacy([{"control_code": "PRV-102", "result": result}])

    assert scored["score"] == expected_score
    assert scored["coverage"] == 100
    assert scored["evaluated_controls"] == 1
    assert scored["applicable_controls"] == 1


def test_prv102_not_applicable_is_excluded_from_scoring_denominator():
    baseline = score_privacy([
        {"control_code": "PRV-501", "result": "detected"},
    ])
    with_prv102 = score_privacy([
        {"control_code": "PRV-501", "result": "detected"},
        {"control_code": "PRV-102", "result": "not_applicable"},
    ])

    assert with_prv102 == baseline
    assert with_prv102["applicable_controls"] == 1


def test_prv102_not_evaluable_is_unscored_and_reduces_coverage():
    scored = score_privacy([
        {"control_code": "PRV-501", "result": "detected"},
        {"control_code": "PRV-102", "result": "not_evaluable"},
    ])

    assert scored["score"] == 100
    assert scored["coverage"] == 50
    assert scored["evaluated_controls"] == 1
    assert scored["applicable_controls"] == 2


def test_context_never_scores():
    detected = score_privacy(
        [{"control_code": "PRV-101", "result": "detected"}]
    )
    not_detected = score_privacy(
        [{"control_code": "PRV-101", "result": "not_detected"}]
    )
    assert detected == not_detected


@pytest.mark.parametrize("result", ["detected", "partial", "not_detected"])
def test_prv009_never_changes_score_or_denominators(result):
    baseline = score_privacy([{"control_code": "PRV-501", "result": "detected"}])
    with_context = score_privacy([
        {"control_code": "PRV-501", "result": "detected"},
        {"control_code": "PRV-009", "result": result},
    ])
    assert with_context == baseline
    assert prioritize_findings([
        {"control_code": "PRV-009", "result": result, "confidence": "high"}
    ]) == []


def test_integral_scenario_returns_the_approved_result():
    assert score_privacy(evaluated_scenario().values()) == {
        "score": 84,
        "status": "Preparación avanzada",
        "coverage": 100,
        "evaluated_controls": 10,
        "applicable_controls": 10,
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


def test_prv004_context_does_not_modify_privacy_score():
    baseline = [{"control_code": "PRV-001", "result": "detected"}]
    expected = score_privacy(baseline)
    for result in ("detected", "partial", "not_detected"):
        assert score_privacy([
            *baseline, {"control_code": "PRV-004", "result": result}
        ]) == expected


@pytest.mark.parametrize("result", [
    "detected", "partial", "not_detected", "not_evaluable", "not_applicable",
])
def test_prv103_never_modifies_score_or_coverage(result):
    baseline = [{"control_code": "PRV-501", "result": "detected"}]
    assert score_privacy(baseline) == score_privacy([
        *baseline, {"control_code": "PRV-103", "result": result},
    ])


def test_prv103_dependency_and_consumer_summaries():
    evidence = {"form_purpose": "concrete", "confidence": "high"}
    assert evaluate_control("PRV-103", evidence, {"PRV-101": "not_detected"})["result"] == "not_applicable"
    assert evaluate_control("PRV-103", evidence, {"PRV-101": "not_evaluable"})["result"] == "not_evaluable"
    result = evaluate_control("PRV-103", evidence, {"PRV-101": "detected"})
    assert result["evidence_summary"] == "Se detectó una finalidad concreta asociada al formulario."


def test_prv103_is_never_an_actionable_priority():
    results = [
        {"control_code": "PRV-103", "result": result, "confidence": "high"}
        for result in ("partial", "not_detected")
    ]
    assert prioritize_findings(results, limit=20) == []


@pytest.mark.parametrize(("result", "score"), [
    ("detected", 100), ("partial", 50), ("not_detected", 0),
])
def test_prv013_uses_normal_high_impact_scoring(result, score):
    assert score_privacy([{"control_code": "PRV-013", "result": result}])["score"] == score


def test_prv014_scores_when_applicable_and_is_excluded_otherwise():
    baseline = [{"control_code": "PRV-013", "result": "not_detected"}]
    assert score_privacy(baseline) == score_privacy([
        *baseline, {"control_code": "PRV-014", "result": "not_applicable"},
    ])
    assert score_privacy([{"control_code": "PRV-014", "result": "detected"}])["score"] == 100
