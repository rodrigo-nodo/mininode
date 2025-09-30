from fastapi import Header, HTTPException
import os

def _load_keys() -> set[str]:
    keys: set[str] = set()
    k1 = os.getenv("API_KEY")
    if k1:
        keys.add(k1.strip())
    klist = os.getenv("API_KEYS")
    if klist:
        keys.update(s.strip() for s in klist.split(",") if s.strip())
    return keys

def require_api_key(x_api_key: str | None = Header(default=None, alias="X-Api-Key")):
    keys = _load_keys()
    # Si no hay claves configuradas, dejamos pasar (dev). En prod, define API_KEY / API_KEYS.
    if not keys:
        return True
    if not x_api_key or x_api_key not in keys:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return True

