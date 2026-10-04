"""Pydantic request and response models for the cumulative HW4/HW5 app."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


CATEGORIES = {
    "Produce",
    "Meat and Seafood",
    "Dairy and Refrigerated",
    "Packaged Foods",
}


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=200)


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    email: EmailStr


class ManufacturerCreate(BaseModel):
    name: str = Field(min_length=2, max_length=160)
    contact_name: str = Field(min_length=2, max_length=160)
    contact_email: EmailStr

    @field_validator("name", "contact_name", mode="before")
    @classmethod
    def strip_manufacturer_text(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value


class ManufacturerUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=160)
    contact_name: str | None = Field(default=None, min_length=2, max_length=160)
    contact_email: EmailStr | None = None

    @field_validator("name", "contact_name", mode="before")
    @classmethod
    def strip_manufacturer_text(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value


class ManufacturerResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    contact_name: str
    contact_email: EmailStr
    created_at: datetime
    updated_at: datetime


class RecallInput(BaseModel):
    product_name: str = Field(min_length=2, max_length=160)
    recall_code: str = Field(pattern=r"^REC-[A-Z0-9][A-Z0-9-]{2,23}$")
    units_affected: int = Field(default=0, ge=0, le=100_000_000)
    manufacturer_id: int = Field(gt=0)
    brand_name: str = Field(min_length=2, max_length=160)
    submitter_email: EmailStr
    category: str
    recall_details: str = Field(min_length=26, max_length=2000)
    terms_accepted: bool

    @field_validator("product_name", "brand_name", "recall_details", mode="before")
    @classmethod
    def strip_text(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value

    @field_validator("recall_code", mode="before")
    @classmethod
    def normalize_recall_code(cls, value: object) -> object:
        return value.strip().upper() if isinstance(value, str) else value

    @field_validator("category")
    @classmethod
    def category_is_allowed(cls, value: str) -> str:
        if value not in CATEGORIES:
            raise ValueError("select a valid grocery category")
        return value

    @field_validator("terms_accepted")
    @classmethod
    def terms_are_required(cls, value: bool) -> bool:
        if not value:
            raise ValueError("terms and conditions must be accepted")
        return value


class RecallCreate(RecallInput):
    pass


class RecallUpdate(RecallInput):
    pass


class RecallEventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    recall_id: int
    event_type: str
    note: str
    created_at: datetime


class RecallResponse(RecallInput):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    updated_at: datetime
    manufacturer: ManufacturerResponse | None = None
    events: list[RecallEventResponse] = Field(default_factory=list)


class RecallListResponse(BaseModel):
    implementation: str
    page: int = 1
    page_size: int
    total: int = 0
    sql_queries: int
    records: list[RecallResponse]
