from pydantic import BaseModel, AnyHttpUrl, Field
from typing import List, Optional

class AnalyzeReq(BaseModel):
    urls: List[AnyHttpUrl] = Field(default_factory=list)
    scope: str = "page"  # "page" | "site"
    lang: str = "es"
    prompt: Optional[str] = None
    max_pages: int = Field(default=5, ge=1, le=50)
    same_domain: bool = True
    follow_subdomains: bool = False
    max_chars: int = Field(default=12000, ge=1000, le=50000)

class SummaryItem(BaseModel):
    url: str
    text: str

class AnalyzeResp(BaseModel):
    summaries: List[SummaryItem]
    compare: Optional[str] = None
