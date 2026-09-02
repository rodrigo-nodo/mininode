from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, model_validator

from mininode_api.privacy_data.catalog import get_catalog


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


class RecoveryLinkResponse(BaseModel):
    recovery_token: str
    expires_at: datetime


class MapObservationResponse(BaseModel):
    code: Literal["D01", "D02", "D03", "D04", "D05", "D06"]
    type: Literal["review", "notice"]
    title: str
    description: str
    activity_id: UUID
    activity_type: str
    third_party_type: str | None = None


class DataMapUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    industry_profile: str | None = None
    business_size: str | None = None

    @model_validator(mode="after")
    def validate_catalog_codes(self):
        catalog = get_catalog()
        for field in ("industry_profile", "business_size"):
            value = getattr(self, field)
            section = "industry_profiles" if field == "industry_profile" else "business_size"
            valid = {item["code"] for item in catalog[section]}
            if value is not None and value not in valid:
                raise ValueError(f"invalid {field}")
        return self
