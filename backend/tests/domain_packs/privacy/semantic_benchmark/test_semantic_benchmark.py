from pathlib import Path

import pytest

from .runner import (
    CaseResult, _contract, calculate_metrics, document_text, run_benchmark,
)
from .schema import BenchmarkCase, CONTROLS, Fixture, load_corpus


ROOT = Path(__file__).parent


def test_manifest_loads_complete_versioned_golden_set():
    corpus = load_corpus()

    assert corpus.schema_version == 1
    assert corpus.corpus_version == "w2s2a-2026-02"
    assert len(corpus.cases) == 36
    assert len({case.policy_id for case in corpus.cases}) == 12
    assert {case.control for case in corpus.cases} == set(CONTROLS)


def test_schema_rejects_invalid_class_and_control():
    corpus = load_corpus()
    raw = {
        "schema_version": 1,
        "corpus_version": corpus.corpus_version,
        "policy_id": "invalid",
        "control": "PRV-008",
        "expected_class": "arbitrary",
        "rationale": "Test inválido.",
        "evidence": [],
        "hard_negatives": [],
        "source_type": "synthetic_equivalent",
        "language": "es",
        "prv003": "detected",
    }
    fixtures = {fixture.fixture_id: fixture for fixture in corpus.fixtures}

    with pytest.raises(ValueError, match="invalid class"):
        BenchmarkCase.from_dict(raw, fixtures)
    with pytest.raises(ValueError, match="unsupported control"):
        BenchmarkCase.from_dict({**raw, "control": "PRV-999"}, fixtures)


def test_fixture_ids_are_unique_and_all_references_resolve():
    corpus = load_corpus()
    fixture_ids = [fixture.fixture_id for fixture in corpus.fixtures]

    assert len(fixture_ids) == len(set(fixture_ids))
    assert all(
        isinstance(fixture, Fixture)
        for case in corpus.cases
        for fixture in case.evidence + case.hard_negatives
    )
    assert set(corpus.documents) == {case.policy_id for case in corpus.cases}


def test_policy_cases_share_one_complete_document_with_cross_control_distractors():
    corpus = load_corpus()
    for policy_id in corpus.documents:
        texts = {
            _contract(case, corpus.documents[case.policy_id]).pages[0].content_text
            for case in corpus.cases
            if case.policy_id == policy_id
        }
        assert len(texts) == 1

    emol_recipients = next(
        case for case in corpus.cases
        if case.policy_id == "emol" and case.control == "PRV-010"
    )
    emol_document_ids = {
        fixture.fixture_id for fixture in corpus.documents["emol"]
    }
    assert "emol-prv-008-e01" in emol_document_ids
    assert "emol-prv-008-e01" not in {
        fixture.fixture_id
        for fixture in emol_recipients.evidence + emol_recipients.hard_negatives
    }


def test_each_control_has_positive_negative_and_hard_negative_cases():
    corpus = load_corpus()
    positive_classes = {
        "PRV-008": {"concrete", "generic"},
        "PRV-010": {"explicit", "generic", "explicit_none"},
        "PRV-012": {"explicit", "generic"},
    }
    for control in CONTROLS:
        cases = [case for case in corpus.cases if case.control == control]
        assert any(case.expected_class in positive_classes[control] for case in cases)
        assert any(case.expected_class == "none" for case in cases)
        assert any(case.hard_negatives for case in cases)


def test_sip_dependency_produces_not_applicable_in_evaluator_baseline():
    corpus = load_corpus()
    sip_cases = [case for case in corpus.cases if case.policy_id == "sip"]
    results = run_benchmark(sip_cases)

    assert {result.control for result in results} == set(CONTROLS)
    assert all(result.actual_class == "not_applicable" for result in results)
    assert all(result.match for result in results)


def test_baseline_runner_executes_every_case_and_metrics_are_consistent():
    results = run_benchmark()
    metrics = calculate_metrics(results)

    assert len(results) == 36
    assert metrics["total_cases"] == 36
    assert metrics["exact_matches"] + metrics["mismatches"] == 36
    assert set(metrics["per_control"]) == set(CONTROLS)
    assert sum(item["count"] for item in metrics["confusion_counts"]) == 36
    assert 0.0 <= metrics["macro_precision"] <= 1.0
    assert 0.0 <= metrics["macro_recall"] <= 1.0


def test_direction_and_semantic_polarity_metrics_are_kept_separate():
    rows = [
        CaseResult("a", "PRV-008", "none", "generic", False),
        CaseResult("b", "PRV-010", "generic", "explicit", False),
        CaseResult("c", "PRV-012", "explicit", "none", False),
        CaseResult("d", "PRV-010", "explicit_none", "explicit", False),
        CaseResult("e", "PRV-010", "explicit", "explicit_none", False),
        CaseResult("f", "PRV-010", "none", "explicit_none", False),
        CaseResult("g", "PRV-008", "concrete", "concrete", True),
    ]

    metrics = calculate_metrics(rows)

    assert metrics["false_positive_promotions"] == 2
    assert metrics["false_negative_omissions"] == 1
    assert metrics["semantic_polarity_errors"] == 2


def test_fixtures_are_short_synthetic_plain_text():
    corpus = load_corpus()

    assert all(len(fixture.text) < 1000 for fixture in corpus.fixtures)
    assert all("<html" not in fixture.text.lower() for fixture in corpus.fixtures)
    assert all("<!doctype" not in fixture.text.lower() for fixture in corpus.fixtures)
    assert max(len(fixture.text) for fixture in corpus.fixtures) < 250
    assert all(
        len(document_text(document)) < 1000
        and "<html" not in document_text(document).lower()
        and "<!doctype" not in document_text(document).lower()
        for document in corpus.documents.values()
    )
