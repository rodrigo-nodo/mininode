# backend/src/mininode_api/core/auth.py
from fastapi import Depends, Header, HTTPException
import os

def _load_keys() -> set[str]:
    keys = set()
    k1 = os.getenv("API_KEY")
    if k1:
        keys.add(k1.strip())
    klist = os.getenv("API_KEYS")
    if klist:
        keys.update(s.strip() for s in klist.split(",") if s.strip())
    return keys

def require_api_key(x_api_key: str | None = Header(default=None, alias="X-Api-Key")):
    keys = _load_keys()
    if not keys:   # en dev, si no hay claves configuradas, deja pasar
        return True
    if not x_api_key or x_api_key not in keys:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return True

