"""Repository helpers."""

from app.db.repositories.ai_run_repository import list_ai_runs_for_session
from app.db.repositories.job_repository import create_job, get_job
from app.db.repositories.match_report_repository import (
    get_match_report,
    get_match_report_by_resume_job,
)
from app.db.repositories.optimization_repository import (
    get_latest_optimized_resume_for_match,
    get_optimized_resume,
)
from app.db.repositories.resume_repository import create_resume, get_resume

__all__ = [
    "create_job",
    "create_resume",
    "get_job",
    "get_latest_optimized_resume_for_match",
    "get_match_report",
    "get_match_report_by_resume_job",
    "get_optimized_resume",
    "get_resume",
    "list_ai_runs_for_session",
]
