import os
from fastapi import APIRouter, HTTPException, Query, Depends
from pydantic import BaseModel, Field
from typing import Optional

from mininode_api.core.auth import require_api_key

def _llm_client():
    from mininode_api.core.llm import LLMClient, ChatMessage
    return LLMClient(), ChatMessage

router = APIRouter()

class RedaccionRequest(BaseModel):
    prompt: str = Field(...)
    tone: Optional[str] = None

class RedaccionResponse(BaseModel):
    text: str

@router.get("/ping")
async def ping():
    try:
        llm, ChatMessage = _llm_client()
        sys = ChatMessage(role="system", content="Eres un ping tester.")
        usr = ChatMessage(role="user", content="Di 'pong'.")
        text = await llm.chat([sys, usr])
        return {"ok": True, "text": text[:80]}
    except Exception as e:
        return {"ok": False, "error": f"{e.__class__.__name__}: {e}"}

@router.post("/draft", response_model=RedaccionResponse, dependencies=[Depends(require_api_key)])
async def draft(req: RedaccionRequest, debug: int = Query(0, description="Set 1 to return errors")):
    try:
        llm, ChatMessage = _llm_client()
        sys = ChatMessage(role="system", content=f"Eres un redactor con tono: {req.tone or 'neutro'}")
        usr = ChatMessage(role="user", content=req.prompt)
        text = await llm.chat([sys, usr])
        return RedaccionResponse(text=text)
    except Exception as e:
        if debug == 1:
            raise HTTPException(status_code=500, detail=f"LLM error: {e.__class__.__name__}: {e}")
        return RedaccionResponse(text=f"[STUB] Redacción para: {req.prompt[:120]}...")
