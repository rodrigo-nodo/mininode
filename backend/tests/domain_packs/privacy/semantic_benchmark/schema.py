"""Small, dependency-light schema and loader for the benchmark corpus."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


SCHEMA_VERSION = 1
CONTROLS = ("PRV-008", "PRV-010", "PRV-012")
VALID_CLASSES = {
    "PRV-008": frozenset({"concrete", "generic", "none", "not_applicable"}),
    "PRV-010": frozenset(
        {"explicit", "generic", "explicit_none", "none", "not_applicable"}
    ),
    "PRV-012": frozenset({"explicit", "generic", "none", "not_applicable"}),
}
VALID_ROLES = frozenset({"positive", "generic", "negative", "hard_negative"})


def _required(data: dict[str, Any], keys: set[str], label: str) -> None:
    missing = keys - data.keys()
    if missing:
        raise ValueError(f"{label} missing fields: {', '.join(sorted(missing))}")


@dataclass(frozen=True)
class Fixture:
    fixture_id: str
    text: str
    expected_role: str
    reason: str

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Fixture":
        _required(data, {"fixture_id", "text", "expected_role", "reason"}, "fixture")
        fixture = cls(**data)
        if not fixture.fixture_id or not fixture.text or not fixture.reason:
            raise ValueError("fixture text fields cannot be empty")
        if fixture.expected_role not in VALID_ROLES:
            raise ValueError(f"invalid fixture role: {fixture.expected_role}")
        return fixture


@dataclass(frozen=True)
class BenchmarkCase:
    schema_version: int
    corpus_version: str
    policy_id: str
    control: str
    expected_class: str
    rationale: str
    evidence: tuple[Fixture, ...]
    hard_negatives: tuple[Fixture, ...]
    source_type: str
    language: str
    prv003: str

    @classmethod
    def from_dict(
        cls, data: dict[str, Any], fixtures: dict[str, Fixture]
    ) -> "BenchmarkCase":
        required = {
            "schema_version", "corpus_version", "policy_id", "control",
            "expected_class", "rationale", "evidence", "hard_negatives",
            "source_type", "language", "prv003",
        }
        _required(data, required, "case")
        control = data["control"]
        if control not in CONTROLS:
            raise ValueError(f"unsupported control: {control}")
        if data["expected_class"] not in VALID_CLASSES[control]:
            raise ValueError(
                f"invalid class {data['expected_class']!r} for {control}"
            )
        if data["schema_version"] != SCHEMA_VERSION:
            raise ValueError(f"unsupported schema version: {data['schema_version']}")
        if data["prv003"] not in {"detected", "not_detected"}:
            raise ValueError("prv003 must be detected or not_detected")
        if (data["expected_class"] == "not_applicable") != (
            data["prv003"] == "not_detected"
        ):
            raise ValueError("not_applicable cases must model PRV-003 as not_detected")

        def resolve(ids: Any, field: str) -> tuple[Fixture, ...]:
            if not isinstance(ids, list):
                raise ValueError(f"{field} must be a list")
            missing = [fixture_id for fixture_id in ids if fixture_id not in fixtures]
            if missing:
                raise ValueError(f"unknown fixtures in {field}: {missing}")
            return tuple(fixtures[fixture_id] for fixture_id in ids)

        return cls(
            **{key: data[key] for key in required - {"evidence", "hard_negatives"}},
            evidence=resolve(data["evidence"], "evidence"),
            hard_negatives=resolve(data["hard_negatives"], "hard_negatives"),
        )


@dataclass(frozen=True)
class Corpus:
    schema_version: int
    corpus_version: str
    cases: tuple[BenchmarkCase, ...]
    fixtures: tuple[Fixture, ...]


def _read_yaml(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as source:
        data = yaml.safe_load(source)
    if not isinstance(data, dict):
        raise ValueError(f"{path.name} must contain a mapping")
    return data


def load_corpus(directory: Path | None = None) -> Corpus:
    root = directory or Path(__file__).parent
    manifest = _read_yaml(root / "manifest.yaml")
    fixture_data = _read_yaml(root / "fixtures.yaml")
    _required(manifest, {"schema_version", "corpus_version", "cases"}, "manifest")
    _required(fixture_data, {"schema_version", "fixtures"}, "fixtures document")
    if manifest["schema_version"] != fixture_data["schema_version"]:
        raise ValueError("manifest and fixture schema versions differ")
    fixtures_list = [Fixture.from_dict(item) for item in fixture_data["fixtures"]]
    fixture_ids = [item.fixture_id for item in fixtures_list]
    if len(fixture_ids) != len(set(fixture_ids)):
        raise ValueError("fixture IDs must be unique")
    fixtures = {item.fixture_id: item for item in fixtures_list}
    cases = tuple(BenchmarkCase.from_dict(item, fixtures) for item in manifest["cases"])
    case_ids = [(item.policy_id, item.control) for item in cases]
    if len(case_ids) != len(set(case_ids)):
        raise ValueError("(policy_id, control) case IDs must be unique")
    if any(item.corpus_version != manifest["corpus_version"] for item in cases):
        raise ValueError("case corpus versions must match the manifest")
    return Corpus(
        schema_version=manifest["schema_version"],
        corpus_version=manifest["corpus_version"],
        cases=cases,
        fixtures=tuple(fixtures_list),
    )
