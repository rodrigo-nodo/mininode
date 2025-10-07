from pydantic import BaseModel

class DraftReq(BaseModel):
    prompt: str
    tone: str | None = "simple"

class DraftResp(BaseModel):
    text: str
