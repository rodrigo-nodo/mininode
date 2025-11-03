from pydantic import BaseModel
from typing import List, Optional

class OptimizeMetrics(BaseModel):
    # Evidencia de cambio real (hash/size) — útil para QA y dashboards.
    changed: bool
    bytes_before: int
    bytes_after: int
    size_delta_pct: float
    sha256_before: str
    sha256_after: str

class OptimizeIn(BaseModel):
    file_id: str
    ops: List[str] = []  # ej: ["deskew","binarize","denoise"]

class OptimizeOut(BaseModel):
    src_file_id: str
    file_id: str
    ops_requested: List[str]
    ops_applied: List[str]
    metrics: Optional[OptimizeMetrics] = None

