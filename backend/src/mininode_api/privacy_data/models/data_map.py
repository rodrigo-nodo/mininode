from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel


class DataMapResponse(BaseModel):
    id: UUID
    status: Literal["draft", "completed"]
    industry_profile: str | None
    business_size: str | None
    catalog_version: str
    created_at: datetime
    updated_at: datetime
    expires_at: datetime


class CreatedDataMapResponse(BaseModel):
    token: str
    map: DataMapResponse
