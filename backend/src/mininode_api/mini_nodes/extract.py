from typing import Optional
import trafilatura

def extract_text(html: str, max_chars: int = 12000) -> str:
    if not html:
        return ""
    try:
        text: Optional[str] = trafilatura.extract(html)
        if not text:
            return ""
        if len(text) > max_chars:
            return text[:max_chars] + "…"
        return text
    except Exception:
        return ""
