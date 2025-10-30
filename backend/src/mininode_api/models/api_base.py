from typing import Generic, Optional, TypeVar
from pydantic import BaseModel, Field

T = TypeVar("T")

class ErrorObj(BaseModel):
    code: str = Field(..., examples=["BAD_INPUT", "NOT_FOUND", "SERVER_ERROR"])
    message: str

class MetaObj(BaseModel):
    request_id: str
    version: str

class ApiResponse(BaseModel, Generic[T]):
    ok: bool
    time_ms: int
    data: Optional[T] = None
    error: Optional[ErrorObj] = None
    meta: MetaObj
