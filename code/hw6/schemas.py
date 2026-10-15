"""Pydantic request and response schemas for Homework 6."""

from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class RecallStatus(str, Enum):
    active = "active"
    monitoring = "monitoring"
    resolved = "resolved"


class RecallCategory(str, Enum):
    produce = "Produce"
    meat_seafood = "Meat and Seafood"
    dairy_refrigerated = "Dairy and Refrigerated"
    packaged_foods = "Packaged Foods"


class RecallDocumentBase(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    title: str = Field(min_length=2, max_length=100)
    description: str | None = Field(default=None, max_length=1000)
    status: RecallStatus = RecallStatus.active
    category: RecallCategory
    recalled_at: datetime

    @field_validator("description")
    @classmethod
    def blank_description_is_none(cls, value: str | None) -> str | None:
        return value or None


class RecallDocumentCreate(RecallDocumentBase):
    pass


class RecallDocumentUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    title: str | None = Field(default=None, min_length=2, max_length=100)
    description: str | None = Field(default=None, max_length=1000)
    status: RecallStatus | None = None
    category: RecallCategory | None = None
    recalled_at: datetime | None = None

    @model_validator(mode="after")
    def require_one_field(self) -> "RecallDocumentUpdate":
        if not self.model_fields_set:
            raise ValueError("at least one field must be supplied")
        return self


class RecallDocumentOut(RecallDocumentBase):
    id: str
    created_at: datetime
    updated_at: datetime


class ChatRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    user_id: str = Field(min_length=1, max_length=80, pattern=r"^[A-Za-z0-9_.-]+$")
    session_id: str | None = Field(
        default=None, min_length=1, max_length=80, pattern=r"^[A-Za-z0-9_.-]+$"
    )
    message: str = Field(min_length=1, max_length=4000)


class MemoryUsed(BaseModel):
    short_term_count: int
    short_term_messages: list[dict[str, str]]
    session_summary: str | None
    lifetime_summary: str | None
    episodic_facts: list[dict[str, object]]


class ChatResponse(BaseModel):
    user_id: str
    session_id: str
    reply: str
    memory_used: MemoryUsed
    usage: dict[str, int | float | str]
