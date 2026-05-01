from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.schemas import JobExtraction, ResumeExtraction
from app.ai.scoring.match_engine import DeterministicMatchEngine, MatchComputationResult
from app.db.models.job import Job
from app.db.models.match_report import MatchEvidence, MatchReport
from app.db.models.resume import Resume


async def create_match_report_record(
    session: AsyncSession,
    resume: Resume,
    job: Job,
) -> MatchReport:
    resume_extraction = ResumeExtraction.model_validate(resume.parsed_json or {})
    job_extraction = JobExtraction.model_validate(job.parsed_json or {})

    engine = DeterministicMatchEngine()
    result = engine.compute(
        resume_extraction,
        job_extraction,
        resume_parse_confidence=resume.parse_confidence,
        job_parse_confidence=job.parse_confidence,
    )

    report = _build_match_report(resume, job, result)
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


def _build_match_report(
    resume: Resume,
    job: Job,
    result: MatchComputationResult,
) -> MatchReport:
    metadata_json: dict[str, Any] = {
        "engine": "deterministic-v1",
        "resume_parse_confidence": resume.parse_confidence,
        "job_parse_confidence": job.parse_confidence,
        "matched_skills": result.matched_skills,
        "missing_skills": result.missing_skills,
    }
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
