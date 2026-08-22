"""Anonymous feedback endpoints for Mininode Learn."""

from __future__ import annotations

from enum import Enum
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field, model_validator

from mininode_api.core.auth import require_api_key
from mininode_api.services import learn_feedback

router = APIRouter(prefix="/learn", tags=["Learn"])

EBOOK_ID = "001-privacidad-para-pequenos-negocios"


class Topic(str, Enum):
    business_data = "Datos que maneja el negocio"
    website_forms = "Sitio web y formularios"
    files = "Excel, WhatsApp y archivos"
    policies = "Políticas y documentos"
    security = "Seguridad"
    new_law = "Nueva ley"


class FeedbackCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ebook_id: str
    rating: int = Field(ge=1, le=5)


class FeedbackUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    topic: Topic | None = None
    comment: str | None = Field(default=None, max_length=500)

    @model_validator(mode="after")
    def require_an_update(self):
        if self.topic is None and self.comment is None:
            raise ValueError("topic or comment is required")
        return self


class FeedbackCreated(BaseModel):
    id: UUID


@router.post("/feedback", response_model=FeedbackCreated, status_code=201, dependencies=[Depends(require_api_key)])
def submit_feedback(body: FeedbackCreate):
    if body.ebook_id != EBOOK_ID:
        raise HTTPException(status_code=422, detail="Unknown ebook_id")
    return {"id": learn_feedback.create_feedback(ebook_id=body.ebook_id, rating=body.rating)}


@router.patch("/feedback/{feedback_id}", status_code=204, dependencies=[Depends(require_api_key)])
def amend_feedback(feedback_id: UUID, body: FeedbackUpdate):
    try:
        updated = learn_feedback.update_feedback(
            feedback_id,
            topic=body.topic.value if body.topic else None,
            comment=body.comment,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if not updated:
        raise HTTPException(status_code=404, detail="Feedback not found")
