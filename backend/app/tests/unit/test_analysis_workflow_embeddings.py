from __future__ import annotations

from types import SimpleNamespace
from typing import cast
from unittest.mock import AsyncMock, patch

import pytest

from app.db.models.job import Job
from app.db.models.resume import Resume


@pytest.mark.asyncio
async def test_run_analysis_builds_embeddings_before_matching_when_inputs_already_parsed() -> None:
    from app.services.ingestion.workflow import run_analysis

    resume = cast(
        Resume,
        SimpleNamespace(
            id="resume-1",
            parse_status="completed",
            parsed_json={"skills": ["Python"]},
        ),
    )
    job = cast(
        Job,
        SimpleNamespace(
            id="job-1",
            parse_status="completed",
            parsed_json={"required_skills": ["Python"]},
        ),
    )
    report = SimpleNamespace(id="report-1")
    optimization = SimpleNamespace(id="opt-1")

    session = AsyncMock()

    with (
        patch(
            "app.services.ingestion.workflow.ensure_resume_embeddings",
            new=AsyncMock(),
        ) as ensure_resume_embeddings,
        patch(
            "app.services.ingestion.workflow.ensure_job_embeddings",
            new=AsyncMock(),
        ) as ensure_job_embeddings,
        patch(
            "app.services.ingestion.workflow.create_match_report_record",
            new=AsyncMock(return_value=report),
        ) as create_match_report_record,
        patch(
            "app.services.ingestion.workflow.get_match_report",
            new=AsyncMock(return_value=report),
        ),
        patch(
            "app.services.ingestion.workflow.optimize_resume_for_match",
            new=AsyncMock(return_value=optimization),
        ),
        patch(
            "app.services.ingestion.workflow.get_optimized_resume",
            new=AsyncMock(return_value=optimization),
        ),
    ):
        bundle = await run_analysis(session, resume=resume, job=job)

    assert bundle.resume is resume
    assert bundle.job is job
    ensure_resume_embeddings.assert_awaited_once_with(session, resume)
    ensure_job_embeddings.assert_awaited_once_with(session, job)
    create_match_report_record.assert_awaited_once_with(session, resume, job)


@pytest.mark.asyncio
async def test_run_analysis_builds_embeddings_after_parsing_unparsed_inputs() -> None:
    from app.services.ingestion.workflow import run_analysis

    unparsed_resume = cast(
        Resume,
        SimpleNamespace(id="resume-1", parse_status="pending"),
    )
    unparsed_job = cast(
        Job,
        SimpleNamespace(id="job-1", parse_status="pending"),
    )
    parsed_resume = cast(
        Resume,
        SimpleNamespace(
            id="resume-1",
            parse_status="completed",
            parsed_json={"skills": ["Python"]},
        ),
    )
    parsed_job = cast(
        Job,
        SimpleNamespace(
            id="job-1",
            parse_status="completed",
            parsed_json={"required_skills": ["Python"]},
        ),
    )
    report = SimpleNamespace(id="report-1")
    optimization = SimpleNamespace(id="opt-1")

    session = AsyncMock()

    with (
        patch(
            "app.services.ingestion.workflow.parse_resume_record",
            new=AsyncMock(return_value=parsed_resume),
        ) as parse_resume_record,
        patch(
            "app.services.ingestion.workflow.parse_job_record",
            new=AsyncMock(return_value=parsed_job),
        ) as parse_job_record,
        patch(
            "app.services.ingestion.workflow.ensure_resume_embeddings",
            new=AsyncMock(),
        ) as ensure_resume_embeddings,
        patch(
            "app.services.ingestion.workflow.ensure_job_embeddings",
            new=AsyncMock(),
        ) as ensure_job_embeddings,
        patch(
            "app.services.ingestion.workflow.create_match_report_record",
            new=AsyncMock(return_value=report),
        ) as create_match_report_record,
        patch(
            "app.services.ingestion.workflow.get_match_report",
            new=AsyncMock(return_value=report),
        ),
        patch(
            "app.services.ingestion.workflow.optimize_resume_for_match",
            new=AsyncMock(return_value=optimization),
        ),
        patch(
            "app.services.ingestion.workflow.get_optimized_resume",
            new=AsyncMock(return_value=optimization),
        ),
    ):
        bundle = await run_analysis(session, resume=unparsed_resume, job=unparsed_job)

    assert bundle.resume is parsed_resume
    assert bundle.job is parsed_job
    parse_resume_record.assert_awaited_once_with(session, unparsed_resume)
    parse_job_record.assert_awaited_once_with(session, unparsed_job)
    ensure_resume_embeddings.assert_awaited_once_with(session, parsed_resume)
    ensure_job_embeddings.assert_awaited_once_with(session, parsed_job)
    create_match_report_record.assert_awaited_once_with(session, parsed_resume, parsed_job)


@pytest.mark.asyncio
async def test_ensure_resume_embeddings_persists_fallback_metadata() -> None:
    from app.ai.embeddings.base import EmbeddingBatchResult
    from app.ai.embeddings.factory import EmbeddingClientSelection
    from app.services.ingestion.workflow import ensure_resume_embeddings

    class FakeFallbackEmbeddingClient:
        provider = "deterministic-fallback"
        model_name = "deterministic-token-hash"
        dimension = 4

        def embed_texts(self, texts: list[str]) -> EmbeddingBatchResult:
            return EmbeddingBatchResult(
                provider=self.provider,
                model_name=self.model_name,
                dimension=self.dimension,
                vectors=[[1.0, 0.0, 0.0, 0.0] for _ in texts],
                metadata={"runtime": "deterministic", "fallback_reason": "missing runtime"},
            )

    resume = cast(
        Resume,
        SimpleNamespace(
            id="resume-1",
            parsed_json={"skills": ["Python"]},
        ),
    )
    session = AsyncMock()

    with (
        patch(
            "app.services.ingestion.workflow.get_embedding_client",
            return_value=EmbeddingClientSelection(
                client=FakeFallbackEmbeddingClient(),
                warning="Local embedding runtime unavailable",
            ),
        ),
        patch(
            "app.services.ingestion.workflow.replace_resume_embeddings",
            new=AsyncMock(),
        ) as replace_resume_embeddings,
    ):
        await ensure_resume_embeddings(session, resume)

    replace_resume_embeddings.assert_awaited_once()
    assert replace_resume_embeddings.await_args is not None
    embeddings = replace_resume_embeddings.await_args.args[2]
    assert embeddings[0].metadata_json == {
        "provider": "deterministic-fallback",
        "runtime": "deterministic",
        "fallback_reason": "missing runtime",
    }
