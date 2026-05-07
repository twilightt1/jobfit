from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models.optimization import OptimizedResume


async def get_optimized_resume(
    session: AsyncSession,
    optimized_resume_id: str,
) -> OptimizedResume | None:
    statement = (
        select(OptimizedResume)
        .options(selectinload(OptimizedResume.suggestions))
        .where(OptimizedResume.id == optimized_resume_id)
    )
    result = await session.execute(statement)
    return result.scalar_one_or_none()


async def get_latest_optimized_resume_for_match(
    session: AsyncSession,
    match_report_id: str,
) -> OptimizedResume | None:
    statement = (
        select(OptimizedResume)
        .options(selectinload(OptimizedResume.suggestions))
        .where(OptimizedResume.match_report_id == match_report_id)
        .order_by(OptimizedResume.created_at.desc())
    )
    result = await session.execute(statement)
    return result.scalars().first()
