"""add optimization and embedding tables

Revision ID: 20260613_0002
Revises: 20260613_0001
Create Date: 2026-06-13
"""

from collections.abc import Sequence

import sqlalchemy as sa
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "20260613_0002"
down_revision: str | None = "20260613_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "optimized_resumes",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("user_id", sa.String(length=36), sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("session_id", sa.String(length=120), nullable=True),
        sa.Column(
            "resume_id",
            sa.String(length=36),
            sa.ForeignKey("resumes.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "job_id",
            sa.String(length=36),
            sa.ForeignKey("jobs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "match_report_id",
            sa.String(length=36),
            sa.ForeignKey("match_reports.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("version_name", sa.String(length=255), nullable=False),
        sa.Column("content_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("score_before", sa.Integer(), nullable=True),
        sa.Column("score_after", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(length=40), nullable=False, server_default="draft"),
        sa.Column(
            "generated_by_ai_run_id",
            sa.String(length=36),
            sa.ForeignKey("ai_runs.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_optimized_resumes_user_id", "optimized_resumes", ["user_id"])
    op.create_index("ix_optimized_resumes_session_id", "optimized_resumes", ["session_id"])
    op.create_index("ix_optimized_resumes_resume_id", "optimized_resumes", ["resume_id"])
    op.create_index("ix_optimized_resumes_job_id", "optimized_resumes", ["job_id"])
    op.create_index(
        "ix_optimized_resumes_match_report_id", "optimized_resumes", ["match_report_id"]
    )
    op.create_index("ix_optimized_resumes_status", "optimized_resumes", ["status"])

    op.create_table(
        "rewrite_suggestions",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column(
            "optimized_resume_id",
            sa.String(length=36),
            sa.ForeignKey("optimized_resumes.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("section_type", sa.String(length=80), nullable=False),
        sa.Column("target_location", sa.String(length=255), nullable=True),
        sa.Column("original_text", sa.Text(), nullable=True),
        sa.Column("suggested_text", sa.Text(), nullable=False),
        sa.Column("user_edited_text", sa.Text(), nullable=True),
        sa.Column("targeted_requirements", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("keywords_added", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("estimated_score_lift", sa.Integer(), nullable=True),
        sa.Column("truth_status", sa.String(length=40), nullable=False, server_default="safe"),
        sa.Column("new_claims_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("guardrail_reason", sa.Text(), nullable=True),
        sa.Column("decision", sa.String(length=40), nullable=False, server_default="pending"),
        sa.Column("accepted_by_user", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "generated_by_ai_run_id",
            sa.String(length=36),
            sa.ForeignKey("ai_runs.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index(
        "ix_rewrite_suggestions_optimized_resume_id", "rewrite_suggestions", ["optimized_resume_id"]
    )
    op.create_index("ix_rewrite_suggestions_section_type", "rewrite_suggestions", ["section_type"])
    op.create_index("ix_rewrite_suggestions_truth_status", "rewrite_suggestions", ["truth_status"])
    op.create_index("ix_rewrite_suggestions_decision", "rewrite_suggestions", ["decision"])

    op.create_table(
        "resume_embeddings",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column(
            "resume_id",
            sa.String(length=36),
            sa.ForeignKey("resumes.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("section_type", sa.String(length=80), nullable=False),
        sa.Column("section_id", sa.String(length=120), nullable=True),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("embedding", Vector(384), nullable=True),
        sa.Column("embedding_model", sa.String(length=255), nullable=False),
        sa.Column("embedding_version", sa.String(length=80), nullable=False),
        sa.Column("dimension", sa.Integer(), nullable=False, server_default="384"),
        sa.Column("metadata_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_resume_embeddings_resume_id", "resume_embeddings", ["resume_id"])
    op.create_index("ix_resume_embeddings_section_type", "resume_embeddings", ["section_type"])
    op.create_index(
        "ix_resume_embeddings_embedding_model", "resume_embeddings", ["embedding_model"]
    )

    op.create_table(
        "job_embeddings",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column(
            "job_id",
            sa.String(length=36),
            sa.ForeignKey("jobs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("requirement_type", sa.String(length=80), nullable=False),
        sa.Column("requirement_id", sa.String(length=120), nullable=True),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("embedding", Vector(384), nullable=True),
        sa.Column("embedding_model", sa.String(length=255), nullable=False),
        sa.Column("embedding_version", sa.String(length=80), nullable=False),
        sa.Column("dimension", sa.Integer(), nullable=False, server_default="384"),
        sa.Column("metadata_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_job_embeddings_job_id", "job_embeddings", ["job_id"])
    op.create_index("ix_job_embeddings_requirement_type", "job_embeddings", ["requirement_type"])
    op.create_index("ix_job_embeddings_embedding_model", "job_embeddings", ["embedding_model"])

    op.execute(
        "CREATE INDEX IF NOT EXISTS resume_embeddings_embedding_hnsw_idx "
        "ON resume_embeddings USING hnsw (embedding vector_cosine_ops)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS job_embeddings_embedding_hnsw_idx "
        "ON job_embeddings USING hnsw (embedding vector_cosine_ops)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS job_embeddings_embedding_hnsw_idx")
    op.execute("DROP INDEX IF EXISTS resume_embeddings_embedding_hnsw_idx")
    op.drop_table("job_embeddings")
    op.drop_table("resume_embeddings")
    op.drop_table("rewrite_suggestions")
    op.drop_table("optimized_resumes")
