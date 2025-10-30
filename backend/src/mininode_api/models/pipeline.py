from typing import Optional, Dict, Any, List
from pydantic import BaseModel
from .api_base import ErrorObj

class StepResult(BaseModel):
    name: str
    ok: bool
    time_ms: int
    data: Optional[Dict[str, Any]] = None
    error: Optional[ErrorObj] = None

class PipelineRunOut(BaseModel):
    steps: List[StepResult]
    result: Optional[Dict[str, Any]] = None
