"""Anonymous feedback endpoints for Mininode Learn."""

from __future__ import annotations

from enum import Enum
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field, model_validator

from mininode_api.core.auth import require_api_key
from mininode_api.services import learn_feedback

router = APIRouter(prefix="/learn", tags=["Learn"])


class Topic(str, Enum):
    business_data = "business_data"
    website_forms = "website_forms"
    files = "files"
    policies = "policies"
    security = "security"
    new_law = "new_law"


class FeedbackCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    content_key: str
    rating: int = Field(ge=1, le=5)


class FeedbackUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    rating: int | None = Field(default=None, ge=1, le=5)
    topic: Topic | None = None
    comment: str | None = Field(default=None, max_length=500)

    @model_validator(mode="after")
    def require_an_update(self):
        if not self.model_fields_set:
            raise ValueError("At least one field is required")
        if "rating" in self.model_fields_set and self.rating is None:
            raise ValueError("rating cannot be null")
        return self


class FeedbackCreated(BaseModel):
    feedback_id: UUID


def require_feedback_database(request: Request) -> None:
    if not getattr(request.app.state, "learn_feedback_ready", False):
        raise HTTPException(status_code=503, detail="Learn feedback is unavailable")


_DEPENDENCIES = [Depends(require_api_key), Depends(require_feedback_database)]


@router.post("/feedback", response_model=FeedbackCreated, status_code=201, dependencies=_DEPENDENCIES)
def submit_feedback(body: FeedbackCreate):
    try:
        feedback_id = learn_feedback.create_feedback(
            content_key=body.content_key, rating=body.rating
        )
    except learn_feedback.FeedbackNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"feedback_id": feedback_id}


@router.patch("/feedback/{feedback_id}", status_code=204, dependencies=_DEPENDENCIES)
def amend_feedback(feedback_id: UUID, body: FeedbackUpdate):
    changes = body.model_dump(exclude_unset=True)
    if isinstance(changes.get("topic"), Topic):
        changes["topic"] = changes["topic"].value
    try:
        learn_feedback.update_feedback(feedback_id, **changes)
    except learn_feedback.FeedbackNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except learn_feedback.InvalidFeedbackError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
