from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db_session
from app.db.repositories.job_repository import create_job, get_job
from app.schemas.job import JobCreate, JobRead

DbSession = Depends(get_db_session)

router = APIRouter(prefix="/api/jobs", tags=["jobs"])


@router.post("", response_model=JobRead, status_code=status.HTTP_201_CREATED)
async def create_job_endpoint(
    payload: JobCreate,
    session: AsyncSession = DbSession,
) -> JobRead:
    job = await create_job(session, payload)
    return JobRead.model_validate(job)


@router.get("/{job_id}", response_model=JobRead)
async def get_job_endpoint(
    job_id: str,
    session: AsyncSession = DbSession,
) -> JobRead:
    job = await get_job(session, job_id)
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    return JobRead.model_validate(job)
