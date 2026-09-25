"""Pydantic request and response models for Homework 4."""

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


class RecallInput(BaseModel):
    product_name: str = Field(min_length=2, max_length=160)
    brand_name: str = Field(min_length=2, max_length=160)
    submitter_email: EmailStr
    category: str
    recall_details: str = Field(min_length=26, max_length=2000)
    terms_accepted: bool

    @field_validator("product_name", "brand_name", "recall_details", mode="before")
    @classmethod
    def strip_text(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value

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
    events: list[RecallEventResponse] = Field(default_factory=list)


class RecallListResponse(BaseModel):
    implementation: str
    page_size: int
    sql_queries: int
    records: list[RecallResponse]
