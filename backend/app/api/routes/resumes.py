from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.pipeline import parse_resume_record
from app.api.deps import get_db_session
from app.db.models.enums import AITaskType, ParseStatus
from app.db.repositories.ai_run_repository import list_ai_runs_for_session
from app.db.repositories.resume_repository import create_resume, get_resume
from app.schemas.parsing import (
    AIRunRead,
    ParseDiagnosticsRead,
    ResumeParseRead,
    ResumeParseRequest,
)
from app.schemas.resume import ResumeCreate, ResumeRead

DbSession = Depends(get_db_session)

router = APIRouter(prefix="/api/resumes", tags=["resumes"])


@router.post("", response_model=ResumeRead, status_code=status.HTTP_201_CREATED)
async def create_resume_endpoint(
    payload: ResumeCreate,
    session: AsyncSession = DbSession,
) -> ResumeRead:
    resume = await create_resume(session, payload)
    return ResumeRead.model_validate(resume)


@router.get("/{resume_id}", response_model=ResumeRead)
async def get_resume_endpoint(
    resume_id: str,
    session: AsyncSession = DbSession,
) -> ResumeRead:
    resume = await get_resume(session, resume_id)
    if resume is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resume not found")
    return ResumeRead.model_validate(resume)


@router.post("/{resume_id}/parse", response_model=ResumeParseRead)
async def parse_resume_endpoint(
    resume_id: str,
    payload: ResumeParseRequest,
    session: AsyncSession = DbSession,
) -> ResumeParseRead:
    resume = await get_resume(session, resume_id)
    if resume is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resume not found")

    if resume.parse_status == ParseStatus.COMPLETED.value and not payload.force_reparse:
        return ResumeParseRead.model_validate(resume)

    parsed_resume = await parse_resume_record(session, resume)
    return ResumeParseRead.model_validate(parsed_resume)


@router.get("/{resume_id}/parse-diagnostics", response_model=ParseDiagnosticsRead)
async def get_resume_parse_diagnostics(
    resume_id: str,
    session: AsyncSession = DbSession,
) -> ParseDiagnosticsRead:
    resume = await get_resume(session, resume_id)
    if resume is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resume not found")

    ai_runs = await list_ai_runs_for_session(session, resume.session_id, AITaskType.RESUME_PARSE)
    return ParseDiagnosticsRead(ai_runs=[AIRunRead.model_validate(ai_run) for ai_run in ai_runs])
