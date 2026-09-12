import importlib.util
from pathlib import Path

import pytest

MODULE_PATH = Path(__file__).with_name("precheck_prv103_holdout.py")
spec = importlib.util.spec_from_file_location("holdout_precheck", MODULE_PATH)
holdout_precheck = importlib.util.module_from_spec(spec)
spec.loader.exec_module(holdout_precheck)


def test_normalize_hostname_ignores_scheme_www_path_and_trailing_dot():
    assert holdout_precheck.normalize_hostname("https://www.Example.com/contact") == "example.com"
    assert holdout_precheck.normalize_hostname("example.com./") == "example.com"


def test_load_domains_requires_exactly_99_unique_normalized_hosts(tmp_path):
    valid = tmp_path / "valid.txt"
    valid.write_text("\n".join(f"site-{number}.example" for number in range(99)))
    assert len(holdout_precheck.load_domains(valid)) == 99

    duplicate = tmp_path / "duplicate.txt"
    duplicate.write_text("\n".join(["example.com", "www.example.com", *[f"site-{number}.example" for number in range(97)]]))
    with pytest.raises(ValueError, match="unique"):
        holdout_precheck.load_domains(duplicate)


def test_frozen_pool_has_99_unique_hosts_and_excludes_issue_223():
    candidates = MODULE_PATH.parents[2] / "docs/evidence/prv103-holdout-0.9-candidates.txt"
    domains = holdout_precheck.load_domains(candidates)

    assert len(domains) == 99
    assert len(set(domains)) == 99
    assert len(holdout_precheck.ISSUE_223_EXCLUSIONS) == 100
    assert set(domains).isdisjoint(holdout_precheck.ISSUE_223_EXCLUSIONS)
