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


def test_cohere_embedding_client_posts_to_v2_embed(monkeypatch: Any) -> None:
    from app.ai.embeddings.cohere import CohereEmbeddingClient
    from app.core.config import Settings

    calls: list[dict[str, Any]] = []

    class FakeResponse:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict[str, Any]:
            return {"embeddings": {"float": [[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]]}}

    class FakeClient:
        def __init__(self, *, timeout: float) -> None:
            calls.append({"timeout": timeout})

        def __enter__(self) -> FakeClient:
            return self

        def __exit__(self, exc_type: object, exc: object, tb: object) -> None:
            return None

        def post(
            self,
            url: str,
            *,
            json: dict[str, Any],
            headers: dict[str, str],
        ) -> FakeResponse:
            calls.append({"url": url, "json": json, "headers": headers})
            return FakeResponse()

    monkeypatch.setattr("app.ai.embeddings.cohere.httpx.Client", FakeClient)

    settings = Settings(
        EMBEDDING_PROVIDER="cohere",
        EMBEDDING_MODEL="embed-english-v3.0",
        EMBEDDING_DIMENSION=3,
        COHERE_API_KEY="test-key",
        EMBEDDING_REQUEST_TIMEOUT_SECONDS=12,
    )
    client = CohereEmbeddingClient(settings)

    result = client.embed_texts(["python api", "fastapi services"])

    assert result.provider == "cohere"
    assert result.model_name == "embed-english-v3.0"
    assert result.dimension == 3
    assert result.vectors == [[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]]
    assert result.metadata["runtime"] == "cohere_api"
    assert calls[0] == {"timeout": 12}
    assert calls[1]["url"] == "https://api.cohere.com/v2/embed"
    assert calls[1]["json"] == {
        "texts": ["python api", "fastapi services"],
        "model": "embed-english-v3.0",
        "input_type": "search_document",
        "embedding_types": ["float"],
    }
    assert calls[1]["headers"]["Authorization"] == "Bearer test-key"


def test_embedding_factory_selects_cohere(monkeypatch: Any) -> None:
    from app.ai.embeddings.cohere import CohereEmbeddingClient
    from app.ai.embeddings.factory import get_embedding_client
    from app.core.config import Settings

    monkeypatch.setattr(CohereEmbeddingClient, "__init__", lambda self, settings: None)

    settings = Settings(
        EMBEDDING_PROVIDER="cohere",
        EMBEDDING_MODEL="embed-english-v3.0",
        EMBEDDING_DIMENSION=1024,
        COHERE_API_KEY="test-key",
    )
    selection = get_embedding_client(settings)

    assert isinstance(selection.client, CohereEmbeddingClient)
    assert selection.warning is None


def test_jina_embedding_client_posts_to_embeddings_endpoint(monkeypatch: Any) -> None:
    from app.ai.embeddings.jina import JinaEmbeddingClient
    from app.core.config import Settings

    calls: list[dict[str, Any]] = []

    class FakeResponse:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict[str, Any]:
            return {
                "data": [
                    {"index": 0, "embedding": [0.1, 0.2, 0.3]},
                    {"index": 1, "embedding": [0.4, 0.5, 0.6]},
                ]
            }

    class FakeClient:
        def __init__(self, *, timeout: float) -> None:
            calls.append({"timeout": timeout})

        def __enter__(self) -> FakeClient:
            return self

        def __exit__(self, exc_type: object, exc: object, tb: object) -> None:
            return None

        def post(
            self,
            url: str,
            *,
            json: dict[str, Any],
            headers: dict[str, str],
        ) -> FakeResponse:
            calls.append({"url": url, "json": json, "headers": headers})
            return FakeResponse()

    monkeypatch.setattr("app.ai.embeddings.jina.httpx.Client", FakeClient)

    settings = Settings(
        EMBEDDING_PROVIDER="jina",
        EMBEDDING_MODEL="jina-embeddings-v3",
        EMBEDDING_DIMENSION=3,
        JINA_API_KEY="test-key",
        EMBEDDING_REQUEST_TIMEOUT_SECONDS=12,
    )
    client = JinaEmbeddingClient(settings)

    result = client.embed_texts(["python api", "fastapi services"])

    assert result.provider == "jina"
    assert result.model_name == "jina-embeddings-v3"
    assert result.dimension == 3
    assert result.vectors == [[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]]
    assert result.metadata["runtime"] == "jina_api"
    assert calls[0] == {"timeout": 12}
    assert calls[1]["url"] == "https://api.jina.ai/v1/embeddings"
    assert calls[1]["json"] == {
        "model": "jina-embeddings-v3",
        "input": ["python api", "fastapi services"],
    }
    assert calls[1]["headers"]["Authorization"] == "Bearer test-key"


def test_embedding_factory_selects_jina(monkeypatch: Any) -> None:
    from app.ai.embeddings.factory import get_embedding_client
    from app.ai.embeddings.jina import JinaEmbeddingClient
    from app.core.config import Settings

    monkeypatch.setattr(JinaEmbeddingClient, "__init__", lambda self, settings: None)

    settings = Settings(
        EMBEDDING_PROVIDER="jina",
        EMBEDDING_MODEL="jina-embeddings-v3",
        EMBEDDING_DIMENSION=1024,
        JINA_API_KEY="test-key",
    )
    selection = get_embedding_client(settings)

    assert isinstance(selection.client, JinaEmbeddingClient)
    assert selection.warning is None
