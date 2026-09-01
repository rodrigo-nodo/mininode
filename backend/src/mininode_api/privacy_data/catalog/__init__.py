"""Versioned Privacy Data catalog access."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

CATALOG_VERSION = "1"


@lru_cache(maxsize=1)
def get_catalog() -> dict:
    path = Path(__file__).with_name("v1.json")
    return json.loads(path.read_text(encoding="utf-8"))
