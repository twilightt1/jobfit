from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.pipeline.optimization import optimize_resume_for_match
from app.api.deps import get_db_session
from app.db.repositories.job_repository import get_job
from app.db.repositories.match_report_repository import get_match_report
from app.db.repositories.optimization_repository import (
    get_latest_optimized_resume_for_match,
    get_optimized_resume,
)
from app.db.repositories.resume_repository import get_resume
from app.schemas.optimization import OptimizationCreate, OptimizedResumeRead

DbSession = Depends(get_db_session)

router = APIRouter(prefix="/api/optimizations", tags=["optimizations"])


@router.post("", response_model=OptimizedResumeRead, status_code=status.HTTP_201_CREATED)
async def create_optimization_endpoint(
    payload: OptimizationCreate,
    session: AsyncSession = DbSession,
) -> OptimizedResumeRead:
    existing = await get_latest_optimized_resume_for_match(session, payload.match_report_id)
    if existing is not None and not payload.force_regenerate:
        return OptimizedResumeRead.model_validate(existing)

    match_report = await get_match_report(session, payload.match_report_id)
    if match_report is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Match report not found")

    resume = await get_resume(session, match_report.resume_id)
    if resume is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resume not found")

    job = await get_job(session, match_report.job_id)
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")

    if not resume.parsed_json:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Resume must be parsed before optimization",
        )
    if not job.parsed_json:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Job must be parsed before optimization",
        )

    optimized_resume = await optimize_resume_for_match(session, resume, job, match_report)
    loaded = await get_optimized_resume(session, optimized_resume.id)
    if loaded is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to load created optimized resume",
        )
    return OptimizedResumeRead.model_validate(loaded)


@router.get("/{optimized_resume_id}", response_model=OptimizedResumeRead)
async def get_optimization_endpoint(
    optimized_resume_id: str,
    session: AsyncSession = DbSession,
) -> OptimizedResumeRead:
    optimized_resume = await get_optimized_resume(session, optimized_resume_id)
    if optimized_resume is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Optimized resume not found",
        )
    return OptimizedResumeRead.model_validate(optimized_resume)
