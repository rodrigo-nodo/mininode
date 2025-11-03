from pydantic import BaseModel
from typing import List

class OptimizeIn(BaseModel):
    file_id: str
    ops: List[str] = []  # ej: ["deskew","binarize","denoise"]

class OptimizeOut(BaseModel):
    src_file_id: str
    file_id: str
    ops_requested: List[str]
    ops_applied: List[str]
