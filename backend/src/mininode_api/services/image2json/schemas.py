from pydantic import BaseModel
from typing import Dict, Any, Optional

class Image2JsonResult(BaseModel):
    id: str
    json: Dict[str, Any]
    confidences: Dict[str, float] = {}
    notes: Optional[str] = None
