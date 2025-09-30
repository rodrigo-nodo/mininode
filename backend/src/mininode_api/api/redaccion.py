from fastapi import APIRouter
from pydantic import BaseModel, Field
from typing import Optional

def _llm_client():
    from mininode_api.core.llm import LLMClient, ChatMessage
    return LLMClient(), ChatMessage

router = APIRouter()

class RedaccionRequest(BaseModel):
    prompt: str = Field(...)
    tone: Optional[str] = None

class RedaccionResponse(BaseModel):
    text: str

@router.post("/draft", response_model=RedaccionResponse)
async def draft(req: RedaccionRequest):
    try:
        llm, ChatMessage = _llm_client()
        sys = ChatMessage(role="system", content=f"Eres un redactor con tono: {req.tone or 'neutro'}")
        usr = ChatMessage(role="user", content=req.prompt)
        text = await llm.chat([sys, usr])
        return RedaccionResponse(text=text)
    except Exception:
        return RedaccionResponse(text=f"[STUB] Redacción para: {req.prompt[:120]}...")
