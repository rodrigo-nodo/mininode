from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks, Depends
from pydantic import BaseModel
from typing import Optional, Dict, Any
import base64

from mininode_api.core.auth import require_api_key
from mininode_api.services.image2json.pipeline import run_image2json

router = APIRouter(prefix="/capture", tags=["Capture"])

class CaptureResp(BaseModel):
    id: str
    data: Dict[str, Any]
    confidences: Dict[str, float] = {}
    notes: Optional[str] = None

@router.post("/parse", response_model=CaptureResp, dependencies=[Depends(require_api_key)])
async def parse_image(
    background: BackgroundTasks,
    file: UploadFile | None = File(default=None),
    image_b64: Optional[str] = None,
    save: bool = False,
):
    if not file and not image_b64:
        raise HTTPException(400, "Debes enviar file o image_b64")

    if file:
        image_bytes = await file.read()
    else:
        try:
            image_bytes = base64.b64decode(image_b64)
        except Exception:
            raise HTTPException(400, "image_b64 inválido")

    result = await run_image2json(image_bytes=image_bytes)
    return CaptureResp(**result.model_dump())

