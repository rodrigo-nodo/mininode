from mininode_api.domain_packs.privacy.declared_processing import MAX_OUTPUT_TOKENS

from .run import QA_BUDGET_USD


def test_qa2_cost_guard_tracks_frozen_output_limit():
    assert MAX_OUTPUT_TOKENS == 8192
    assert QA_BUDGET_USD == 2.00
