from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class MatchReportCreate(BaseModel):
    resume_id: str
    job_id: str


class MatchEvidenceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    requirement_id: str | None
    job_requirement_text: str
    resume_section_id: str | None
    resume_section_type: str | None
    resume_evidence_text: str | None
    match_type: str
    match_status: str
    similarity_score: float | None
    confidence: float | None
    explanation: str | None
    metadata_json: dict[str, Any] | None
    created_at: datetime


class MatchReportRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str | None
    session_id: str | None
    resume_id: str
    job_id: str
    overall_score: int
    analysis_confidence: float | None
    breakdown_json: dict[str, Any]
    strengths_json: list[str] | None
    gaps_json: list[str] | None
    recommendations_json: list[str] | None
    ats_report_json: dict[str, Any] | None
    explanation_json: dict[str, Any] | None
    model_metadata_json: dict[str, Any] | None
    created_at: datetime
    updated_at: datetime
    evidence: list[MatchEvidenceRead] = Field(default_factory=list)
