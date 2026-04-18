from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import uuid4

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class OptimizedResume(Base):
    """Job-specific optimized resume version."""

    __tablename__ = "optimized_resumes"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), index=True
    )
    session_id: Mapped[str | None] = mapped_column(String(120), index=True)
    resume_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("resumes.id", ondelete="CASCADE"), index=True
    )
    job_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("jobs.id", ondelete="CASCADE"), index=True
    )
    match_report_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("match_reports.id", ondelete="SET NULL"), index=True
    )

    version_name: Mapped[str] = mapped_column(String(255))
    content_json: Mapped[dict[str, Any]] = mapped_column(JSONB)
    score_before: Mapped[int | None] = mapped_column(Integer)
    score_after: Mapped[int | None] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(40), default="draft", index=True)

    generated_by_ai_run_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("ai_runs.id", ondelete="SET NULL")
    )

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    suggestions = relationship(
        "RewriteSuggestion", back_populates="optimized_resume", cascade="all, delete-orphan"
    )


class RewriteSuggestion(Base):
    """One AI resume rewrite suggestion and truth-guard decision."""

    __tablename__ = "rewrite_suggestions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    optimized_resume_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("optimized_resumes.id", ondelete="CASCADE"), index=True
    )

    section_type: Mapped[str] = mapped_column(String(80), index=True)
    target_location: Mapped[str | None] = mapped_column(String(255))
    original_text: Mapped[str | None] = mapped_column(Text)
    suggested_text: Mapped[str] = mapped_column(Text)
    user_edited_text: Mapped[str | None] = mapped_column(Text)

    targeted_requirements: Mapped[list[Any] | None] = mapped_column(JSONB)
    keywords_added: Mapped[list[Any] | None] = mapped_column(JSONB)
    reason: Mapped[str | None] = mapped_column(Text)
    estimated_score_lift: Mapped[int | None] = mapped_column(Integer)

    truth_status: Mapped[str] = mapped_column(String(40), default="safe", index=True)
    new_claims_json: Mapped[list[Any] | None] = mapped_column(JSONB)
    guardrail_reason: Mapped[str | None] = mapped_column(Text)

    decision: Mapped[str] = mapped_column(String(40), default="pending", index=True)
    accepted_by_user: Mapped[bool] = mapped_column(default=False)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    generated_by_ai_run_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("ai_runs.id", ondelete="SET NULL")
    )

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    optimized_resume = relationship("OptimizedResume", back_populates="suggestions")
