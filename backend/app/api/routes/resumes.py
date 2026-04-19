from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db_session
from app.db.repositories.resume_repository import create_resume, get_resume
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
