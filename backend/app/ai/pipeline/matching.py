from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.embeddings.semantic import (
    find_best_semantic_requirement_matches,
    find_best_semantic_skill_matches,
)
from app.ai.schemas import JobExtraction, ResumeExtraction
from app.ai.scoring.match_engine import DeterministicMatchEngine, MatchComputationResult
from app.db.models.embedding import JobEmbedding, ResumeEmbedding
from app.db.models.job import Job
from app.db.models.match_report import MatchEvidence, MatchReport
from app.db.models.resume import Resume

SEMANTIC_SCORE_THRESHOLD = 0.8

SemanticMatchMaps = tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]]]


async def _load_resume_embeddings(session: AsyncSession, resume_id: str) -> list[ResumeEmbedding]:
    statement = select(ResumeEmbedding).where(ResumeEmbedding.resume_id == resume_id)
    result = await session.execute(statement)
    return list(result.scalars().all())


async def _load_job_embeddings(session: AsyncSession, job_id: str) -> list[JobEmbedding]:
    statement = select(JobEmbedding).where(JobEmbedding.job_id == job_id)
    result = await session.execute(statement)
    return list(result.scalars().all())


def _build_semantic_match_maps(
    resume_embeddings: list[ResumeEmbedding],
    job_embeddings: list[JobEmbedding],
) -> SemanticMatchMaps:
    semantic_skill_matches = find_best_semantic_skill_matches(
        resume_embeddings,
        job_embeddings,
        score_threshold=SEMANTIC_SCORE_THRESHOLD,
    )
    semantic_requirement_matches = find_best_semantic_requirement_matches(
        resume_embeddings,
        job_embeddings,
        score_threshold=SEMANTIC_SCORE_THRESHOLD,
    )
    return semantic_skill_matches, semantic_requirement_matches


def _build_metadata_json(
    resume: Resume,
    job: Job,
    result: MatchComputationResult,
    semantic_skill_matches: dict[str, dict[str, Any]],
    semantic_requirement_matches: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    return {
        "engine": "hybrid-semantic-v1",
        "base_engine": "deterministic-v1",
        "semantic_score_threshold": SEMANTIC_SCORE_THRESHOLD,
        "resume_parse_confidence": resume.parse_confidence,
        "job_parse_confidence": job.parse_confidence,
        "matched_skills": result.matched_skills,
        "missing_skills": result.missing_skills,
        "semantic_skill_match_count": len(semantic_skill_matches),
        "semantic_requirement_match_count": len(semantic_requirement_matches),
        "semantic_embedding_models": _semantic_metadata_values(
            semantic_skill_matches,
            semantic_requirement_matches,
            "embedding_model",
        ),
        "semantic_embedding_providers": _semantic_metadata_values(
            semantic_skill_matches,
            semantic_requirement_matches,
            "embedding_provider",
        ),
    }


def _semantic_metadata_values(
    semantic_skill_matches: dict[str, dict[str, Any]],
    semantic_requirement_matches: dict[str, dict[str, Any]],
    key: str,
) -> list[object]:
    values = {
        match[key]
        for match in [
            *semantic_skill_matches.values(),
            *semantic_requirement_matches.values(),
        ]
        if match.get(key) is not None
    }
    return sorted(values, key=str)


def _build_report_from_result(
    resume: Resume,
    job: Job,
    result: MatchComputationResult,
    semantic_skill_matches: dict[str, dict[str, Any]],
    semantic_requirement_matches: dict[str, dict[str, Any]],
) -> MatchReport:
    metadata_json = _build_metadata_json(
        resume,
        job,
        result,
        semantic_skill_matches,
        semantic_requirement_matches,
    )
    return MatchReport(
        user_id=resume.user_id or job.user_id,
        session_id=resume.session_id or job.session_id,
        resume_id=resume.id,
        job_id=job.id,
        overall_score=result.overall_score,
        analysis_confidence=result.analysis_confidence,
        breakdown_json=result.breakdown,
        strengths_json=result.strengths,
        gaps_json=result.gaps,
        recommendations_json=result.recommendations,
        ats_report_json=result.ats_report,
        explanation_json=result.explanation,
        model_metadata_json=metadata_json,
    )


async def create_match_report_record(
    session: AsyncSession,
    resume: Resume,
    job: Job,
) -> MatchReport:
    resume_extraction = ResumeExtraction.model_validate(resume.parsed_json or {})
    job_extraction = JobExtraction.model_validate(job.parsed_json or {})
    resume_embeddings = await _load_resume_embeddings(session, resume.id)
    job_embeddings = await _load_job_embeddings(session, job.id)
    semantic_skill_matches, semantic_requirement_matches = _build_semantic_match_maps(
        resume_embeddings,
        job_embeddings,
    )

    engine = DeterministicMatchEngine()
    result = engine.compute(
        resume_extraction,
        job_extraction,
        resume_parse_confidence=resume.parse_confidence,
        job_parse_confidence=job.parse_confidence,
        semantic_skill_matches=semantic_skill_matches,
        semantic_requirement_matches=semantic_requirement_matches,
    )

    report = _build_report_from_result(
        resume,
        job,
        result,
        semantic_skill_matches,
        semantic_requirement_matches,
    )
    session.add(report)
    await session.flush()

    for item in result.evidence:
        session.add(
            MatchEvidence(
                match_report_id=report.id,
                requirement_id=item.requirement_id,
                job_requirement_text=item.job_requirement_text,
                resume_section_id=item.resume_section_id,
                resume_section_type=item.resume_section_type,
                resume_evidence_text=item.resume_evidence_text,
                match_type=item.match_type,
                match_status=item.match_status,
                similarity_score=item.similarity_score,
                confidence=item.confidence,
                explanation=item.explanation,
                metadata_json=item.metadata_json,
            )
        )

    await session.commit()
    await session.refresh(report)
    return report


