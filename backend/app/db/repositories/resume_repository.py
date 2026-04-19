from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.resume import Resume
from app.schemas.resume import ResumeCreate


async def create_resume(session: AsyncSession, payload: ResumeCreate) -> Resume:
    resume = Resume(
        title=payload.title,
        raw_text=payload.raw_text,
        session_id=payload.session_id,
    )
    session.add(resume)
    await session.commit()
    await session.refresh(resume)
    return resume


async def get_resume(session: AsyncSession, resume_id: str) -> Resume | None:
    return await session.get(Resume, resume_id)
