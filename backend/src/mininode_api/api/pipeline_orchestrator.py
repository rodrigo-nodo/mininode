from fastapi import APIRouter, UploadFile, File, Header, HTTPException
from typing import Dict, Any
from ..core import config
from ..core.measure import now_ms, elapsed_ms
from ..core.ids import new_id
from ..models.api_base import ErrorObj, MetaObj
from ..models.pipeline import (
    PipelineRunOut, StepResult, FlowsOut,
    ApiResponseFlows, ApiResponsePipeline
)
from ..services.pipeline.runner import execute_flow
from ..services.pipeline.flows import FLOWS

router = APIRouter(prefix="/pipeline", tags=["pipeline"])

def _enforce_api_key(x_api_key: str | None):
    if not config.MININODE_API_KEY:
        return
    if not x_api_key or x_api_key != config.MININODE_API_KEY:
        raise HTTPException(status_code=401, detail="invalid api key")

@router.get("/flows", response_model=ApiResponseFlows)
async def list_flows(x_api_key: str | None = Header(default=None, convert_underscores=False)):
    _enforce_api_key(x_api_key)
    try:
        data = FlowsOut(flows=list(FLOWS.keys()))
        return ApiResponseFlows(
            ok=True, time_ms=0, data=data, error=None,
            meta=MetaObj(request_id=new_id("req"), version=config.API_VERSION),
        )
    except Exception as e:
        return ApiResponseFlows(
            ok=False, time_ms=0, data=None,
            error=ErrorObj(code="FLOW_ENUM_ERROR", message=str(e)),
            meta=MetaObj(request_id=new_id("req"), version=config.API_VERSION),
        )

@router.post("/flow/{flow_name}", response_model=ApiResponsePipeline)
async def run_flow(
    flow_name: str,
    file: UploadFile | None = File(default=None),
    x_api_key: str | None = Header(default=None, convert_underscores=False),
):
    _enforce_api_key(x_api_key)
    t0_total = now_ms()

    ctx: Dict[str, Any] = {}
    if file is not None:
        ctx["file"] = file

    try:
        steps_raw, last_data = execute_flow(flow_name, ctx=ctx)
    except Exception as e:
        return ApiResponsePipeline(
            ok=False,
            time_ms=elapsed_ms(t0_total),
            data=None,
            error=ErrorObj(code="FLOW_ERROR", message=str(e)),
            meta=MetaObj(request_id=new_id("req"), version=config.API_VERSION),
        )

    steps_out = [
        StepResult(
            name=s["name"],
            ok=bool(s.get("ok")),
            time_ms=int(s.get("time_ms", 0)),
            data=s.get("data"),
            error=ErrorObj(**s["error"]) if s.get("error") else None,
        )
        for s in steps_raw
    ]

    ok_global = all(s.ok for s in steps_out)
    return ApiResponsePipeline(
        ok=ok_global,
        time_ms=elapsed_ms(t0_total),
        data=PipelineRunOut(steps=steps_out, result=last_data if ok_global else None),
        error=None if ok_global else ErrorObj(code="STEP_FAILED", message="Uno o más pasos fallaron"),
        meta=MetaObj(request_id=new_id("req"), version=config.API_VERSION),
    )
