# -*- coding: utf-8 -*-
# backend/src/mininode_api/models/analyze.py
from __future__ import annotations
from typing import List, Literal
from pydantic import BaseModel, HttpUrl

# Modelos "nuevos"
class SummaryIn(BaseModel):
    urls: List[HttpUrl]
    scope: Literal["page", "site"] = "page"
    lang: str = "es"
    prompt: str

class SiteSummary(BaseModel):
    url: HttpUrl
    text: str

class SummaryOut(BaseModel):
    summaries: List[SiteSummary]
    compare: str

# Alias "viejos" para compatibilidad
class AnalyzeReq(SummaryIn):
    pass

class AnalyzeResp(SummaryOut):
    pass

__all__ = [
    "SummaryIn", "SiteSummary", "SummaryOut",
    "AnalyzeReq", "AnalyzeResp",
]

