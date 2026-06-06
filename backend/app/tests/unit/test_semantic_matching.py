from __future__ import annotations

from app.ai.schemas import JobExtraction, JobRequirementItem, ResumeExtraction
from app.ai.scoring.match_engine import DeterministicMatchEngine


def test_semantic_skill_match_can_cover_lexical_miss() -> None:
    engine = DeterministicMatchEngine()
    resume = ResumeExtraction(
        skills=[],
        experience_highlights=["Built and operated REST APIs for ML model serving."],
        total_years_experience=4,
    )
    job = JobExtraction(
        required_skills=["FastAPI"],
        requirements=[],
        seniority="mid",
    )

    semantic_matches = {
        "fastapi": {
            "text": "Built and operated REST APIs for ML model serving.",
            "score": 0.91,
            "match_type": "semantic",
            "resume_section_id": "experience:0",
            "resume_section_type": "experience",
            "embedding_model": "mini",
        }
    }
    result = engine.compute(
        resume,
        job,
        semantic_skill_matches=semantic_matches,
    )

    assert result.breakdown["skills"]["matched"] == ["fastapi"]
    assert result.breakdown["skills"]["missing"] == []
    assert any(item.match_type == "semantic" for item in result.evidence)
    semantic_evidence = next(item for item in result.evidence if item.match_type == "semantic")
    assert semantic_evidence.similarity_score == 0.91
    assert semantic_evidence.metadata_json["semantic"]["resume_section_id"] == "experience:0"
    assert semantic_evidence.metadata_json["semantic"]["embedding_model"] == "mini"


def test_semantic_requirement_match_can_upgrade_missing_requirement() -> None:
    engine = DeterministicMatchEngine()
    resume = ResumeExtraction(
        skills=["Python"],
        experience_highlights=["Delivered production-grade prediction endpoints at scale."],
        total_years_experience=4,
    )
    job = JobExtraction(
        required_skills=["Python"],
        requirements=[
            JobRequirementItem(
                requirement="Experience building FastAPI services for model inference.",
                requirement_type="required",
            )
        ],
        seniority="mid",
    )

    semantic_requirement_matches = {
        "req:1": {
            "text": "Delivered production-grade prediction endpoints at scale.",
            "score": 0.88,
            "match_type": "semantic",
            "resume_section_id": "experience:0",
            "resume_section_type": "experience",
            "job_requirement_id": "req:1",
            "job_requirement_type": "requirement",
            "embedding_model": "mini",
            "embedding_provider": "local",
            "score_threshold": 0.8,
        }
    }
    result = engine.compute(
        resume,
        job,
        semantic_requirement_matches=semantic_requirement_matches,
    )

    requirement_evidence = [item for item in result.evidence if item.requirement_id == "req:1"]
    assert len(requirement_evidence) == 1
    assert requirement_evidence[0].match_type == "semantic"
    assert requirement_evidence[0].similarity_score == 0.88
    assert requirement_evidence[0].resume_evidence_text == (
        "Delivered production-grade prediction endpoints at scale."
    )
    assert result.breakdown["requirements"]["score"] > 0
    assert requirement_evidence[0].resume_section_id == "experience:0"
    assert requirement_evidence[0].metadata_json["semantic"] == {
        "resume_section_id": "experience:0",
        "resume_section_type": "experience",
        "job_requirement_id": "req:1",
        "job_requirement_type": "requirement",
        "embedding_model": "mini",
        "embedding_provider": "local",
        "score_threshold": 0.8,
    }


def test_semantic_requirement_match_marks_hybrid_when_lexical_and_semantic_support_exist() -> None:
    engine = DeterministicMatchEngine()
    resume = ResumeExtraction(
        skills=["Python"],
        experience_highlights=["Built and operated REST APIs for ML model serving."],
        total_years_experience=4,
    )
    job = JobExtraction(
        required_skills=["Python"],
        requirements=[
            JobRequirementItem(
                requirement="Experience building FastAPI services for model inference.",
                requirement_type="required",
            )
        ],
        seniority="mid",
    )

    result = engine.compute(
        resume,
        job,
        semantic_requirement_matches={
            "req:1": {
                "text": "Built and operated REST APIs for ML model serving.",
                "score": 0.88,
                "match_type": "semantic",
                "resume_section_id": "experience:0",
                "resume_section_type": "experience",
            }
        },
    )

    requirement_evidence = [item for item in result.evidence if item.requirement_id == "req:1"]
    assert len(requirement_evidence) == 1
    assert requirement_evidence[0].match_type == "hybrid"
    assert requirement_evidence[0].similarity_score == 0.88


def test_semantic_matches_preserve_explainable_output_shape() -> None:
    engine = DeterministicMatchEngine()
    resume = ResumeExtraction(
        skills=[],
        experience_highlights=["Built and operated REST APIs for ML model serving."],
        languages=["English"],
        total_years_experience=4,
    )
    job = JobExtraction(
        required_skills=["FastAPI"],
        requirements=[
            JobRequirementItem(
                requirement="Experience building FastAPI services for model inference.",
                requirement_type="required",
            )
        ],
        seniority="mid",
    )

    result = engine.compute(
        resume,
        job,
        semantic_skill_matches={
            "fastapi": {
                "text": "Delivered production-grade prediction endpoints at scale.",
                "score": 0.91,
                "match_type": "semantic",
            }
        },
        semantic_requirement_matches={
            "req:1": {
                "text": "Delivered production-grade prediction endpoints at scale.",
                "score": 0.88,
                "match_type": "semantic",
            }
        },
    )

    assert set(result.breakdown.keys()) == {"skills", "requirements", "experience", "languages"}
    assert "keywords_matched" in result.ats_report
    assert "keywords_missing" in result.ats_report
    assert isinstance(result.evidence, list)
    assert result.overall_score >= 0
