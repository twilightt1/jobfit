from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models.match_report import MatchReport


async def get_match_report(session: AsyncSession, report_id: str) -> MatchReport | None:
    statement = (
        select(MatchReport)
        .options(selectinload(MatchReport.evidence))
        .where(MatchReport.id == report_id)
    )
    result = await session.execute(statement)
    return result.scalar_one_or_none()


async def get_match_report_by_resume_job(
    session: AsyncSession,
    resume_id: str,
    job_id: str,
) -> MatchReport | None:
    statement = (
        select(MatchReport)
        .options(selectinload(MatchReport.evidence))
        .where(MatchReport.resume_id == resume_id, MatchReport.job_id == job_id)
    )
    result = await session.execute(statement)
    return result.scalar_one_or_none()
