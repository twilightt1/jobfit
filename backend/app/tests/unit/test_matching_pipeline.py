from __future__ import annotations

from types import SimpleNamespace
from typing import cast
from unittest.mock import AsyncMock, patch

import pytest

from app.db.models.embedding import JobEmbedding, ResumeEmbedding
from app.db.models.job import Job
from app.db.models.resume import Resume


def _make_fake_result() -> SimpleNamespace:
    return SimpleNamespace(
        overall_score=88,
        analysis_confidence=0.87,
        breakdown={
            "skills": {"score": 100, "matched": ["fastapi"], "missing": []},
            "requirements": {"score": 100, "evaluated": 1},
            "experience": {"score": 100, "years": 4},
            "languages": {"score": 100, "matched": ["English"]},
        },
        strengths=["Resume demonstrates fastapi."],
        gaps=[],
        recommendations=[],
        ats_report={
            "keywords_matched": ["fastapi"],
            "keywords_missing": [],
            "coverage_ratio": 1.0,
            "warnings": [],
        },
        explanation={"summary": "Strong fit."},
        evidence=[],
        missing_skills=[],
        matched_skills=["fastapi"],
    )


def _fake_resume() -> Resume:
    return cast(
        Resume,
        SimpleNamespace(
            id="resume-1",
            user_id=None,
            session_id="session-1",
            parsed_json={
                "skills": [],
                "experience_highlights": [
                    "Built and operated REST APIs for ML model serving."
                ],
                "languages": ["English"],
                "total_years_experience": 4,
            },
            parse_confidence=0.9,
        ),
    )


def _fake_job() -> Job:
    return cast(
        Job,
        SimpleNamespace(
            id="job-1",
            user_id=None,
            session_id="session-1",
            parsed_json={
                "required_skills": ["FastAPI"],
                "requirements": [
                    {
                        "requirement": (
                            "Experience building FastAPI services for model inference."
                        ),
                        "requirement_type": "required",
                    }
                ],
                "seniority": "mid",
            },
            parse_confidence=0.92,
        ),
    )


def _fake_session() -> AsyncMock:
    session = AsyncMock()
    session.flush = AsyncMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    session.add = lambda report: None
    return session


def _resume_embeddings() -> list[ResumeEmbedding]:
    return [
        ResumeEmbedding(
            resume_id="resume-1",
            section_type="experience",
            section_id="experience:0",
            text="Built and operated REST APIs for ML model serving.",
            embedding=[1.0, 0.0, 0.0, 0.0],
            embedding_model="mini",
            embedding_version="v1",
            dimension=4,
            metadata_json={"provider": "local"},
        )
    ]


def _job_embeddings() -> list[JobEmbedding]:
    return [
        JobEmbedding(
            job_id="job-1",
            requirement_type="required_skill",
            requirement_id="required_skill:0",
            text="FastAPI",
            embedding=[0.9, 0.1, 0.0, 0.0],
            embedding_model="mini",
            embedding_version="v1",
            dimension=4,
            metadata_json={"provider": "local"},
        ),
        JobEmbedding(
            job_id="job-1",
            requirement_type="requirement",
            requirement_id="req:1",
            text="Experience building FastAPI services for model inference.",
            embedding=[0.95, 0.05, 0.0, 0.0],
            embedding_model="mini",
            embedding_version="v1",
            dimension=4,
            metadata_json={"provider": "local"},
        ),
    ]


@pytest.mark.asyncio
async def test_create_match_report_record_uses_semantic_embedding_matches() -> None:
    from app.ai.pipeline.matching import create_match_report_record

    resume = _fake_resume()
    job = _fake_job()
    session = _fake_session()

    with (
        patch(
            "app.ai.pipeline.matching._load_resume_embeddings",
            new=AsyncMock(return_value=_resume_embeddings()),
        ),
        patch(
            "app.ai.pipeline.matching._load_job_embeddings",
            new=AsyncMock(return_value=_job_embeddings()),
        ),
        patch("app.ai.pipeline.matching.DeterministicMatchEngine") as engine_cls,
    ):
        engine = engine_cls.return_value
        engine.compute.return_value = _make_fake_result()

        report = await create_match_report_record(session, resume, job)

    engine.compute.assert_called_once()
    call_kwargs = engine.compute.call_args.kwargs
    assert call_kwargs["semantic_skill_matches"]["fastapi"]["match_type"] == "semantic"
    assert call_kwargs["semantic_requirement_matches"]["req:1"]["match_type"] == "semantic"
    assert report.model_metadata_json is not None
    assert report.model_metadata_json["engine"] == "hybrid-semantic-v1"
    assert report.model_metadata_json["base_engine"] == "deterministic-v1"
    assert report.model_metadata_json["semantic_score_threshold"] == 0.8
    assert report.model_metadata_json["semantic_skill_match_count"] == 1
    assert report.model_metadata_json["semantic_requirement_match_count"] == 1
    assert report.model_metadata_json["semantic_embedding_models"] == ["mini"]
    assert report.model_metadata_json["semantic_embedding_providers"] == ["local"]


@pytest.mark.asyncio
async def test_create_match_report_record_sets_zero_semantic_counts_when_no_matches() -> None:
    from app.ai.pipeline.matching import create_match_report_record

    resume = _fake_resume()
    job = _fake_job()
    session = _fake_session()

    with (
        patch(
            "app.ai.pipeline.matching._load_resume_embeddings",
            new=AsyncMock(return_value=[]),
        ),
        patch(
            "app.ai.pipeline.matching._load_job_embeddings",
            new=AsyncMock(return_value=[]),
        ),
        patch("app.ai.pipeline.matching.DeterministicMatchEngine") as engine_cls,
    ):
        engine = engine_cls.return_value
        engine.compute.return_value = _make_fake_result()

        report = await create_match_report_record(session, resume, job)

    assert report.model_metadata_json is not None
    assert report.model_metadata_json["semantic_skill_match_count"] == 0
    assert report.model_metadata_json["semantic_requirement_match_count"] == 0
    assert report.model_metadata_json["semantic_embedding_models"] == []
    assert report.model_metadata_json["semantic_embedding_providers"] == []
    assert report.model_metadata_json["matched_skills"] == ["fastapi"]
    assert report.model_metadata_json["missing_skills"] == []
