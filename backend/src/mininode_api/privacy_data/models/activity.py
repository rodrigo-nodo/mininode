from datetime import datetime
from typing import Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, model_validator

from mininode_api.privacy_data.catalog import get_catalog


def _codes(section: str) -> set[str]:
    return {item["code"] for item in get_catalog()[section]}


class ThirdParty(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID = Field(default_factory=uuid4)
    type: str
    relationships: list[str] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_catalog_codes(self):
        if self.type not in _codes("third_party_types"):
            raise ValueError("invalid third-party type")
        invalid = set(self.relationships) - _codes("third_party_relationships")
        if invalid:
            raise ValueError(f"invalid third-party relationships: {sorted(invalid)}")
        if "unknown" in self.relationships and len(self.relationships) > 1:
            raise ValueError("unknown must be the only third-party relationship")
        return self


class Retention(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal["defined", "variable", "unknown"] = "unknown"
    value: float | None = None
    unit: Literal["days", "months", "years"] | None = None
    note: str | None = None

    @model_validator(mode="after")
    def validate_defined(self):
        if self.status == "defined" and (
            self.value is None or self.value <= 0 or self.unit is None
        ):
            raise ValueError("defined retention requires a positive value and unit")
        return self


class ActivityAnswers(BaseModel):
    model_config = ConfigDict(extra="forbid")

    people_categories: list[str] = Field(default_factory=list)
    may_include_minors: bool | Literal["unknown"] | None = None
    personal_data_types: list[str] = Field(default_factory=list)
    storage_locations: list[str] = Field(default_factory=list)
    data_origins: list[str] = Field(default_factory=list)
    data_channels: list[str] = Field(default_factory=list)
    purposes: list[str] = Field(default_factory=list)
    access_roles: list[str] = Field(default_factory=list)
    has_third_parties: bool | Literal["unknown"] | None = None
    third_parties: list[ThirdParty] = Field(default_factory=list)
    retention: Retention = Field(default_factory=Retention)

    @model_validator(mode="after")
    def validate_answers(self):
        sections = (
            "people_categories", "personal_data_types", "storage_locations", "data_origins",
            "data_channels", "purposes", "access_roles",
        )
        for section in sections:
            invalid = set(getattr(self, section)) - _codes(section)
            if invalid:
                raise ValueError(f"invalid {section} codes: {sorted(invalid)}")
        for exclusive in ("owner_only", "unknown"):
            if exclusive in self.access_roles and len(self.access_roles) > 1:
                raise ValueError(f"{exclusive} must be the only access role")
        if self.has_third_parties is not True and self.third_parties:
            raise ValueError("third_parties require has_third_parties=true")
        return self


class ActivityCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    activity_type: str
    data_context: Literal["unconfirmed", "own_operations", "client_service", "both"]
    position: int | None = Field(default=None, ge=0)
    answers: ActivityAnswers = Field(default_factory=ActivityAnswers)

    @model_validator(mode="after")
    def validate_activity_type(self):
        if self.activity_type not in _codes("activity_types"):
            raise ValueError("invalid activity_type")
        return self


class ActivityUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    activity_type: str | None = None
    data_context: Literal["unconfirmed", "own_operations", "client_service", "both"] | None = None
    position: int | None = Field(default=None, ge=0)
    answers: ActivityAnswers | None = None

    @model_validator(mode="after")
    def validate_activity_type(self):
        for field in self.model_fields_set:
            if getattr(self, field) is None:
                raise ValueError(f"{field} cannot be null")
        if self.activity_type is not None and self.activity_type not in _codes("activity_types"):
            raise ValueError("invalid activity_type")
        return self


class ActivityResponse(BaseModel):
    id: UUID
    activity_type: str
    data_context: str
    position: int
    answers: ActivityAnswers
    created_at: datetime
    updated_at: datetime
