# reemplazo simple del contenido actual (manteniendo el path)
from fastapi import APIRouter, Depends
from mininode_api.core.auth import require_api_key
from mininode_api.models.write import DraftReq, DraftResp
from mininode_api.api.write import write_draft

router = APIRouter(prefix="/redaccion", tags=["Legacy"])

@router.post("/draft", response_model=DraftResp, dependencies=[Depends(require_api_key)])
async def redaccion_draft_legacy(req: DraftReq):
    return await write_draft(req)
