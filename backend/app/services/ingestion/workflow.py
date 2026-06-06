from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from fastapi import HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.embeddings.factory import get_embedding_client
from app.ai.embeddings.indexing import (
    prepare_job_embeddings,
    prepare_resume_embeddings,
    replace_job_embeddings,
    replace_resume_embeddings,
)
from app.ai.pipeline import parse_job_record, parse_resume_record
from app.ai.pipeline.matching import create_match_report_record
from app.ai.pipeline.optimization import optimize_resume_for_match
from app.ai.schemas import JobExtraction, ResumeExtraction
from app.core.config import Settings, get_settings
from app.db.models.enums import ParseStatus, ResumeSourceType
from app.db.models.job import Job
from app.db.models.match_report import MatchReport
from app.db.models.optimization import OptimizedResume
from app.db.models.resume import Resume
from app.db.repositories.job_repository import create_job_from_ingestion
from app.db.repositories.match_report_repository import get_match_report
from app.db.repositories.optimization_repository import get_optimized_resume
from app.db.repositories.resume_repository import create_resume_from_ingestion
from app.services.ingestion.extractors import (
    IngestionError,
    extract_uploaded_text,
    validate_extracted_text,
)
from app.services.ingestion.filenames import title_from_filename
from app.services.ingestion.storage import save_upload_bytes
from app.services.ingestion.url_fetcher import fetch_job_description_from_url

JobInputType = Literal["text", "url", "file"]


@dataclass(slots=True)
class AnalysisBundle:
    resume: Resume
    job: Job
    match_report: MatchReport
    optimization: OptimizedResume


async def read_limited_upload(file: UploadFile, *, settings: Settings) -> bytes:
    """Read an UploadFile while enforcing the configured byte limit."""

    data = await file.read()
    if len(data) > settings.max_upload_bytes:
        raise IngestionError(
            f"Uploaded file is too large. Limit is {settings.max_upload_bytes // 1_000_000} MB."
        )
    return data


async def create_resume_from_upload(
    session: AsyncSession,
    *,
    file: UploadFile,
    settings: Settings,
    title: str | None = None,
    session_id: str | None = None,
    parse_immediately: bool = False,
) -> Resume:
    file_bytes = await read_limited_upload(file, settings=settings)
    extracted = extract_uploaded_text(
        file_bytes,
        filename=file.filename,
        content_type=file.content_type,
    )
    original_file_key = save_upload_bytes(
        file_bytes,
        filename=file.filename,
        kind="resumes",
        settings=settings,
    )
    resume_title = title or title_from_filename(file.filename, fallback="Uploaded Resume")
    resume = await create_resume_from_ingestion(
        session,
        title=resume_title,
        raw_text=extracted.text,
        session_id=session_id,
        source_type=_resume_source_type(extracted.source_kind.value),
        original_file_key=original_file_key,
    )
    if parse_immediately:
        return await parse_resume_record(session, resume)
    return resume


async def create_job_from_upload(
    session: AsyncSession,
    *,
    file: UploadFile,
    settings: Settings,
    title: str | None = None,
    company: str | None = None,
    session_id: str | None = None,
    parse_immediately: bool = False,
) -> Job:
    file_bytes = await read_limited_upload(file, settings=settings)
    extracted = extract_uploaded_text(
        file_bytes,
        filename=file.filename,
        content_type=file.content_type,
    )
    save_upload_bytes(file_bytes, filename=file.filename, kind="jobs", settings=settings)
    job_title = title or title_from_filename(file.filename, fallback="Uploaded Job Description")
    job = await create_job_from_ingestion(
        session,
        description=extracted.text,
        title=job_title,
        company=company,
        session_id=session_id,
    )
    if parse_immediately:
        return await parse_job_record(session, job)
    return job


async def create_job_from_url(
    session: AsyncSession,
    *,
    url: str,
    settings: Settings,
    title: str | None = None,
    company: str | None = None,
    session_id: str | None = None,
    parse_immediately: bool = False,
) -> Job:
    fetched = await fetch_job_description_from_url(url, settings=settings)
    job = await create_job_from_ingestion(
        session,
        description=fetched.text,
        title=title or fetched.title,
        company=company,
        session_id=session_id,
        source_url=fetched.url,
    )
    if parse_immediately:
        return await parse_job_record(session, job)
    return job


async def create_job_from_text(
    session: AsyncSession,
    *,
    text: str,
    title: str | None = None,
    company: str | None = None,
    session_id: str | None = None,
    parse_immediately: bool = False,
) -> Job:
    description = validate_extracted_text(text, source_label="job text")
    job = await create_job_from_ingestion(
        session,
        description=description,
        title=title,
        company=company,
        session_id=session_id,
    )
    if parse_immediately:
        return await parse_job_record(session, job)
    return job


async def create_resume_from_text(
    session: AsyncSession,
    *,
    text: str,
    title: str | None = None,
    session_id: str | None = None,
    parse_immediately: bool = False,
) -> Resume:
    raw_text = validate_extracted_text(text, source_label="resume text")
    resume = await create_resume_from_ingestion(
        session,
        title=title or "Pasted Resume",
        raw_text=raw_text,
        session_id=session_id,
        source_type=ResumeSourceType.TEXT.value,
    )
    if parse_immediately:
        return await parse_resume_record(session, resume)
    return resume


async def run_analysis(
    session: AsyncSession,
    *,
    resume: Resume,
    job: Job,
) -> AnalysisBundle:
    if resume.parse_status != ParseStatus.COMPLETED.value:
        resume = await parse_resume_record(session, resume)
    if job.parse_status != ParseStatus.COMPLETED.value:
        job = await parse_job_record(session, job)

    await ensure_resume_embeddings(session, resume)
    await ensure_job_embeddings(session, job)

    report = await create_match_report_record(session, resume, job)
    loaded_report = await get_match_report(session, report.id)
    if loaded_report is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to load created match report",
        )

    optimization = await optimize_resume_for_match(session, resume, job, loaded_report)
    loaded_optimization = await get_optimized_resume(session, optimization.id)
    if loaded_optimization is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to load created optimized resume",
        )

    return AnalysisBundle(
        resume=resume,
        job=job,
        match_report=loaded_report,
        optimization=loaded_optimization,
    )


async def ensure_resume_embeddings(session: AsyncSession, resume: Resume) -> None:
    if not resume.parsed_json:
        raise ValueError("Resume must be parsed before embeddings can be generated.")

    settings = get_settings()
    embedding_selection = get_embedding_client(settings)
    resume_extraction = ResumeExtraction.model_validate(resume.parsed_json)
    embeddings = prepare_resume_embeddings(
        resume.id,
        resume_extraction,
        embedding_selection.client,
        embedding_version="v1",
    )
    await replace_resume_embeddings(session, resume.id, embeddings)


async def ensure_job_embeddings(session: AsyncSession, job: Job) -> None:
    if not job.parsed_json:
        raise ValueError("Job must be parsed before embeddings can be generated.")

    settings = get_settings()
    embedding_selection = get_embedding_client(settings)
    job_extraction = JobExtraction.model_validate(job.parsed_json)
    embeddings = prepare_job_embeddings(
        job.id,
        job_extraction,
        embedding_selection.client,
        embedding_version="v1",
    )
    await replace_job_embeddings(session, job.id, embeddings)


def ingestion_http_error(exc: IngestionError) -> HTTPException:
    return HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))


def _resume_source_type(source_kind: str) -> str:
    if source_kind in {
        ResumeSourceType.PDF.value,
        ResumeSourceType.DOCX.value,
        ResumeSourceType.TEXT.value,
    }:
        return source_kind
    return ResumeSourceType.IMPORTED.value
