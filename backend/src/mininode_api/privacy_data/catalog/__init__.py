"""Versioned Privacy Data catalog access."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

CATALOG_VERSION = "1"


def _extend_phase_two_retention(catalog: dict) -> dict:
    """Keep catalog v1 compatible while Phase 2 adds an explicit no-policy answer."""
    statuses = catalog["retention"]["statuses"]
    defined = next((item for item in statuses if item["code"] == "defined"), None)
    if defined is not None:
        defined["label"] = "Sí, tengo un plazo definido"
    if not any(item["code"] == "not_defined" for item in statuses):
        unknown_index = next(
            (index for index, item in enumerate(statuses) if item["code"] == "unknown"),
            len(statuses),
        )
        statuses.insert(
            unknown_index,
            {"code": "not_defined", "label": "No lo tengo definido"},
        )
    return catalog


@lru_cache(maxsize=1)
def get_catalog() -> dict:
    path = Path(__file__).with_name("v1.json")
    catalog = json.loads(path.read_text(encoding="utf-8"))
    return _extend_phase_two_retention(catalog)
