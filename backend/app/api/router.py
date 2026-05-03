from fastapi import APIRouter

from app.api.routes import health, jobs, match_reports, resumes

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(resumes.router)
api_router.include_router(jobs.router)
api_router.include_router(match_reports.router)
