from pydantic import BaseModel

class UploadOut(BaseModel):
    file_id: str
    filename: str
    mime: str | None = None
    size: int
