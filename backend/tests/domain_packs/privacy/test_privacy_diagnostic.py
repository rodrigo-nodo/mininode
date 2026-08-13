import json
import sys
from dataclasses import replace
from pathlib import Path

BACKEND_SRC = Path(__file__).resolve().parents[3] / "src"
sys.path.insert(0, str(BACKEND_SRC))

from mininode_api.domain_packs.privacy.diagnostic import run_privacy_diagnostic  # noqa: E402
from mininode_api.domain_packs.privacy.evaluator import evaluate_control  # noqa: E402
from mininode_api.domain_packs.privacy.evidence_adapter import (  # noqa: E402
    CONTROL_CODES, adapt_evidence,
)
from mininode_api.domain_packs.privacy.prioritization import prioritize_findings  # noqa: E402
from mininode_api.domain_packs.privacy.scoring import (  # noqa: E402
    load_scoring, score_privacy,
)
from mininode_api.web_inspector.models import (  # noqa: E402
    ContactEvidence, CookieEvidence, EvidenceContract, FieldEvidence, FormEvidence,
    InspectionEvidence, LinkEvidence, PageEvidence, TargetEvidence, TransportEvidence,
)

CODES = ["PRV-001", "PRV-002", "PRV-101", "PRV-104", "PRV-201", "PRV-301", "PRV-501"]


def complete_contract():
    policy = LinkEvidence("https://example.com/privacy", "Política de privacidad", "https://example.com/")
    form = FormEvidence(
        "https://example.com/contact", "https://example.com/send", "post",
        [FieldEvidence("email", "email", "Correo electrónico", True)], [],
        "Tratamiento de datos personales", [policy],
    )
    return EvidenceContract(
        TargetEvidence("http://example.com/", "https://example.com/", "example.com"),
        InspectionEvidence(5, 4, True, []),
        [PageEvidence("https://example.com/", 200, "Inicio", "text/html"), PageEvidence("https://example.com/privacy", 200, "Privacy", "text/html")],
        TransportEvidence(True, True, True, False), [policy], [form],
        CookieEvidence(True, ["session"], True, True),
        [ContactEvidence("https://example.com/contact", email="hello@example.com")],
    )


def failed_contract():
    return EvidenceContract(
        TargetEvidence("https://example.com/", None, "example.com"),
        InspectionEvidence(3, 0, True, [{"code": "timeout", "message": "Timed out", "url": "https://example.com/"}]),
        [], TransportEvidence(None, None, None, None), [], [],
        CookieEvidence(False, [], False, False), [],
    )


def test_full_contract_runs_complete_privacy_pipeline():
    result = run_privacy_diagnostic(complete_contract())
    assert [control["control_code"] for control in result["controls"]] == CODES
    assert len(result["controls"]) == 7
    assert result["controls"][1]["result"] == "detected"
    assert result["controls"][3]["result"] == "partial"
    assert 0 <= result["score"] <= 100
    assert result["status"] in {item["label"] for item in load_scoring()["ranges"]}
    assert 0 <= result["coverage"] <= 100
    assert len(result["priorities"]) <= 3
    assert result["scope"] == {"pages_requested": 5, "pages_analyzed": 4, "limited": True}
    encoded = json.dumps(result).lower()
    assert "<html" not in encoded
    assert "session" not in encoded
    assert "set-cookie" not in encoded
    assert "impact_weights" not in encoded
    assert "score_weight" not in encoded


def test_technical_failure_is_unscored_not_artificially_penalized():
    result = run_privacy_diagnostic(failed_contract())
    outcomes = {control["control_code"]: control["result"] for control in result["controls"]}
    assert set(outcomes.values()) == {"not_evaluable"}
    assert "not_detected" not in outcomes.values()
    assert result["coverage"] == 0
    assert result["evaluated_controls"] == 0
    assert result["applicable_controls"] == 6
    assert result["score"] == 0
    assert result["priorities"] == []
    assert result["scope"] == {"pages_requested": 3, "pages_analyzed": 0, "limited": True}


def test_source_trace_does_not_change_score_status_coverage_or_priorities():
    traced = complete_contract()
    traced.pages.append(PageEvidence("https://example.com/contact", 200, "Contacto", "text/html"))
    baseline = complete_contract()
    baseline = replace(baseline, forms=[
        FormEvidence(
            "https://example.com/untraced", form.action, form.method, form.fields,
            form.checkboxes, form.nearby_text, form.privacy_links,
        )
        for form in baseline.forms
    ])

    traced_result = run_privacy_diagnostic(traced)
    baseline_result = run_privacy_diagnostic(baseline)

    for field in ("score", "status", "coverage", "evaluated_controls", "applicable_controls"):
        assert traced_result[field] == baseline_result[field]
    assert [item["control_code"] for item in traced_result["priorities"]] == [
        item["control_code"] for item in baseline_result["priorities"]
    ]
    assert len(traced_result["priorities"]) == len(baseline_result["priorities"])
    priority = next(item for item in traced_result["priorities"] if item["control_code"] == "PRV-104")
    assert priority["source_url"] == "https://example.com/contact"


def test_frontend_conditionally_renders_safe_source_path_and_home_label():
    app = (Path(__file__).resolve().parents[4] / "frontend" / "privacy" / "app.js").read_text()

    assert "if (priority.source_url)" in app
    assert "Detectado en: ${page}" in app
    assert "source.pathname === '/' ? 'página principal' : source.pathname" in app
    assert "if (priority.evidence_summary)" in app
    assert "Evidencia: ${priority.evidence_summary}" in app


def test_visible_evidence_metadata_is_strictly_evaluation_invariant():
    contract = complete_contract()
    contract.pages.append(PageEvidence("https://example.com/contact", 200, "Contacto", "text/html"))
    adapted = adapt_evidence(contract)
    baseline = {
        code: {key: value for key, value in evidence.items() if key != "visible_evidence"}
        for code, evidence in adapted.items()
    }

    def evaluate(evidence_by_control):
        results = {}
        for code in CONTROL_CODES:
            results[code] = evaluate_control(code, evidence_by_control[code], results)
        return list(results.values())

    controls = evaluate(adapted)
    baseline_controls = evaluate(baseline)

    for actual, previous in zip(controls, baseline_controls):
        for field in ("control_code", "result", "reason", "confidence"):
            assert actual[field] == previous[field]
    assert score_privacy(controls) == score_privacy(baseline_controls)
    priorities = prioritize_findings(controls)
    baseline_priorities = prioritize_findings(baseline_controls)
    assert [item["control_code"] for item in priorities] == [
        item["control_code"] for item in baseline_priorities
    ]
    assert len(priorities) == len(baseline_priorities)
