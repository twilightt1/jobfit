from __future__ import annotations

from app.ai.clients.local_resume_optimizer import LocalResumeOptimizer
from app.ai.guardrails.truth_guard import LocalTruthGuard
from app.ai.schemas import JobExtraction, JobRequirementItem, ResumeExtraction
from app.ai.schemas.optimization import RewriteSuggestionDraft


def test_local_resume_optimizer_generates_grounded_suggestions() -> None:
    resume = ResumeExtraction(
        candidate_name="Jane Doe",
        summary="Backend engineer building Python APIs",
        skills=["Python", "FastAPI"],
        experience_highlights=["Built FastAPI services for ML inference."],
    )
    job = JobExtraction(
        title="ML Platform Engineer",
        required_skills=["Python", "FastAPI", "PostgreSQL"],
        requirements=[
            JobRequirementItem(
                requirement="Build FastAPI services for model inference.",
                requirement_type="required",
            )
        ],
    )
    match_report = {
        "overall_score": 72,
        "breakdown_json": {"skills": {"missing": ["FastAPI"]}},
    }

    draft = LocalResumeOptimizer().optimize(resume, job, match_report)

    assert draft.projected_score > 72
    assert draft.suggestions
    assert draft.suggestions[0].section_type == "summary"
    assert "fastapi" in draft.suggestions[0].keywords_added


def test_local_truth_guard_marks_supported_rewrite_safe() -> None:
    resume = ResumeExtraction(
        summary="Backend engineer building Python APIs",
        skills=["Python", "FastAPI"],
        experience_highlights=["Built FastAPI services for ML inference."],
    )
    suggestion = RewriteSuggestionDraft(
        section_type="experience",
        original_text="Built FastAPI services for ML inference.",
        suggested_text="Built FastAPI services for ML inference with Python APIs.",
        keywords_added=["fastapi", "python"],
        reason="Rephrase verified backend API evidence.",
        estimated_score_lift=4,
    )

    decision = LocalTruthGuard().evaluate(suggestion, resume)

    assert decision.truth_status == "safe"
    assert decision.new_claims == []


def test_local_truth_guard_flags_unsupported_claims() -> None:
    resume = ResumeExtraction(
        summary="Backend engineer building Python APIs",
        skills=["Python"],
        experience_highlights=["Built internal APIs."],
    )
    suggestion = RewriteSuggestionDraft(
        section_type="experience",
        original_text="Built internal APIs.",
        suggested_text="Led a team that increased revenue by millions using Kubernetes.",
        keywords_added=["leadership", "kubernetes"],
        reason="Add business impact.",
        estimated_score_lift=10,
    )

    decision = LocalTruthGuard().evaluate(suggestion, resume)

    assert decision.truth_status == "unsupported"
    assert "increased" in decision.new_claims or "led" in decision.new_claims
