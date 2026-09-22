from pathlib import Path


def test_qa_runner_has_cost_guards():
    text = Path("backend/tests/domain_packs/privacy/declared_processing_qa1/run.py").read_text(encoding="utf-8")
    assert "QA_EXECUTION_SHA" in text
    assert "executed_sha.txt" in text
    assert "INFRASTRUCTURE_ERRORS" in text
    assert "fail-fast after infrastructure error" in text
    assert "QA_BUDGET_USD=5.00" in text
    assert "INPUT_USD_PER_MILLION=4.00" in text
    assert "OUTPUT_USD_PER_MILLION=20.00" in text
    assert "budget_stopped" in text
    assert "estimated_cost_usd" in text


def test_stable_workflow_has_sha_concurrency_and_duplicate_guard():
    text = Path(".github/workflows/privacy-declared-processing-qa.yml").read_text(encoding="utf-8")
    assert "group: privacy-declared-processing-qa-${{ github.event.workflow_run.head_sha }}" in text
    assert "Refuse duplicate QA for this SHA" in text
    assert "QA_EXECUTION_SHA=" in text
