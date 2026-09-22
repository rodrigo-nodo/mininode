from pathlib import Path

from mininode_api.domain_packs.privacy.declared_processing import MAX_OUTPUT_TOKENS


RUNNER = Path(__file__).with_name("run.py")


def test_qa2_cost_guard_tracks_frozen_output_limit():
    source = RUNNER.read_text(encoding="utf-8")
    assert MAX_OUTPUT_TOKENS == 8192
    assert "QA_BUDGET_USD = 2.00" in source


def test_qa2_hard_guard_uses_actual_cumulative_cost():
    source = RUNNER.read_text(encoding="utf-8")
    assert "actual_cost_usd + call_ceiling > QA_BUDGET_USD" in source
    assert "reserved_cost_usd + call_ceiling" not in source
