from __future__ import annotations

from dataclasses import replace

import pytest

from backend.tests.domain_packs.privacy.prv103_semantic_benchmark.intent_llm_runner import (
    CaseResult,
    EvidenceItem,
    IntentOutput,
    catalog_for_model,
    decision,
    final_class_for,
    load_json,
    metrics,
    output_schema,
    stability,
    validate_output,
    TAXONOMY_PATH,
)


def taxonomy():
    return load_json(TAXONOMY_PATH)


def case(**overrides):
    base = {
        "id": "T-001",
        "source_cycle": "TEST",
        "split": "dev",
        "heading": "Reserva tu hora",
        "legend": None,
        "introductory_text": None,
        "submit_text": "Agendar cita",
        "gold": "concrete",
    }
    base.update(overrides)
    return base


def result(final_class="concrete", gold="concrete", **overrides):
    base = CaseResult(
        case_id="T-001",
        source_cycle="TEST",
        split="dev",
        gold=gold,
        baseline_v07=None,
        intent_id="appointment_booking",
        final_class=final_class,
        evidence=(EvidenceItem("heading", "Reserva tu hora"),),
        reason_short="La evidencia indica una reserva de hora.",
        uncertain=False,
        valid_output=True,
        validation_error=None,
        input_tokens=10,
        output_tokens=5,
        reasoning_tokens=2,
        latency_seconds=0.1,
        resolved_model="test",
    )
    return replace(base, **overrides)


def test_catalog_hides_product_classes_from_model():
    catalog = catalog_for_model(taxonomy())
    assert catalog
    assert set(catalog[0]) == {"intent_id", "examples"}
    assert all("class" not in item for item in catalog)


def test_schema_allows_only_frozen_intents_and_fields():
    schema = output_schema(taxonomy())
    ids = schema["properties"]["intent_id"]["enum"]
    fields = schema["properties"]["evidence"]["items"]["properties"]["field"]["enum"]
    assert "appointment_booking" in ids
    assert fields == ["heading", "legend", "introductory_text", "submit_text"]
    assert schema["additionalProperties"] is False


def test_validate_output_requires_literal_evidence_from_cited_field():
    raw = {
        "intent_id": "appointment_booking",
        "evidence": [{"field": "heading", "quote": "Reserva tu hora"}],
        "reason_short": "La finalidad visible es reservar una hora.",
        "uncertain": False,
    }
    parsed = validate_output(raw, case(), taxonomy())
    assert parsed.intent_id == "appointment_booking"
    assert parsed.evidence == (EvidenceItem("heading", "Reserva tu hora"),)

    raw["evidence"] = [{"field": "heading", "quote": "Pagar cuenta"}]
    with pytest.raises(ValueError, match="not present"):
        validate_output(raw, case(), taxonomy())


def test_validate_output_rejects_empty_or_duplicated_evidence_fields():
    raw = {
        "intent_id": "appointment_booking",
        "evidence": [
            {"field": "heading", "quote": "Reserva tu hora"},
            {"field": "heading", "quote": "Reserva"},
        ],
        "reason_short": "Hay una finalidad visible.",
        "uncertain": False,
    }
    with pytest.raises(ValueError, match="duplicated"):
        validate_output(raw, case(), taxonomy())

    raw["evidence"] = [{"field": "legend", "quote": "Reserva"}]
    with pytest.raises(ValueError, match="empty field"):
        validate_output(raw, case(), taxonomy())


def test_uncertain_always_abstains_to_unknown():
    output = IntentOutput(
        "appointment_booking",
        (EvidenceItem("heading", "Reserva tu hora"),),
        "La intención parece una reserva.",
        True,
    )
    assert final_class_for(output, taxonomy()) == "unknown"


def test_metrics_and_decision_treat_false_concrete_as_risky():
    rows = [
        result(case_id="A", final_class="concrete", gold="generic"),
        result(case_id="B", final_class="generic", gold="generic", intent_id="contact_generic"),
    ]
    quality = metrics(rows)
    stable = {
        "class_stability": 1.0,
        "intent_stability": 1.0,
        "uncertain_stability": 1.0,
        "evidence_stability": 1.0,
    }
    assert quality["false_concrete_promotions"] == 1
    assert decision(quality, stable) == "D_RISKY"


def test_stability_compares_intent_class_uncertainty_and_evidence():
    left = [result(case_id="A")]
    right = [result(case_id="A")]
    same = stability(left, right)
    assert same["class_stability"] == 1.0
    assert same["intent_stability"] == 1.0
    assert same["evidence_stability"] == 1.0

    changed = [result(case_id="A", intent_id="specific_service_request")]
    diff = stability(left, changed)
    assert diff["class_stability"] == 1.0
    assert diff["intent_stability"] == 0.0
    assert diff["differences"][0]["id"] == "A"
