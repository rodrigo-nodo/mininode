from dataclasses import replace
import pytest
from .semantic_llm_runner import (INPUT_USD_PER_MILLION, OUTPUT_USD_PER_MILLION, Inference, LlmOutput, compare_stability, compose_hybrid, cost_summary, execute, metrics_for, output_schema, run_case, should_route, validate_output)
from .schema import load_corpus


def _case(policy="commerce_01", control="PRV-008"):
    corpus = load_corpus()
    case = next(x for x in corpus.cases if x.policy_id == policy and x.control == control)
    return case, corpus.documents[policy]


def _fake(predicted="concrete", evidence=(), tokens=(10, 4, 2), uncertain=False):
    return lambda *_: Inference(LlmOutput(predicted, tuple(evidence), "Evidencia observable.", uncertain), *tokens, 0.25)


def _none_client(control, *_):
    return Inference(LlmOutput("none", (), "Sin evidencia observable.", False), 10, 5, 2, 1.0)


def test_output_schema_is_strict_and_control_specific():
    schema = output_schema("PRV-010")
    assert schema["additionalProperties"] is False
    assert set(schema["properties"]["predicted_class"]["enum"]) == {"explicit", "generic", "explicit_none", "none"}


def test_fixture_validation_and_original_evidence_text():
    case, document = _case(); fixture = document[0]
    result = run_case(case, document, "none", _fake(evidence=(fixture.fixture_id,)))
    assert result.llm_evidence_texts == (fixture.text,)
    with pytest.raises(ValueError, match="invalid_output"):
        validate_output(case.control, {"predicted_class": "concrete", "evidence_fixture_ids": ["invented"], "reason_short": "Visible.", "uncertain": False}, document)


@pytest.mark.parametrize("control,bad", [("PRV-008", "explicit"), ("PRV-010", "concrete"), ("PRV-012", "explicit_none")])
def test_class_mapping_by_control(control, bad):
    _, document = _case(control=control)
    with pytest.raises(ValueError, match="invalid_output"):
        validate_output(control, {"predicted_class": bad, "evidence_fixture_ids": [], "reason_short": "Visible.", "uncertain": False}, document)


def test_prv003_gate_skips_client():
    case, document = _case("sip", "PRV-008")
    result = run_case(case, document, "not_applicable", lambda *_: pytest.fail("client called"))
    assert result.llm_class == result.hybrid_class == "not_applicable" and result.input_tokens == 0


@pytest.mark.parametrize("control,kept,routed", [("PRV-008", "concrete", "generic"), ("PRV-010", "explicit_none", "none"), ("PRV-012", "explicit", "generic")])
def test_frozen_routing(control, kept, routed):
    assert not should_route(control, kept)
    assert should_route(control, routed)


def test_hybrid_composition():
    assert compose_hybrid("PRV-008", "none", "concrete") == "concrete"
    assert compose_hybrid("PRV-010", "explicit", "none") == "explicit"
    assert compose_hybrid("PRV-012", "not_applicable", "explicit") == "not_applicable"


def test_one_inference_per_applicable_case_and_metrics_for_all_scenarios():
    calls = 0
    def client(control, *_):
        nonlocal calls; calls += 1
        return _none_client(control)
    rows = execute(client)
    assert len(rows) == 36 and calls == sum(x.rules_class != "not_applicable" for x in rows)
    for field in ("rules_class", "llm_class", "hybrid_class"):
        metrics = metrics_for(rows, field)
        assert metrics["total_cases"] == 36
        assert {"confusion_counts", "false_positive_promotions", "false_negative_omissions", "semantic_polarity_errors"} <= metrics.keys()


def test_invalid_output_is_not_repaired():
    case, document = _case()
    result = run_case(case, document, "none", _fake(evidence=("almost-right",)))
    assert result.llm_class == "invalid_output"
    assert result.llm_evidence_fixture_ids == ()


def test_token_and_cost_aggregation():
    rows = execute(_none_client); applicable = sum(x.input_tokens > 0 for x in rows)
    assert cost_summary(rows)["estimated_usd"] == applicable * (10 * INPUT_USD_PER_MILLION + 5 * OUTPUT_USD_PER_MILLION) / 1_000_000
    assert metrics_for(rows, "llm_class")["reasoning_tokens"] == applicable * 2


def test_stability_reports_every_material_difference():
    row = execute(_none_client)[0]
    changed = replace(row, llm_class="generic", llm_evidence_fixture_ids=("x",), uncertain=True)
    report = compare_stability([row], [changed])
    assert report["stable_classes"] == 0
    assert all(len(report[key]) == 1 for key in ("class_differences", "evidence_differences", "uncertain_differences"))
