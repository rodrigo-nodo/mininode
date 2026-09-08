from pathlib import Path
import importlib.util
import json
import sys

HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("prv103_semantic_runner", HERE / "runner.py")
runner = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = runner
SPEC.loader.exec_module(runner)


def test_corpus_is_blind_minimized_and_split_by_qa_cycle():
    corpus = json.loads((HERE / "corpus.json").read_text(encoding="utf-8"))
    assert corpus["corpus_version"] == "prv103-semantic-v1-2026-09-08"
    assert corpus["allowed_fields"] == ["heading", "legend", "introductory_text", "submit_text"]
    dev = [case for case in corpus["cases"] if case["split"] == "dev"]
    evaluation = [case for case in corpus["cases"] if case["split"] == "eval"]
    assert len(dev) == 37
    assert len(evaluation) == 32
    assert {case["source_cycle"] for case in dev} == {"QA4"}
    assert {case["source_cycle"] for case in evaluation} == {"QA5"}
    for case in corpus["cases"]:
        assert case["gold"] in runner.LABELS
        assert "url" not in case
        assert "hostname" not in case
        assert "organization" not in case


def test_eval_keeps_frozen_v07_baseline():
    corpus = json.loads((HERE / "corpus.json").read_text(encoding="utf-8"))
    evaluation = [case for case in corpus["cases"] if case["split"] == "eval"]
    assert all(case.get("baseline_v07") in runner.LABELS for case in evaluation)
    metrics = runner.baseline_metrics(evaluation)
    assert metrics["total"] == 32
    assert metrics["exact"] == 16
    assert metrics["accuracy"] == 0.5
    assert metrics["false_concrete_promotions"] == 2
    assert metrics["false_adverse_none"] == 0


def test_taxonomy_has_closed_intent_to_class_mapping():
    taxonomy = json.loads((HERE / "intent_taxonomy.json").read_text(encoding="utf-8"))
    ids = [intent["id"] for intent in taxonomy["intents"]]
    assert len(ids) == len(set(ids))
    assert all(intent["class"] in runner.LABELS for intent in taxonomy["intents"])
    assert all(intent["prototypes"] for intent in taxonomy["intents"])


def test_selective_prediction_abstains_on_low_score_or_margin():
    case = runner.ScoredCase("x", "concrete", "quote_request", "concrete", 0.70, 0.03)
    assert runner.selective_prediction(case, 0.65, 0.02) == "concrete"
    assert runner.selective_prediction(case, 0.75, 0.02) == "unknown"
    assert runner.selective_prediction(case, 0.65, 0.05) == "unknown"


def test_unknown_intent_never_emits_a_stronger_class():
    case = runner.ScoredCase("x", "unknown", "ambiguous_action", "unknown", 0.99, 0.50)
    assert runner.selective_prediction(case, 0.20, 0.0) == "unknown"


def test_metrics_count_safety_errors_and_coverage():
    m = runner.metrics([
        ("concrete", "generic"),
        ("none", "unknown"),
        ("generic", "generic"),
        ("unknown", "concrete"),
    ])
    assert m["false_concrete_promotions"] == 1
    assert m["false_adverse_none"] == 1
    assert m["coverage"] == 0.75
    assert m["exact"] == 1


def test_threshold_selection_prioritizes_safety_and_precision():
    dev = [
        runner.ScoredCase("a", "concrete", "quote_request", "concrete", 0.80, 0.20),
        runner.ScoredCase("b", "generic", "contact_generic", "generic", 0.78, 0.18),
        runner.ScoredCase("c", "generic", "quote_request", "concrete", 0.45, 0.01),
        runner.ScoredCase("d", "unknown", "ambiguous_action", "unknown", 0.90, 0.30),
    ]
    chosen = runner.choose_thresholds(dev)
    assert chosen["dev_metrics"]["false_concrete_promotions"] == 0
    assert chosen["dev_metrics"]["false_adverse_none"] == 0
    assert chosen["dev_metrics"]["emitted_precision"] >= 0.90
