from typing import Optional, Dict, Any, List
from pydantic import BaseModel
from .api_base import ErrorObj, MetaObj  # MetaObj existe en api_base.py

# === Step y payloads de pipeline ===
class StepResult(BaseModel):
    name: str
    ok: bool
    time_ms: int
    data: Optional[Dict[str, Any]] = None
    error: Optional[ErrorObj] = None

class PipelineRunOut(BaseModel):
    steps: List[StepResult]
    result: Optional[Dict[str, Any]] = None

# === Flows ===
class FlowsOut(BaseModel):
    flows: List[str]

# === RESPUESTAS NO-GENÉRICAS (evita 500 por generics) ===
class ApiResponseFlows(BaseModel):
    ok: bool
    time_ms: int
    data: Optional[FlowsOut] = None
    error: Optional[ErrorObj] = None
    meta: MetaObj

class ApiResponsePipeline(BaseModel):
    ok: bool
    time_ms: int
    data: Optional[PipelineRunOut] = None
    error: Optional[ErrorObj] = None
    meta: MetaObj
