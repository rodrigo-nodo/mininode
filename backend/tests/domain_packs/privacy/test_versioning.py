import sys
from pathlib import Path

import pytest


BACKEND_SRC = Path(__file__).resolve().parents[3] / "src"
sys.path.insert(0, str(BACKEND_SRC))

from mininode_api.domain_packs.privacy.evaluator import load_control_catalog  # noqa: E402
from mininode_api.domain_packs.privacy.scoring import load_scoring  # noqa: E402
from mininode_api.domain_packs.privacy.versioning import (  # noqa: E402
    diagnostic_comparability,
    diagnostic_versions,
)


def test_canonical_catalogs_expose_current_versions():
    assert load_control_catalog()["version"] == "0.9"
    assert load_scoring()["version"] == "0.1"
    assert diagnostic_versions() == {
        "framework_version": "0.9",
        "scoring_version": "0.1",
    }


@pytest.mark.parametrize(
    ("original", "current", "status", "reason"),
    [
        (("0.1", "0.1"), ("0.1", "0.1"), "comparable", None),
        (("0.8", "0.1"), ("0.9", "0.1"), "not_comparable", "framework_version_mismatch"),
        (("0.1", "0.1"), ("0.1", "0.2"), "not_comparable", "scoring_version_mismatch"),
        ((None, None), ("0.1", "0.1"), "not_comparable", "missing_version"),
        (("0.1", "0.1"), (None, None), "not_comparable", "missing_version"),
    ],
)
def test_diagnostic_comparability(original, current, status, reason):
    keys = ("framework_version", "scoring_version")
    original_snapshot = dict(zip(keys, original)) if original[0] is not None else {}
    current_snapshot = dict(zip(keys, current)) if current[0] is not None else {}

    result = diagnostic_comparability(original_snapshot, current_snapshot)

    assert result["status"] == status
    assert result["reason"] == reason
