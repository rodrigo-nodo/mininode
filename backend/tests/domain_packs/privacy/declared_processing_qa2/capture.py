from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import httpx
import trafilatura

ROOT = Path("backend/tests/domain_packs/privacy/declared_processing_qa2")
CASES = ROOT / "cases.json"
CAPTURES = ROOT / "captures"
MANIFEST = ROOT / "capture_manifest.json"

HEADERS = {
    "User-Agent": "Mininode-Privacy-QA/1.0 (+public passive GET; no forms; no login)"
}


def main() -> None:
    cases = json.loads(CASES.read_text(encoding="utf-8"))["cases"]
    CAPTURES.mkdir(parents=True, exist_ok=True)
    rows = []

    with httpx.Client(headers=HEADERS, follow_redirects=True, timeout=30.0) as client:
        for case in cases:
            row = {
                "case_id": case["case_id"],
                "requested_url": case["url"],
                "document_type": case["document_type"],
                "captured_at_utc": datetime.now(timezone.utc).isoformat(),
            }
            try:
                response = client.get(case["url"])
                row["http_status"] = response.status_code
                row["final_url"] = str(response.url)
                response.raise_for_status()
                text = trafilatura.extract(
                    response.text,
                    include_comments=False,
                    include_tables=True,
                    no_fallback=False,
                )
                if not text or len(text.strip()) < 200:
                    raise ValueError("extracted public text is empty or too short")
                text = text.strip() + "\n"
                payload = text.encode("utf-8")
                (CAPTURES / f'{case["case_id"]}.txt').write_bytes(payload)
                row.update({
                    "status": "captured",
                    "sha256": hashlib.sha256(payload).hexdigest(),
                    "bytes": len(payload),
                    "page_title": None,
                })
            except Exception as exc:
                row.update({
                    "status": "capture_failed",
                    "error_type": type(exc).__name__,
                    "error": str(exc)[:500],
                })
            rows.append(row)

    MANIFEST.write_text(
        json.dumps(rows, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
