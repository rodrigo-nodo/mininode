import re
import sys
from pathlib import Path


BACKEND_SRC = Path(__file__).resolve().parents[3] / "src"
sys.path.insert(0, str(BACKEND_SRC))

from mininode_api.domain_packs.privacy.evaluator import load_controls  # noqa: E402
from mininode_api.domain_packs.privacy.prioritization import (  # noqa: E402
    load_actions,
    prioritize_findings,
)


EXPECTED_ACTIONS = {
    "PRV-001": {"not_detected"},
    "PRV-002": {"partial", "not_detected"},
    "PRV-104": {"partial", "not_detected"},
    "PRV-201": {"partial", "not_detected"},
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


def test_action_catalog_has_no_placeholders_dynamic_interpolation_or_defensive_terms():
    forbidden_terms = re.compile(
        r"\b(cumple|incumple|ilegal|obligatorio|garantiza)\b"
        r"|\b(?:es|está|queda) certificado\b",
        re.IGNORECASE,
    )
    placeholders = ("{{", "}}", "${", "<%", "%>", "source_url", "evidence_summary")
    for outcomes in load_actions()["actions"].values():
        for action in outcomes.values():
            texts = [*action["action_steps"], action["validation_step"]]
            assert all(not forbidden_terms.search(text) for text in texts)
            assert all(marker not in text for text in texts for marker in placeholders)


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
