import json
import sys
from pathlib import Path

BACKEND_SRC = Path(__file__).resolve().parents[3] / "src"
sys.path.insert(0, str(BACKEND_SRC))

from mininode_api.domain_packs.privacy.diagnostic import run_privacy_diagnostic  # noqa: E402
from mininode_api.domain_packs.privacy.scoring import load_scoring  # noqa: E402
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
