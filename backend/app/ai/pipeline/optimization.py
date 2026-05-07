from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.clients.local_resume_optimizer import LocalResumeOptimizer
from app.ai.guardrails.truth_guard import LocalTruthGuard
from app.ai.prompt_loader import load_prompt_template
from app.ai.schemas import JobExtraction, ResumeExtraction
from app.ai.schemas.optimization import OptimizedResumeDraft, RewriteSuggestionDraft
from app.ai.schemas.truth_guard import TruthGuardDecision
from app.db.models.ai_run import AIOutput, AIRun
from app.db.models.enums import AIProvider, AIRunStatus, AITaskType, ValidationStatus
from app.db.models.job import Job
from app.db.models.match_report import MatchReport
from app.db.models.optimization import OptimizedResume, RewriteSuggestion
from app.db.models.resume import Resume

OPTIMIZER_PROMPT_NAME = "resume_optimizer.v1.md"
TRUTH_GUARD_PROMPT_NAME = "truth_guard.v1.md"
PROMPT_VERSION = "v1"
SCHEMA_VERSION = "v1"


@dataclass(slots=True)
class GuardedSuggestion:
    suggestion: RewriteSuggestionDraft
    decision: TruthGuardDecision
    truth_run_id: str


async def optimize_resume_for_match(
    session: AsyncSession,
    resume: Resume,
    job: Job,
    match_report: MatchReport,
) -> OptimizedResume:
    resume_extraction = ResumeExtraction.model_validate(resume.parsed_json or {})
    job_extraction = JobExtraction.model_validate(job.parsed_json or {})
    match_report_json = _match_report_to_json(match_report)

    optimizer = LocalResumeOptimizer()
    optimizer_prompt = _build_optimizer_prompt(resume_extraction, job_extraction, match_report_json)
    optimizer_run = _create_ai_run(
        session_id=resume.session_id or job.session_id,
        task_type=AITaskType.RESUME_OPTIMIZE.value,
        model_name=optimizer.model_name,
        prompt_name=OPTIMIZER_PROMPT_NAME,
        input_text=optimizer_prompt,
        input_summary={
            "resume_id": resume.id,
            "job_id": job.id,
            "match_report_id": match_report.id,
        },
    )
    session.add(optimizer_run)
    await session.flush()

    try:
        draft = optimizer.optimize(resume_extraction, job_extraction, match_report_json)
        draft_json = _model_dump(draft)
        _complete_ai_run(optimizer_run, optimizer_prompt, draft_json)
        session.add(
            AIOutput(
                ai_run=optimizer_run,
                output_json=draft_json,
                validation_status=ValidationStatus.VALID.value,
                validation_errors=None,
                repair_attempted=False,
                metadata_json={"suggestion_count": len(draft.suggestions)},
            )
        )

        truth_guard = LocalTruthGuard()
        guarded_suggestions = await _guard_suggestions(
            session,
            truth_guard,
            draft.suggestions,
            resume_extraction,
            resume,
            job,
            match_report,
        )

        optimized_resume = _build_optimized_resume(
            resume,
            job,
            match_report,
            draft,
            guarded_suggestions,
            optimizer_run.id,
        )
        session.add(optimized_resume)
        await session.flush()

        for guarded in guarded_suggestions:
            session.add(_build_rewrite_suggestion(optimized_resume.id, guarded))

        await session.commit()
        await session.refresh(optimized_resume)
        return optimized_resume
    except Exception as exc:
        optimizer_run.status = AIRunStatus.FAILED.value
        optimizer_run.validation_status = ValidationStatus.INVALID.value
        optimizer_run.error_type = exc.__class__.__name__
        optimizer_run.error_message = str(exc)
        optimizer_run.completed_at = datetime.now(UTC)
        await session.commit()
        raise


async def _guard_suggestions(
    session: AsyncSession,
    truth_guard: LocalTruthGuard,
    suggestions: list[RewriteSuggestionDraft],
    resume_extraction: ResumeExtraction,
    resume: Resume,
    job: Job,
    match_report: MatchReport,
) -> list[GuardedSuggestion]:
    guarded: list[GuardedSuggestion] = []
    for index, suggestion in enumerate(suggestions, start=1):
        guard_prompt = _build_truth_guard_prompt(suggestion, resume_extraction)
        guard_run = _create_ai_run(
            session_id=resume.session_id or job.session_id,
            task_type=AITaskType.TRUTH_GUARD.value,
            model_name=truth_guard.model_name,
            prompt_name=TRUTH_GUARD_PROMPT_NAME,
            input_text=guard_prompt,
            input_summary={
                "resume_id": resume.id,
                "job_id": job.id,
                "match_report_id": match_report.id,
                "suggestion_index": index,
            },
        )
        session.add(guard_run)
        await session.flush()

        decision = truth_guard.evaluate(suggestion, resume_extraction)
        output_json = _model_dump(decision)
        _complete_ai_run(guard_run, guard_prompt, output_json)
        session.add(
            AIOutput(
                ai_run=guard_run,
                output_json=output_json,
                validation_status=ValidationStatus.VALID.value,
                validation_errors=None,
                repair_attempted=False,
                metadata_json={"section_type": suggestion.section_type},
            )
        )
        guarded.append(
            GuardedSuggestion(
                suggestion=suggestion,
                decision=decision,
                truth_run_id=guard_run.id,
            )
        )
    return guarded


def _build_optimized_resume(
    resume: Resume,
    job: Job,
    match_report: MatchReport,
    draft: OptimizedResumeDraft,
    guarded_suggestions: list[GuardedSuggestion],
    optimizer_run_id: str,
) -> OptimizedResume:
    content_json: dict[str, Any] = {
        "summary": draft.summary,
        "skills": draft.skills,
        "experience_highlights": draft.experience_highlights,
        "source_resume_id": resume.id,
        "job_id": job.id,
    }
    return OptimizedResume(
        user_id=resume.user_id or job.user_id,
        session_id=resume.session_id or job.session_id,
        resume_id=resume.id,
        job_id=job.id,
        match_report_id=match_report.id,
        version_name=draft.version_name,
        content_json=content_json,
        score_before=match_report.overall_score,
        score_after=draft.projected_score,
        status=_optimization_status(guarded_suggestions),
        generated_by_ai_run_id=optimizer_run_id,
    )


def _build_rewrite_suggestion(
    optimized_resume_id: str,
    guarded: GuardedSuggestion,
) -> RewriteSuggestion:
    suggestion = guarded.suggestion
    decision = guarded.decision
    return RewriteSuggestion(
        optimized_resume_id=optimized_resume_id,
        section_type=suggestion.section_type,
        target_location=suggestion.target_location,
        original_text=suggestion.original_text,
        suggested_text=suggestion.suggested_text,
        user_edited_text=None,
        targeted_requirements=suggestion.targeted_requirements,
        keywords_added=suggestion.keywords_added,
        reason=suggestion.reason,
        estimated_score_lift=suggestion.estimated_score_lift,
        truth_status=decision.truth_status,
        new_claims_json=decision.new_claims,
        guardrail_reason=decision.reason,
        decision="pending",
        accepted_by_user=False,
        generated_by_ai_run_id=guarded.truth_run_id,
    )


def _optimization_status(guarded_suggestions: list[GuardedSuggestion]) -> str:
    statuses = [guarded.decision.truth_status for guarded in guarded_suggestions]
    if any(status == "unsupported" for status in statuses):
        return "needs_review"
    if any(status == "needs_review" for status in statuses):
        return "review_recommended"
    return "draft"


def _build_optimizer_prompt(
    resume: ResumeExtraction,
    job: JobExtraction,
    match_report: dict[str, Any],
) -> str:
    prompt_template = load_prompt_template(OPTIMIZER_PROMPT_NAME)
    return (
        prompt_template.replace("<<<RESUME_JSON>>>", str(_model_dump(resume)))
        .replace("<<<JOB_JSON>>>", str(_model_dump(job)))
        .replace("<<<MATCH_ANALYSIS_JSON>>>", str(match_report))
    )


def _build_truth_guard_prompt(
    suggestion: RewriteSuggestionDraft,
    resume: ResumeExtraction,
) -> str:
    prompt_template = load_prompt_template(TRUTH_GUARD_PROMPT_NAME)
    return prompt_template.replace("<<<RESUME_JSON>>>", str(_model_dump(resume))).replace(
        "<<<SUGGESTION_JSON>>>",
        str(_model_dump(suggestion)),
    )


def _create_ai_run(
    *,
    session_id: str | None,
    task_type: str,
    model_name: str,
    prompt_name: str,
    input_text: str,
    input_summary: dict[str, Any],
) -> AIRun:
    return AIRun(
        session_id=session_id,
        task_type=task_type,
        status=AIRunStatus.RUNNING.value,
        provider=AIProvider.LOCAL.value,
        model_name=model_name,
        prompt_name=prompt_name,
        prompt_version=PROMPT_VERSION,
        schema_version=SCHEMA_VERSION,
        temperature=0.0,
        input_hash=hashlib.sha256(input_text.encode("utf-8")).hexdigest(),
        input_summary_json=input_summary,
        validation_status=ValidationStatus.NOT_VALIDATED.value,
        started_at=datetime.now(UTC),
    )


def _complete_ai_run(ai_run: AIRun, input_text: str, output_json: dict[str, Any]) -> None:
    ai_run.status = AIRunStatus.SUCCESS.value
    ai_run.validation_status = ValidationStatus.VALID.value
    ai_run.completed_at = datetime.now(UTC)
    ai_run.input_token_count = len(input_text.split())
    ai_run.output_token_count = max(1, len(str(output_json).split()))
    ai_run.total_token_count = ai_run.input_token_count + ai_run.output_token_count
    ai_run.latency_ms = 1


def _match_report_to_json(match_report: MatchReport) -> dict[str, Any]:
    return {
        "id": match_report.id,
        "overall_score": match_report.overall_score,
        "analysis_confidence": match_report.analysis_confidence,
        "breakdown_json": match_report.breakdown_json,
        "strengths_json": match_report.strengths_json,
        "gaps_json": match_report.gaps_json,
        "recommendations_json": match_report.recommendations_json,
        "ats_report_json": match_report.ats_report_json,
        "explanation_json": match_report.explanation_json,
    }


def _model_dump(model: Any) -> dict[str, Any]:
    return dict(model.model_dump(mode="json"))
