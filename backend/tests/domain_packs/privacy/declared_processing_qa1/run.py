from __future__ import annotations

# QA1 trigger: execution is orchestrated by the stable workflow on main.
import json
import os
import signal
from pathlib import Path
from mininode_api.domain_packs.privacy.declared_processing import PublicDocument, extract_declared_processing

ROOT=Path("backend/tests/domain_packs/privacy/declared_processing_qa1")
CALL_TIMEOUT_SECONDS=90
QA_BUDGET_USD=5.00
INPUT_USD_PER_MILLION=4.00
OUTPUT_USD_PER_MILLION=20.00

class QAInferenceTimeout(TimeoutError):
    pass

def _timeout(_signum, _frame):
    raise QAInferenceTimeout(f"inference exceeded {CALL_TIMEOUT_SECONDS}s")

signal.signal(signal.SIGALRM, _timeout)
manifest=json.loads((ROOT/"capture_manifest.json").read_text(encoding="utf-8"))
out=ROOT/"outputs"; out.mkdir(exist_ok=True)
summary=[]
estimated_cost_usd=0.0
execution_sha=os.environ.get("QA_EXECUTION_SHA")
if not execution_sha:
    raise SystemExit("QA_EXECUTION_SHA is required")
marker=ROOT/"executed_sha.txt"
if marker.exists() and execution_sha in marker.read_text(encoding="utf-8").splitlines():
    raise SystemExit(f"QA already executed for {execution_sha}; refusing duplicate API spend")

INFRASTRUCTURE_ERRORS={"RateLimitError","APITimeoutError","APIConnectionError","InternalServerError"}
for row in manifest:
    cid=row["case_id"]
    if row["status"]!="captured":
        summary.append({"case_id":cid,"status":"capture_failed"}); continue
    text=(ROOT/"captures"/f"{cid}.txt").read_text(encoding="utf-8")
    doc=PublicDocument(url=row["final_url"],text=text,document_type=row["document_type"],page_title=row.get("page_title"))
    for run in (1,2):
        input_tokens_estimate=max(1, len(text.encode("utf-8")) // 3)
        next_call_ceiling=(input_tokens_estimate/1_000_000)*INPUT_USD_PER_MILLION + (4096/1_000_000)*OUTPUT_USD_PER_MILLION
        if estimated_cost_usd + next_call_ceiling > QA_BUDGET_USD:
            summary.append({"case_id":cid,"run":run,"status":"budget_stopped","estimated_cost_usd":round(estimated_cost_usd,6),"budget_usd":QA_BUDGET_USD})
            (ROOT/"run_summary.json").write_text(json.dumps({"budget_usd":QA_BUDGET_USD,"estimated_cost_usd":round(estimated_cost_usd,6),"calls":summary},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
            marker.write_text(execution_sha+"\n",encoding="utf-8")
            raise SystemExit(f"QA budget exhausted before next call: ${estimated_cost_usd:.4f} / ${QA_BUDGET_USD:.2f}")
        target=out/f"{cid}-run{run}.json"
        try:
            signal.alarm(CALL_TIMEOUT_SECONDS)
            result=extract_declared_processing(doc)
            # Successful extraction currently returns validated facts only. Until token usage is
            # surfaced by the extractor, reserve the worst-case output allowance before each call.
            estimated_cost_usd += next_call_ceiling
            target.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
            summary.append({"case_id":cid,"run":run,"status":"valid","records":len(result["records"])})
            print(cid,run,"VALID",len(result["records"]))
        except Exception as e:
            error_type=type(e).__name__
            target.write_text(json.dumps({"error_type":type(e).__name__,"error":str(e)},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
            summary.append({"case_id":cid,"run":run,"status":"invalid","error_type":error_type})
            print(cid,run,"INVALID",error_type,str(e)[:200],flush=True)
            if error_type in INFRASTRUCTURE_ERRORS:
                (ROOT/"run_summary.json").write_text(json.dumps({"budget_usd":QA_BUDGET_USD,"estimated_cost_usd":round(estimated_cost_usd,6),"calls":summary},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
                marker.write_text(execution_sha+"\n",encoding="utf-8")
                raise SystemExit(f"fail-fast after infrastructure error: {error_type}")
        finally:
            signal.alarm(0)
(ROOT/"run_summary.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
marker.write_text(execution_sha+"\n",encoding="utf-8")

# QA1 execution trigger: stable runner from main.
