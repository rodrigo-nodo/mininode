from fastapi import APIRouter, HTTPException, Depends, Query
from mininode_api.core.auth import require_api_key
from mininode_api.core.llm import LLMClient, ChatMessage
from mininode_api.models.write import DraftReq, DraftResp

router = APIRouter(prefix="/write", tags=["Write"])

@router.post("/draft", response_model=DraftResp, dependencies=[Depends(require_api_key)])
async def write_draft(req: DraftReq, debug: int = Query(0, description="Set 1 para ver errores")):
    if not req.prompt:
        raise HTTPException(status_code=400, detail="prompt vacío")
    try:
        llm = LLMClient()
        sys = ChatMessage(role="system", content=f"Eres un redactor con tono: {req.tone or 'neutro'}")
        usr = ChatMessage(role="user", content=req.prompt)
        text = await llm.chat([sys, usr])
        return DraftResp(text=text)
    except Exception as e:
        if debug == 1:
            raise HTTPException(status_code=500, detail=f"LLM error: {e.__class__.__name__}: {e}")
        # fallback no intrusivo
        return DraftResp(text=f"[STUB] Borrador para: {req.prompt[:120]}...")
