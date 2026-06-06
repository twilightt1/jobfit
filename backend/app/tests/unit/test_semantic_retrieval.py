from __future__ import annotations

from app.db.models.embedding import JobEmbedding, ResumeEmbedding


def test_find_best_semantic_skill_matches_returns_best_resume_hit() -> None:
    from app.ai.embeddings.semantic import find_best_semantic_skill_matches

    resume_embeddings = [
        ResumeEmbedding(
            resume_id="resume-1",
            section_type="experience",
            section_id="experience:0",
            text="Built and operated REST APIs for ML model serving.",
            embedding=[1.0, 0.0, 0.0, 0.0],
            embedding_model="mini",
            embedding_version="v1",
            dimension=4,
            metadata_json={"provider": "local"},
        ),
        ResumeEmbedding(
            resume_id="resume-1",
            section_type="experience",
            section_id="experience:1",
            text="Optimized PostgreSQL queries.",
            embedding=[0.0, 1.0, 0.0, 0.0],
            embedding_model="mini",
            embedding_version="v1",
            dimension=4,
            metadata_json={"provider": "local"},
        ),
    ]
    job_embeddings = [
        JobEmbedding(
            job_id="job-1",
            requirement_type="required_skill",
            requirement_id="required_skill:0",
            text="FastAPI",
            embedding=[0.9, 0.1, 0.0, 0.0],
            embedding_model="mini",
            embedding_version="v1",
            dimension=4,
            metadata_json={"provider": "local"},
        )
    ]

    matches = find_best_semantic_skill_matches(
        resume_embeddings,
        job_embeddings,
        score_threshold=0.8,
    )

    assert set(matches.keys()) == {"fastapi"}
    assert matches["fastapi"]["text"] == "Built and operated REST APIs for ML model serving."
    assert matches["fastapi"]["match_type"] == "semantic"
    assert matches["fastapi"]["score"] > 0.8
    assert matches["fastapi"]["resume_section_id"] == "experience:0"
    assert matches["fastapi"]["resume_section_type"] == "experience"
    assert matches["fastapi"]["job_requirement_id"] == "required_skill:0"
    assert matches["fastapi"]["embedding_model"] == "mini"
    assert matches["fastapi"]["embedding_provider"] == "local"
    assert matches["fastapi"]["score_threshold"] == 0.8


def test_find_best_semantic_requirement_matches_uses_requirement_ids() -> None:
    from app.ai.embeddings.semantic import find_best_semantic_requirement_matches

    resume_embeddings = [
        ResumeEmbedding(
            resume_id="resume-1",
            section_type="experience",
            section_id="experience:0",
            text="Built and operated REST APIs for ML model serving.",
            embedding=[1.0, 0.0, 0.0, 0.0],
            embedding_model="mini",
            embedding_version="v1",
            dimension=4,
            metadata_json={"provider": "local"},
        )
    ]
    job_embeddings = [
        JobEmbedding(
            job_id="job-1",
            requirement_type="requirement",
            requirement_id="req:1",
            text="Experience building FastAPI services for model inference.",
            embedding=[0.95, 0.05, 0.0, 0.0],
            embedding_model="mini",
            embedding_version="v1",
            dimension=4,
            metadata_json={"provider": "local"},
        )
    ]

    matches = find_best_semantic_requirement_matches(
        resume_embeddings,
        job_embeddings,
        score_threshold=0.8,
    )

    assert set(matches.keys()) == {"req:1"}
    assert matches["req:1"]["text"] == "Built and operated REST APIs for ML model serving."
    assert matches["req:1"]["match_type"] == "semantic"
    assert matches["req:1"]["score"] > 0.8
    assert matches["req:1"]["resume_section_id"] == "experience:0"
    assert matches["req:1"]["job_requirement_id"] == "req:1"
    assert matches["req:1"]["job_requirement_type"] == "requirement"
    assert matches["req:1"]["embedding_model"] == "mini"
    assert matches["req:1"]["embedding_provider"] == "local"
    assert matches["req:1"]["score_threshold"] == 0.8


def test_semantic_retrieval_respects_threshold() -> None:
    from app.ai.embeddings.semantic import find_best_semantic_skill_matches

    resume_embeddings = [
        ResumeEmbedding(
            resume_id="resume-1",
            section_type="experience",
            section_id="experience:0",
            text="Built REST APIs.",
            embedding=[1.0, 0.0, 0.0, 0.0],
            embedding_model="mini",
            embedding_version="v1",
            dimension=4,
            metadata_json={"provider": "local"},
        )
    ]
    job_embeddings = [
        JobEmbedding(
            job_id="job-1",
            requirement_type="required_skill",
            requirement_id="required_skill:0",
            text="FastAPI",
            embedding=[0.0, 1.0, 0.0, 0.0],
            embedding_model="mini",
            embedding_version="v1",
            dimension=4,
            metadata_json={"provider": "local"},
        )
    ]

    matches = find_best_semantic_skill_matches(
        resume_embeddings,
        job_embeddings,
        score_threshold=0.95,
    )

    assert matches == {}
