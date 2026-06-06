from __future__ import annotations

from typing import Any

import pytest

from app.ai.schemas import JobExtraction, JobRequirementItem, ResumeExtraction


def test_local_embedding_client_uses_configured_model_and_dimension(monkeypatch: Any) -> None:
    from app.core.config import Settings

    encode_calls: list[dict[str, Any]] = []

    class FakeModel:
        def encode(
            self,
            texts: list[str],
            *,
            convert_to_numpy: bool,
            normalize_embeddings: bool,
        ) -> list[list[float]]:
            encode_calls.append(
                {
                    "texts": texts,
                    "convert_to_numpy": convert_to_numpy,
                    "normalize_embeddings": normalize_embeddings,
                }
            )
            return [[0.1, 0.2, 0.3, 0.4] for _ in texts]

    monkeypatch.setattr(
        "app.ai.embeddings.local._load_sentence_transformer",
        lambda model_name: FakeModel(),
    )

    from app.ai.embeddings.local import LocalEmbeddingClient

    settings = Settings(
        EMBEDDING_PROVIDER="local",
        EMBEDDING_MODEL="sentence-transformers/all-MiniLM-L6-v2",
        EMBEDDING_DIMENSION=4,
    )
    client = LocalEmbeddingClient(settings)

    result = client.embed_texts(["python api", "fastapi services"])

    assert result.model_name == "sentence-transformers/all-MiniLM-L6-v2"
    assert result.dimension == 4
    assert result.provider == "local"
    assert result.vectors == [[0.1, 0.2, 0.3, 0.4], [0.1, 0.2, 0.3, 0.4]]
    assert encode_calls == [
        {
            "texts": ["python api", "fastapi services"],
            "convert_to_numpy": False,
            "normalize_embeddings": True,
        }
    ]


def test_local_embedding_client_rejects_dimension_mismatch(monkeypatch: Any) -> None:
    from app.core.config import Settings

    class FakeModel:
        def encode(
            self,
            texts: list[str],
            *,
            convert_to_numpy: bool,
            normalize_embeddings: bool,
        ) -> list[list[float]]:
            return [[0.1, 0.2] for _ in texts]

    monkeypatch.setattr(
        "app.ai.embeddings.local._load_sentence_transformer",
        lambda model_name: FakeModel(),
    )

    from app.ai.embeddings.local import LocalEmbeddingClient

    settings = Settings(
        EMBEDDING_PROVIDER="local",
        EMBEDDING_MODEL="mini",
        EMBEDDING_DIMENSION=4,
    )
    client = LocalEmbeddingClient(settings)

    with pytest.raises(ValueError):
        client.embed_texts(["python api"])


def test_build_resume_embedding_inputs_maps_summary_skills_and_experience() -> None:
    from app.ai.embeddings.indexing import build_resume_embedding_inputs

    resume = ResumeExtraction(
        summary="Backend engineer building Python APIs.",
        skills=["Python", "FastAPI"],
        experience_highlights=[
            "Built FastAPI services for ML inference.",
            "Optimized PostgreSQL queries.",
        ],
    )

    inputs = build_resume_embedding_inputs("resume-1", resume)

    assert [(item.section_type, item.section_id) for item in inputs] == [
        ("summary", "summary"),
        ("skill", "skill:0"),
        ("skill", "skill:1"),
        ("experience", "experience:0"),
        ("experience", "experience:1"),
    ]
    assert inputs[0].text == "Backend engineer building Python APIs."
    assert inputs[1].text == "Python"
    assert inputs[4].text == "Optimized PostgreSQL queries."


def test_build_job_embedding_inputs_maps_skills_requirements_and_responsibilities() -> None:
    from app.ai.embeddings.indexing import build_job_embedding_inputs

    job = JobExtraction(
        title="ML Platform Engineer",
        responsibilities=["Build and operate model-serving APIs."],
        required_skills=["Python"],
        preferred_skills=["FastAPI"],
        requirements=[
            JobRequirementItem(
                requirement="Experience building APIs for ML inference.",
                requirement_type="required",
            )
        ],
    )

    inputs = build_job_embedding_inputs("job-1", job)

    assert [(item.requirement_type, item.requirement_id) for item in inputs] == [
        ("required_skill", "required_skill:0"),
        ("preferred_skill", "preferred_skill:0"),
        ("requirement", "req:1"),
        ("responsibility", "responsibility:0"),
    ]
    assert inputs[0].text == "Python"
    assert inputs[2].text == "Experience building APIs for ML inference."
    assert inputs[3].text == "Build and operate model-serving APIs."


def test_build_embedding_inputs_skips_empty_fields() -> None:
    from app.ai.embeddings.indexing import build_job_embedding_inputs, build_resume_embedding_inputs

    resume_inputs = build_resume_embedding_inputs(
        "resume-2",
        ResumeExtraction(summary=None, skills=[], experience_highlights=[]),
    )
    job_inputs = build_job_embedding_inputs(
        "job-2",
        JobExtraction(
            required_skills=[],
            preferred_skills=[],
            responsibilities=[],
            requirements=[],
        ),
    )

    assert resume_inputs == []
    assert job_inputs == []

    from app.ai.embeddings.indexing import prepare_job_embeddings, prepare_resume_embeddings

    class NoCallEmbeddingClient:
        provider = "local"
        model_name = "mini"
        dimension = 4

        def embed_texts(self, texts: list[str]) -> Any:
            raise AssertionError("embed_texts should not be called for empty inputs")

    assert prepare_resume_embeddings(
        "resume-2",
        ResumeExtraction(summary=None, skills=[], experience_highlights=[]),
        NoCallEmbeddingClient(),
        embedding_version="v1",
    ) == []
    assert prepare_job_embeddings(
        "job-2",
        JobExtraction(
            required_skills=[],
            preferred_skills=[],
            responsibilities=[],
            requirements=[],
        ),
        NoCallEmbeddingClient(),
        embedding_version="v1",
    ) == []


def test_deterministic_embedding_client_is_normalized_and_configurable() -> None:
    from app.ai.embeddings.deterministic import DeterministicEmbeddingClient

    client = DeterministicEmbeddingClient(
        dimension=8,
        provider="fallback-test",
        fallback_reason="missing runtime",
    )

    result = client.embed_texts(["Python APIs", ""])

    assert result.provider == "fallback-test"
    assert result.model_name == "deterministic-token-hash"
    assert result.dimension == 8
    assert result.metadata == {
        "runtime": "deterministic",
        "fallback_reason": "missing runtime",
    }
    assert len(result.vectors) == 2
    assert len(result.vectors[0]) == 8
    assert round(sum(value * value for value in result.vectors[0]), 6) == 1.0
    assert result.vectors[1] == [0.0] * 8


def test_embedding_factory_falls_back_when_local_runtime_unavailable(monkeypatch: Any) -> None:
    from app.ai.embeddings.deterministic import DeterministicEmbeddingClient
    from app.ai.embeddings.factory import get_embedding_client
    from app.core.config import Settings

    def raise_missing_runtime(model_name: str) -> Any:
        raise ImportError(f"missing {model_name}")

    monkeypatch.setattr(
        "app.ai.embeddings.local._load_sentence_transformer",
        raise_missing_runtime,
    )

    settings = Settings(
        EMBEDDING_PROVIDER="local",
        EMBEDDING_MODEL="mini",
        EMBEDDING_DIMENSION=4,
    )
    selection = get_embedding_client(settings)

    assert isinstance(selection.client, DeterministicEmbeddingClient)
    assert selection.warning is not None
    assert "Local embedding runtime unavailable" in selection.warning
    assert selection.client.dimension == 4
