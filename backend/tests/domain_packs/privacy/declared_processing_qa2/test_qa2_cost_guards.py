from pathlib import Path

from mininode_api.domain_packs.privacy.declared_processing import MAX_OUTPUT_TOKENS


RUNNER = Path(__file__).with_name("run.py")


def _source() -> str:
    return RUNNER.read_text(encoding="utf-8")


def test_qa2_cost_guard_tracks_frozen_output_limit():
    source = _source()
    assert MAX_OUTPUT_TOKENS == 8192
    assert "QA_BUDGET_USD = 2.00" in source


def test_qa2_hard_guard_uses_accounted_cumulative_cost():
    source = _source()
    assert "actual_cost_usd + call_ceiling > QA_BUDGET_USD" in source
    assert "actual_cost_usd += call_cost" in source
    assert "actual_cost_usd += call_ceiling" in source


def test_qa2_invalid_output_usage_is_charged():
    source = _source()
    assert "if usage:" in source
    assert '"accounted_cost_usd": round(call_cost, 6)' in source


def test_qa2_unknown_usage_reserves_full_ceiling():
    source = _source()
    assert "call_cost = call_ceiling" in source
    assert "actual_cost_usd += call_ceiling" in source


def test_qa2_attempt_marker_precedes_inference_loop():
    source = _source()
    marker_write = source.index('marker.write_text(execution_sha + "\\\\n"')
    inference_loop = source.index("for row in manifest:")
    assert marker_write < inference_loop


def test_qa2_input_ceiling_includes_full_serialized_request():
    source = _source()
    assert "request = request_kwargs(doc)" in source
    assert "input_tokens_ceiling = max(1, request_bytes)" in source
    assert "len(text.encode" not in source
