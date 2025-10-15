# -*- coding: utf-8 -*-
# mininode_api/core/http_fetcher.py
from __future__ import annotations
import httpx

BROWSER_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "es-ES,es;q=0.9,en;q=0.8",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
}

CF_PATTERNS = (
    "cf-browser-verification",
    "cf-error-details",
    "Attention Required!",
    "Just a moment...",
    "Unusual activity has been detected",
)

def _looks_like_cf_challenge(text: str, status: int, headers: dict) -> bool:
    if status in (403, 503):
        return True
    if any(pat.lower() in (text or "").lower() for pat in CF_PATTERNS):
        return True
    return False

async def fetch_html(url: str, timeout_s: float = 15.0) -> dict:
    """
    Devuelve: {ok: bool, html: str|None, status: int, reason: str|None}
    - ok=False y reason='cloudflare_challenge' si detecta WAF.
    """
    try:
        async with httpx.AsyncClient(
            http2=True, timeout=timeout_s, follow_redirects=True, headers=BROWSER_HEADERS
        ) as client:
            r = await client.get(url)
            text = r.text or ""
            if _looks_like_cf_challenge(text, r.status_code, r.headers):
                return {"ok": False, "html": None, "status": r.status_code, "reason": "cloudflare_challenge"}
            ctype = (r.headers.get("content-type") or "").lower()
            if ("text/html" not in ctype) and ("xml" not in ctype):
                return {"ok": False, "html": None, "status": r.status_code, "reason": f"unsupported_content_type:{ctype}"}
            return {"ok": True, "html": text, "status": r.status_code, "reason": None}
    except httpx.RequestError as e:
        return {"ok": False, "html": None, "status": 0, "reason": f"network_error:{e.__class__.__name__}"}
