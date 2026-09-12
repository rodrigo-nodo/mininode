#!/usr/bin/env python3
"""Passive public freshness precheck for a proposed PRV-103 holdout.

This utility only issues GET requests, follows ordinary redirects, and records
transport metadata. It never parses response bodies or runs product code.
"""
from __future__ import annotations

import argparse
import json
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit

USER_AGENT = "Mininode-PRV103-holdout-precheck/1.0"


def normalize_hostname(value: str) -> str:
    value = value.strip()
    parsed = urlsplit(value if "://" in value else f"https://{value}")
    hostname = (parsed.hostname or "").lower().rstrip(".")
    return hostname[4:] if hostname.startswith("www.") else hostname


def load_domains(path: Path) -> list[str]:
    domains = [normalize_hostname(line) for line in path.read_text().splitlines() if line.strip()]
    if len(domains) != 100:
        raise ValueError(f"expected exactly 100 domains, got {len(domains)}")
    if "" in domains or len(set(domains)) != len(domains):
        raise ValueError("domains must be non-empty and unique after normalization")
    return domains


def precheck(domain: str, timeout: float) -> dict[str, object]:
    request = urllib.request.Request(f"https://{domain}/", headers={"User-Agent": USER_AGENT}, method="GET")
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            response.read(1)  # Establish that a public response body is readable; do not inspect it.
            return {
                "domain": domain,
                "result": "PASS" if 200 <= response.status < 400 else "FAIL",
                "http_status": response.status,
                "final_url": response.url,
                "error": None,
            }
    except urllib.error.HTTPError as error:
        return {"domain": domain, "result": "FAIL", "http_status": error.code, "final_url": error.url, "error": str(error)}
    except (urllib.error.URLError, TimeoutError, OSError) as error:
        return {"domain": domain, "result": "FAIL", "http_status": None, "final_url": None, "error": str(error)}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("domains", type=Path, help="text file containing exactly 100 domains")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--timeout", type=float, default=20)
    args = parser.parse_args()

    domains = load_domains(args.domains)
    results = [precheck(domain, args.timeout) for domain in domains]
    document = {
        "checked_at_utc": datetime.now(timezone.utc).isoformat(),
        "method": "public passive GET; redirects followed; one response byte read; no form inspection",
        "result": "PASS" if all(row["result"] == "PASS" for row in results) else "FAIL",
        "sites": results,
    }
    args.output.write_text(json.dumps(document, ensure_ascii=False, indent=2) + "\n")
    return 0 if document["result"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
