from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class OptimizationCreate(BaseModel):
    match_report_id: str
    force_regenerate: bool = False


class RewriteSuggestionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    optimized_resume_id: str
    section_type: str
    target_location: str | None
    original_text: str | None
    suggested_text: str
    user_edited_text: str | None
    targeted_requirements: list[Any] | None
    keywords_added: list[Any] | None
    reason: str | None
    estimated_score_lift: int | None
    truth_status: str
    new_claims_json: list[Any] | None
    guardrail_reason: str | None
    decision: str
    accepted_by_user: bool
    generated_by_ai_run_id: str | None
    created_at: datetime
    updated_at: datetime


class OptimizedResumeRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str | None
    session_id: str | None
    resume_id: str
    job_id: str
    match_report_id: str | None
    version_name: str
    content_json: dict[str, Any]
    score_before: int | None
    score_after: int | None
    status: str
    generated_by_ai_run_id: str | None
    created_at: datetime
    updated_at: datetime
    suggestions: list[RewriteSuggestionRead] = Field(default_factory=list)
