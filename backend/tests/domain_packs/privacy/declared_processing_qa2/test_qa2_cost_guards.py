import importlib.util
from pathlib import Path

import pytest

from mininode_api.domain_packs.privacy.declared_processing import MAX_OUTPUT_TOKENS


RUNNER = Path(__file__).with_name("run.py")
_SPEC = importlib.util.spec_from_file_location("declared_processing_qa2_run", RUNNER)
assert _SPEC is not None and _SPEC.loader is not None
_RUN = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_RUN)

QA_BUDGET_USD = _RUN.QA_BUDGET_USD
_accounted_call_cost = _RUN._accounted_call_cost
_may_start_call = _RUN._may_start_call


def test_qa2_cost_guard_tracks_frozen_output_limit():
    assert MAX_OUTPUT_TOKENS == 8192
    assert QA_BUDGET_USD == 2.00


def test_valid_response_without_usage_consumes_full_ceiling_and_blocks_next_call():
    call_ceiling = 1.01
    first_call_cost = _accounted_call_cost({}, call_ceiling)

    assert first_call_cost == call_ceiling
    assert _may_start_call(0.0, call_ceiling)
    assert not _may_start_call(first_call_cost, call_ceiling)


def test_invalid_or_unknown_usage_consumes_full_ceiling():
    call_ceiling = 0.42
    assert _accounted_call_cost({}, call_ceiling) == call_ceiling


def test_provider_usage_is_accounted_at_frozen_prices():
    call_ceiling = 1.50
    usage = {"input_tokens": 100_000, "output_tokens": 10_000}
    assert _accounted_call_cost(usage, call_ceiling) == pytest.approx(0.6)


def test_next_call_is_allowed_only_within_total_budget():
    assert _may_start_call(1.0, 1.0)
    assert not _may_start_call(1.01, 1.0)


def test_attempt_marker_is_persisted_before_inference_loop():
    source = RUNNER.read_text(encoding="utf-8")
    marker_write = source.index('marker.write_text(execution_sha + "\\\\n"')
    inference_loop = source.index("for row in manifest:")
    assert marker_write < inference_loop


def test_input_ceiling_uses_full_serialized_request():
    source = RUNNER.read_text(encoding="utf-8")
    assert "request = request_kwargs(doc)" in source
    assert "input_tokens_ceiling = max(1, request_bytes)" in source
    assert "len(text.encode" not in source
