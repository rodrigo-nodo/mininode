"""Versioned Privacy Data catalog access."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

CATALOG_VERSION = "1"

SECURITY_MEASURES = [
    {"code": "passwords_device_lock", "label": "Contraseñas o bloqueo de dispositivos"},
    {"code": "individual_accounts", "label": "Usuarios o cuentas individuales"},
    {"code": "two_factor_auth", "label": "Verificación en dos pasos"},
    {"code": "backups", "label": "Copias de respaldo"},
    {"code": "updates_antivirus", "label": "Actualizaciones y antivirus"},
    {"code": "encryption", "label": "Cifrado o protección adicional de archivos"},
    {"code": "locked_storage", "label": "Archivadores o espacios cerrados"},
    {"code": "none", "label": "No tengo medidas definidas"},
    {"code": "unknown", "label": "No estoy seguro"},
]


@lru_cache(maxsize=1)
def get_catalog() -> dict:
    path = Path(__file__).with_name("v1.json")
    catalog = json.loads(path.read_text(encoding="utf-8"))
    catalog["security_measures"] = SECURITY_MEASURES
    return catalog
