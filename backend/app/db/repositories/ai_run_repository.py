from __future__ import annotations

from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.ai_run import AIRun
from app.db.models.enums import AITaskType


async def list_ai_runs_for_session(
    session: AsyncSession,
    session_id: str | None,
    task_type: AITaskType | None = None,
) -> list[AIRun]:
    statement: Select[tuple[AIRun]] = select(AIRun).order_by(AIRun.created_at.desc())

    if session_id is not None:
        statement = statement.where(AIRun.session_id == session_id)
    if task_type is not None:
        statement = statement.where(AIRun.task_type == task_type.value)

    result = await session.execute(statement)
    return list(result.scalars().all())
