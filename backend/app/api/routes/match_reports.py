from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.pipeline.matching import create_match_report_record
from app.api.deps import get_db_session
from app.db.repositories.job_repository import get_job
from app.db.repositories.match_report_repository import (
    get_match_report,
    get_match_report_by_resume_job,
)
from app.db.repositories.resume_repository import get_resume
from app.schemas.match_report import MatchReportCreate, MatchReportRead

DbSession = Depends(get_db_session)

router = APIRouter(prefix="/api/match-reports", tags=["match-reports"])


@router.post("", response_model=MatchReportRead, status_code=status.HTTP_201_CREATED)
async def create_match_report_endpoint(
    payload: MatchReportCreate,
    session: AsyncSession = DbSession,
) -> MatchReportRead:
    existing_report = await get_match_report_by_resume_job(
        session,
        payload.resume_id,
        payload.job_id,
    )
    if existing_report is not None:
        return MatchReportRead.model_validate(existing_report)

    resume = await get_resume(session, payload.resume_id)
    if resume is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resume not found")

    job = await get_job(session, payload.job_id)
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")

    if not resume.parsed_json:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Resume must be parsed before creating a match report",
        )
    if not job.parsed_json:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Job must be parsed before creating a match report",
        )

    report = await create_match_report_record(session, resume, job)
    loaded_report = await get_match_report(session, report.id)
    if loaded_report is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to load created match report",
        )
    return MatchReportRead.model_validate(loaded_report)


@router.get("/{report_id}", response_model=MatchReportRead)
async def get_match_report_endpoint(
    report_id: str,
    session: AsyncSession = DbSession,
) -> MatchReportRead:
    report = await get_match_report(session, report_id)
    if report is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Match report not found")
    return MatchReportRead.model_validate(report)
