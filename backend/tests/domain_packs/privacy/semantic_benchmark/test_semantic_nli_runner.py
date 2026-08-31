from .semantic_nli_runner import (
    CLASS_MARGIN, ENTAILMENT_THRESHOLD, Candidate, choose_class, combine_scores,
    hypotheses_for, metrics_for, run_case,
)
from .schema import load_corpus


def _scores(entailments):
    return [
        {"entailment": value, "neutral": 1.0 - value, "contradiction": 0.0}
        for value in entailments
    ]


def test_hypotheses_cover_every_semantic_assertion_without_none():
    assert {label for label, _ in hypotheses_for("PRV-008")} == {"concrete", "generic"}
    assert {label for label, _ in hypotheses_for("PRV-010")} == {"explicit", "generic", "explicit_none"}
    assert {label for label, _ in hypotheses_for("PRV-012")} == {"explicit", "generic"}
    assert all(text.startswith("El texto afirma") or text.startswith("El texto establece")
               for control in ("PRV-008", "PRV-010", "PRV-012")
               for _, text in hypotheses_for(control))


def test_combination_keeps_best_fixture_per_class():
    document = load_corpus().documents["emol"][:2]
    # PRV-008 has three hypotheses per fixture: concrete, concrete, generic.
    candidates = combine_scores(
        "PRV-008", document, _scores([0.10, 0.20, 0.30, 0.91, 0.80, 0.40])
    )
    assert candidates[0].semantic_class == "concrete"
    assert candidates[0].fixture == document[1]
    assert candidates[0].entailment == 0.91


def test_score_mapping_requires_explicit_threshold_and_margin():
    fixture = load_corpus().fixtures[0]
    strong = Candidate("explicit", fixture, ENTAILMENT_THRESHOLD, 0.2, 0.1)
    weak = Candidate(
        "generic", fixture, ENTAILMENT_THRESHOLD - CLASS_MARGIN - 0.01, 0.3, 0.1
    )
    assert choose_class([strong, weak]) == strong
    assert choose_class([Candidate("explicit", fixture, ENTAILMENT_THRESHOLD - 0.01, 0.3, 0.1)]) is None
    assert choose_class([strong, Candidate("generic", fixture, strong.entailment - CLASS_MARGIN / 2, 0.2, 0.1)]) is None


def test_prv003_gate_returns_not_applicable_without_inference():
    corpus = load_corpus()
    case = next(case for case in corpus.cases if case.policy_id == "sip")
    called = False

    def scorer(_pairs):
        nonlocal called
        called = True
        return []

    result, inferences = run_case(case, corpus.documents[case.policy_id], scorer)
    assert result.predicted_class == "not_applicable"
    assert result.match
    assert inferences == 0
    assert not called


def test_explicit_none_can_win_and_returns_document_evidence():
    corpus = load_corpus()
    case = next(case for case in corpus.cases if case.policy_id == "banking_01" and case.control == "PRV-010")
    document = corpus.documents[case.policy_id]
    hypothesis_count = len(hypotheses_for(case.control))

    def scorer(pairs):
        values = [0.05] * len(pairs)
        values[0] = 0.94  # explicit_none is the first ordered hypothesis.
        return _scores(values)

    result, inferences = run_case(case, document, scorer)
    assert result.predicted_class == "explicit_none"
    assert result.match
    assert result.evidence_fixture_id in {fixture.fixture_id for fixture in document}
    assert result.evidence_text in {fixture.text for fixture in document}
    assert inferences == len(document) * hypothesis_count


def test_metric_integration_uses_baseline_error_definitions():
    corpus = load_corpus()
    cases = [case for case in corpus.cases if case.policy_id == "sip"]
    results = [run_case(case, corpus.documents["sip"], lambda _: [])[0] for case in cases]
    metrics = metrics_for(results)
    assert metrics["total_cases"] == 3
    assert metrics["exact_matches"] == 3
    assert metrics["false_positive_promotions"] == 0
    assert metrics["semantic_polarity_errors"] == 0
