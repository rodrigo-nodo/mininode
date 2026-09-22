from mininode_api.domain_packs.privacy.declared_processing import MAX_OUTPUT_TOKENS

from .run import QA_BUDGET_USD


def test_qa2_cost_guard_tracks_frozen_output_limit():
    assert MAX_OUTPUT_TOKENS == 8192
    assert QA_BUDGET_USD == 2.00


def test_qa2_hard_guard_uses_actual_cumulative_cost():
    source = (__import__("pathlib").Path(__file__).with_name("run.py")).read_text(encoding="utf-8")
    assert "actual_cost_usd + call_ceiling > QA_BUDGET_USD" in source
    assert "reserved_cost_usd + call_ceiling" not in source
