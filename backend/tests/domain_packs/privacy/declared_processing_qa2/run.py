from __future__ import annotations

"""QA2 runner definition.

This file is intentionally inert in the freeze PR. Inference must not be wired to CI
until captures and the independent reference are committed and reviewed.
"""

import json
import os
import signal
from pathlib import Path

from mininode_api.domain_packs.privacy.declared_processing import (
    MAX_OUTPUT_TOKENS,
    PublicDocument,
    extract_declared_processing,
)

ROOT = Path("backend/tests/domain_packs/privacy/declared_processing_qa2")
CALL_TIMEOUT_SECONDS = 120
QA_BUDGET_USD = 10.00
INPUT_USD_PER_MILLION = 4.00
OUTPUT_USD_PER_MILLION = 20.00

if MAX_OUTPUT_TOKENS != 8192:
    raise RuntimeError("QA2 cost guard must track the frozen extractor output limit")


class QAInferenceTimeout(TimeoutError):
    pass


def _timeout(_signum, _frame):
    raise QAInferenceTimeout(f"inference exceeded {CALL_TIMEOUT_SECONDS}s")


def run() -> None:
    reference = ROOT / "reference.json"
    manifest_path = ROOT / "capture_manifest.json"
    if not reference.exists() or not manifest_path.exists():
        raise SystemExit("QA2 is not ready: freeze captures and independent reference first")

    signal.signal(signal.SIGALRM, _timeout)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    out = ROOT / "outputs"
    out.mkdir(exist_ok=True)
    calls = []
    reserved_cost_usd = 0.0
    actual_cost_usd = 0.0
    execution_sha = os.environ.get("QA_EXECUTION_SHA")
    if not execution_sha:
        raise SystemExit("QA_EXECUTION_SHA is required")

    marker = ROOT / "executed_sha.txt"
    if marker.exists():
        raise SystemExit("QA2 already executed; refusing duplicate independent-QA spend")

    infra_errors = {"RateLimitError", "APITimeoutError", "APIConnectionError", "InternalServerError"}

    for row in manifest:
        cid = row["case_id"]
        if row["status"] != "captured":
            calls.append({"case_id": cid, "status": "capture_failed"})
            continue

        text = (ROOT / "captures" / f"{cid}.txt").read_text(encoding="utf-8")
        doc = PublicDocument(
            url=row["final_url"],
            text=text,
            document_type=row["document_type"],
            page_title=row.get("page_title"),
        )

        for run_number in (1, 2):
            input_tokens_estimate = max(1, len(text.encode("utf-8")) // 3)
            call_ceiling = (
                input_tokens_estimate / 1_000_000 * INPUT_USD_PER_MILLION
                + MAX_OUTPUT_TOKENS / 1_000_000 * OUTPUT_USD_PER_MILLION
            )
            if reserved_cost_usd + call_ceiling > QA_BUDGET_USD:
                raise SystemExit("QA2 budget guard stopped before next API call")

            usage = {}
            try:
                signal.alarm(CALL_TIMEOUT_SECONDS)
                result = extract_declared_processing(doc, usage_sink=usage.update)
                reserved_cost_usd += call_ceiling
                call_cost = (
                    usage.get("input_tokens", 0) / 1_000_000 * INPUT_USD_PER_MILLION
                    + usage.get("output_tokens", 0) / 1_000_000 * OUTPUT_USD_PER_MILLION
                )
                actual_cost_usd += call_cost
                (out / f"{cid}-run{run_number}.json").write_text(
                    json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
                )
                calls.append({
                    "case_id": cid,
                    "run": run_number,
                    "status": "valid",
                    "records": len(result["records"]),
                    "usage": usage,
                    "actual_cost_usd": round(call_cost, 6),
                })
            except Exception as exc:
                error_type = type(exc).__name__
                calls.append({"case_id": cid, "run": run_number, "status": "invalid", "error_type": error_type})
                if error_type in infra_errors:
                    raise
            finally:
                signal.alarm(0)

    (ROOT / "run_summary.json").write_text(
        json.dumps({
            "budget_usd": QA_BUDGET_USD,
            "reserved_cost_usd": round(reserved_cost_usd, 6),
            "actual_cost_usd": round(actual_cost_usd, 6),
            "calls": calls,
        }, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    marker.write_text(execution_sha + "\n", encoding="utf-8")


if __name__ == "__main__":
    run()
