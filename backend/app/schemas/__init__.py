"""Pydantic API schemas."""

from app.schemas.job import JobCreate, JobRead
from app.schemas.match_report import MatchEvidenceRead, MatchReportCreate, MatchReportRead
from app.schemas.optimization import (
    OptimizationCreate,
    OptimizedResumeRead,
    RewriteSuggestionRead,
)
from app.schemas.parsing import (
    AIRunRead,
    JobParseRead,
    JobParseRequest,
    ParseDiagnosticsRead,
    ResumeParseRead,
    ResumeParseRequest,
)
from app.schemas.resume import ResumeCreate, ResumeRead

__all__ = [
    "AIRunRead",
    "JobCreate",
    "JobParseRead",
    "JobParseRequest",
    "JobRead",
    "MatchEvidenceRead",
    "MatchReportCreate",
    "MatchReportRead",
    "OptimizationCreate",
    "OptimizedResumeRead",
    "ParseDiagnosticsRead",
    "ResumeCreate",
    "ResumeParseRead",
    "ResumeParseRequest",
    "ResumeRead",
    "RewriteSuggestionRead",
]
