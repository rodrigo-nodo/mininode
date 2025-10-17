from fastapi import APIRouter, File, UploadFile, Depends, HTTPException
from mininode_api.core.auth import require_api_key
from mininode_api.services.capture.pipeline import procesar_documento
from mininode_api.services.capture.schemas import CaptureRequest, CaptureResponse

router = APIRouter(prefix="", tags=["Capture"])

@router.post("/capture", response_model=CaptureResponse, dependencies=[Depends(require_api_key)])
async def capture_endpoint(
    doc_type: str,
    usar_fallback: bool = True,
    file: UploadFile = File(...),
):
    data = await file.read()
    req = CaptureRequest(doc_type=doc_type, usar_fallback=usar_fallback)
    return procesar_documento(data, req)
