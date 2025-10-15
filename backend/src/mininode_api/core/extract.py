# -*- coding: utf-8 -*-
# mininode/backend/src/mininode_api/core/extract.py
# Decisión: extractor naïf y rápido (sin dependencias pesadas). 
# Si quieres mayor calidad, cambia a selectolax/readability.

import re
from html import unescape

_TITLE_RE = re.compile(r"<title[^>]*>(.*?)</title>", re.I | re.S)
_META_DESC_RE = re.compile(r'<meta[^>]+name=["\']description["\'][^>]+content=["\'](.*?)["\']', re.I | re.S)

def extract_title(html: str) -> str:
    m = _TITLE_RE.search(html)
    return unescape(m.group(1)).strip() if m else ""

def extract_description(html: str) -> str:
    m = _META_DESC_RE.search(html)
    return unescape(m.group(1)).strip() if m else ""

def extract_text_fast(html: str, max_chars: int = 6000) -> str:
    # Quitar scripts/estilos y tags básicos, luego colapsar espacios
    html = re.sub(r"(?is)<(script|style|noscript)[^>]*>.*?</\1>", " ", html)
    html = re.sub(r"(?is)<!--.*?-->", " ", html)
    text = re.sub(r"(?is)<[^>]+>", " ", html)
    text = unescape(text)
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) > max_chars:
        text = text[:max_chars] + " …"
    return text

def extract_payload(html: str) -> dict:
    title = extract_title(html)
    desc = extract_description(html)
    text = extract_text_fast(html)
    return {"title": title, "description": desc, "text": text}
