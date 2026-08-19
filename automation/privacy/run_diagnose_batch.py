#!/usr/bin/env python3
import argparse
import csv
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path


DIAGNOSTIC_FIELDS = [
    "requested_url",
    "final_url",
    "requested_hostname",
    "effective_hostname",
    "internal_error_code",
    "failure_phase",
    "dns_attempt_count",
    "dns_failure_category",
    "network_family",
    "resolved_addresses",
    "rejected_addresses",
    "transport_error_class",
    "tls_valid",
    "redirect_count",
    "status_code",
    "elapsed_ms",
]


def parse_urls(raw: str) -> list[str]:
    seen = set()
    urls = []
    for line in raw.splitlines():
        url = line.strip()
        if not url or url.startswith("#") or url in seen:
            continue
        seen.add(url)
        urls.append(url)
    return urls


def diagnose(url: str, endpoint: str, api_key: str, timeout: float = 60.0) -> dict:
    payload = json.dumps({"url": url}).encode("utf-8")
    request = urllib.request.Request(
        endpoint,
        data=payload,
        method="POST",
        headers={
            "Content-Type": "application/json",
            "X-Api-Key": api_key,
            "X-Mininode-Diagnostics": "1",
            "User-Agent": "mininode-privacy-diagnose-bridge/1.0",
        },
    )
    status = None
    body_text = ""
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            status = response.status
            body_text = response.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        status = exc.code
        body_text = exc.read().decode("utf-8", errors="replace")
    except Exception as exc:
        return {
            "url": url,
            "http_status": None,
            "success": False,
            "error_code": "transport_error",
            "detail": exc.__class__.__name__,
            "diagnostic": {"transport_error_class": exc.__class__.__name__},
            "response": None,
        }

    try:
        body = json.loads(body_text) if body_text else None
    except json.JSONDecodeError:
        body = {"raw": body_text[:2000]}

    success = bool(status is not None and 200 <= status < 300)
    error_code = None
    detail = None
    diagnostic = None
    if isinstance(body, dict):
        diagnostic = body.get("diagnostic") if isinstance(body.get("diagnostic"), dict) else None
        if not success:
            error_code = body.get("code") or body.get("error_code") or body.get("error")
            raw_detail = body.get("detail")
            if isinstance(raw_detail, dict):
                error_code = error_code or raw_detail.get("code") or raw_detail.get("error_code")
                detail = raw_detail.get("detail") or raw_detail.get("message")
            elif raw_detail is not None:
                detail = str(raw_detail)
            detail = detail or body.get("message")

    return {
        "url": url,
        "http_status": status,
        "success": success,
        "error_code": error_code,
        "detail": detail,
        "diagnostic": diagnostic,
        "response": body,
    }


def write_outputs(results: list[dict], output_dir: Path, label: str) -> tuple[Path, Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    safe_label = "".join(ch if ch.isalnum() or ch in "-_" else "-" for ch in label).strip("-") or "batch"
    json_path = output_dir / f"privacy-diagnose-{safe_label}.json"
    csv_path = output_dir / f"privacy-diagnose-{safe_label}.csv"
    diagnostic_path = output_dir / f"privacy-diagnose-{safe_label}-diagnostics.jsonl"
    json_path.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["url", "http_status", "success", "error_code", "detail"])
        writer.writeheader()
        for item in results:
            writer.writerow({key: item.get(key) for key in writer.fieldnames})
    with diagnostic_path.open("w", encoding="utf-8") as handle:
        for item in results:
            diagnostic = item.get("diagnostic") or {}
            row = {
                "url": item.get("url"),
                "http_status": item.get("http_status"),
                "success": item.get("success"),
                "error_code": item.get("error_code"),
                "detail": item.get("detail"),
            }
            for key in DIAGNOSTIC_FIELDS:
                if key in diagnostic:
                    row[key] = diagnostic.get(key)
            handle.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n")
    return json_path, csv_path, diagnostic_path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--urls", default=os.getenv("PRIVACY_URLS", ""))
    parser.add_argument("--endpoint", default=os.getenv("PRIVACY_ENDPOINT", "https://mininode.io/api/privacy/diagnose"))
    parser.add_argument("--api-key", default=os.getenv("MININODE_API_KEY", ""))
    parser.add_argument("--label", default=os.getenv("PRIVACY_BATCH_LABEL", "batch"))
    parser.add_argument("--output-dir", default=os.getenv("PRIVACY_OUTPUT_DIR", "automation/privacy/results"))
    parser.add_argument("--timeout", type=float, default=60.0)
    args = parser.parse_args()

    urls = parse_urls(args.urls)
    if not urls:
        print("No URLs supplied", file=sys.stderr)
        return 2
    if not args.api_key:
        print("MININODE_API_KEY is not available", file=sys.stderr)
        return 2

    results = []
    for index, url in enumerate(urls, start=1):
        print(f"[{index}/{len(urls)}] Diagnosing {url}")
        result = diagnose(url, args.endpoint, args.api_key, args.timeout)
        results.append(result)
        print(f"  -> status={result['http_status']} success={result['success']} error={result['error_code']}")

    json_path, csv_path, diagnostic_path = write_outputs(results, Path(args.output_dir), args.label)
    print(f"JSON: {json_path}")
    print(f"CSV: {csv_path}")
    print(f"Diagnostics: {diagnostic_path}")
    failures = sum(not item["success"] for item in results)
    print(f"Completed {len(results)} diagnostics; failures={failures}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
