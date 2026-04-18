from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import uuid4

from pgvector.sqlalchemy import Vector  # type: ignore[import-untyped]
from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class ResumeEmbedding(Base):
    """Vector embedding for a resume section or bullet."""

    __tablename__ = "resume_embeddings"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    resume_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("resumes.id", ondelete="CASCADE"), index=True
    )
    section_type: Mapped[str] = mapped_column(String(80), index=True)
    section_id: Mapped[str | None] = mapped_column(String(120))
    text: Mapped[str] = mapped_column(Text)

    embedding = mapped_column(Vector(384))
    embedding_model: Mapped[str] = mapped_column(String(255), index=True)
    embedding_version: Mapped[str] = mapped_column(String(80))
    dimension: Mapped[int] = mapped_column(Integer, default=384)
    metadata_json: Mapped[dict[str, Any] | None] = mapped_column(JSONB)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class JobEmbedding(Base):
    """Vector embedding for a job requirement or responsibility."""

    __tablename__ = "job_embeddings"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    job_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("jobs.id", ondelete="CASCADE"), index=True
    )
    requirement_type: Mapped[str] = mapped_column(String(80), index=True)
    requirement_id: Mapped[str | None] = mapped_column(String(120))
    text: Mapped[str] = mapped_column(Text)

    embedding = mapped_column(Vector(384))
    embedding_model: Mapped[str] = mapped_column(String(255), index=True)
    embedding_version: Mapped[str] = mapped_column(String(80))
    dimension: Mapped[int] = mapped_column(Integer, default=384)
    metadata_json: Mapped[dict[str, Any] | None] = mapped_column(JSONB)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
