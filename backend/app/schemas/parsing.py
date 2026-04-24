from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ResumeParseRequest(BaseModel):
    force_reparse: bool = False


class ResumeParseRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    parse_status: str
    parse_confidence: float | None
    parsed_json: dict[str, Any] | None
    parse_warnings: list[Any] | None
    parse_error: str | None
    updated_at: datetime


class JobParseRequest(BaseModel):
    force_reparse: bool = False


class JobParseRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    parse_status: str
    parse_confidence: float | None
    parsed_json: dict[str, Any] | None
    parse_warnings: list[Any] | None
    parse_error: str | None
    updated_at: datetime


class AIRunRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    task_type: str
    status: str
    provider: str
    model_name: str
    prompt_name: str | None
    prompt_version: str | None
    schema_version: str | None
    validation_status: str
    latency_ms: int | None
    created_at: datetime


class ParseDiagnosticsRead(BaseModel):
    ai_runs: list[AIRunRead] = Field(default_factory=list)
