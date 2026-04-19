from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ResumeCreate(BaseModel):
    title: str = Field(default="Untitled Resume", max_length=255)
    raw_text: str = Field(min_length=20)
    session_id: str | None = Field(default=None, max_length=120)


class ResumeRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    title: str
    raw_text: str
    parse_status: str
    parse_confidence: float | None
    parsed_json: dict[str, Any] | None
    session_id: str | None
    created_at: datetime
    updated_at: datetime
