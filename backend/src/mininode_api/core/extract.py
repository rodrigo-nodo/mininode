# -*- coding: utf-8 -*-
# mininode_api/core/mini_nodes/extract.py
from __future__ import annotations
import re
from html import unescape

_TITLE_RE = re.compile(r"<title[^>]*>(.*?)</title>", re.I | re.S)
_META_DESC_RE = re.compile(r'<meta[^>]+name=["\']description["\'][^>]+content=["\'](.*?)["\']', re.I | re.S)

def extract_title(html: str) -> str:
    m = _TITLE_RE.search(html or "")
    return unescape(m.group(1)).strip() if m else ""

def extract_description(html: str) -> str:
    m = _META_DESC_RE.search(html or "")
    return unescape(m.group(1)).strip() if m else ""

def extract_text_fast(html: str, max_chars: int = 6000) -> str:
    h = re.sub(r"(?is)<(script|style|noscript)[^>]*>.*?</\1>", " ", html or "")
    h = re.sub(r"(?is)<!--.*?-->", " ", h)
    txt = re.sub(r"(?is)<[^>]+>", " ", h)
    txt = unescape(txt)
    txt = re.sub(r"\s+", " ", txt).strip()
    if len(txt) > max_chars:
        txt = txt[:max_chars] + " …"
    return txt

def extract_payload(html: str) -> dict:
    return {
        "title": extract_title(html),
        "description": extract_description(html),
        "text": extract_text_fast(html),
    }
