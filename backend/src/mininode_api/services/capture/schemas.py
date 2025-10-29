# SPDX-License-Identifier: MIT
from __future__ import annotations
from typing import Dict, Optional, List, Literal
from pydantic import BaseModel, Field

DocType = Literal["guia", "boleta", "factura"]

class CaptureRequest(BaseModel):
    doc_type: DocType = Field(..., description="Tipo de documento a extraer")
    return_fields: Optional[List[str]] = Field(None, description="Campos a devolver (si None, todos)")
    usar_fallback: bool = Field(True, description="Usar fallback con modelo 4o si faltan campos críticos")
    mode: Literal["normal", "fast"] = Field("normal", description="Modo: normal o fast (solo cabecera)")
class FieldOut(BaseModel):
    value: Optional[str]
    confidence: float
    source: str
    uncertain: bool

class ConsistencyReport(BaseModel):
    checks: Dict[str, bool] = {}
    notes: List[str] = []

class CostBreakdown(BaseModel):
    tokens: Dict[str, int] = {}
    usd: Dict[str, float] = {}
    total_usd: float = 0.0

class TimingMs(BaseModel):
    # Nuevos (mÃ¡s claros)
    server_total: int = 0
    decode_ms: int = 0
    preproc_ms: int = 0
    ocr: int = 0
    llm_mini: int = 0
    llm_fallback: int = 0
    validate_ms: int = 0
    roi_table: int = 0
    # Compat: mantener 'total' por atrÃ¡s; igual a server_total
    total: int = 0

class CaptureResponse(BaseModel):
    doc_type: DocType
    fields: Dict[str, FieldOut]
    consistency: ConsistencyReport
    consistency_after_fallback: Optional[ConsistencyReport] = None
    cost: CostBreakdown
    timings: TimingMs
    fallback_applied: bool = False
    adjusted_fields: List[str] = []
    items: List[Dict[str, Optional[str]]] = []



