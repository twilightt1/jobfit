from __future__ import annotations

from typing import Any, cast

from app.ai.schemas import JobExtraction, JobRequirementItem, ResumeExtraction
from app.db.models.embedding import JobEmbedding, ResumeEmbedding


class FakeEmbeddingClient:
    provider = "local"
    model_name = "mini"
    dimension = 4

    def __init__(self, vectors: list[list[float]]) -> None:
        self._vectors = vectors
        self.calls: list[list[str]] = []

    def embed_texts(self, texts: list[str]) -> Any:
        from app.ai.embeddings.base import EmbeddingBatchResult

        self.calls.append(texts)
        return EmbeddingBatchResult(
            provider=self.provider,
            model_name=self.model_name,
            dimension=self.dimension,
            vectors=self._vectors,
        )


class FakeSession:
    def __init__(self) -> None:
        self.resume_rows: list[ResumeEmbedding] = []
        self.job_rows: list[JobEmbedding] = []
        self.commit_count = 0

    async def execute(self, statement: Any) -> None:
        table_name = statement.table.name
        if table_name == "resume_embeddings":
            self.resume_rows = []
        if table_name == "job_embeddings":
            self.job_rows = []

    def add_all(self, rows: list[Any]) -> None:
        if not rows:
            return
        first_row = rows[0]
        if isinstance(first_row, ResumeEmbedding):
            self.resume_rows = list(rows)
        if isinstance(first_row, JobEmbedding):
            self.job_rows = list(rows)

    async def commit(self) -> None:
        self.commit_count += 1


def test_prepare_resume_embeddings_uses_embedding_client_vectors() -> None:
    from app.ai.embeddings.indexing import prepare_resume_embeddings

    client = FakeEmbeddingClient(
        vectors=[
            [0.1, 0.2, 0.3, 0.4],
            [0.2, 0.3, 0.4, 0.5],
            [0.3, 0.4, 0.5, 0.6],
            [0.4, 0.5, 0.6, 0.7],
        ]
    )

    embeddings = prepare_resume_embeddings(
        "resume-1",
        ResumeExtraction(
            summary="Backend engineer building Python APIs.",
            skills=["Python", "FastAPI"],
            experience_highlights=["Built FastAPI services for ML inference."],
        ),
        client,
        embedding_version="v1",
    )

    assert client.calls == [[
        "Backend engineer building Python APIs.",
        "Python",
        "FastAPI",
        "Built FastAPI services for ML inference.",
    ]]
    assert [item.section_type for item in embeddings] == [
        "summary",
        "skill",
        "skill",
        "experience",
    ]
    assert embeddings[0].embedding == [0.1, 0.2, 0.3, 0.4]
    assert embeddings[0].embedding_model == "mini"
    assert embeddings[0].dimension == 4
    assert embeddings[0].metadata_json == {"provider": "local"}


def test_prepare_job_embeddings_uses_embedding_client_vectors() -> None:
    from app.ai.embeddings.indexing import prepare_job_embeddings

    client = FakeEmbeddingClient(
        vectors=[
            [0.1, 0.1, 0.1, 0.1],
            [0.2, 0.2, 0.2, 0.2],
            [0.3, 0.3, 0.3, 0.3],
            [0.4, 0.4, 0.4, 0.4],
        ]
    )

    embeddings = prepare_job_embeddings(
        "job-1",
        JobExtraction(
            required_skills=["Python"],
            preferred_skills=["FastAPI"],
            responsibilities=["Build and operate model-serving APIs."],
            requirements=[
                JobRequirementItem(
                    requirement="Experience building APIs for ML inference.",
                    requirement_type="required",
                )
            ],
        ),
        client,
        embedding_version="v1",
    )

    assert client.calls == [[
        "Python",
        "FastAPI",
        "Experience building APIs for ML inference.",
        "Build and operate model-serving APIs.",
    ]]
    assert [item.requirement_type for item in embeddings] == [
        "required_skill",
        "preferred_skill",
        "requirement",
        "responsibility",
    ]
    assert [item.requirement_id for item in embeddings] == [
        "required_skill:0",
        "preferred_skill:0",
        "req:1",
        "responsibility:0",
    ]
    assert embeddings[-1].embedding == [0.4, 0.4, 0.4, 0.4]
    assert embeddings[-1].metadata_json == {"provider": "local"}


async def test_replace_resume_embeddings_is_idempotent() -> None:
    from app.ai.embeddings.indexing import replace_resume_embeddings

    session = cast(Any, FakeSession())
    first = [
        ResumeEmbedding(
            resume_id="resume-1",
            section_type="skill",
            section_id="skill:0",
            text="Python",
            embedding=[0.1, 0.2, 0.3, 0.4],
            embedding_model="mini",
            embedding_version="v1",
            dimension=4,
            metadata_json={"provider": "local"},
        )
    ]
    second = [
        ResumeEmbedding(
            resume_id="resume-1",
            section_type="skill",
            section_id="skill:1",
            text="FastAPI",
            embedding=[0.2, 0.3, 0.4, 0.5],
            embedding_model="mini",
            embedding_version="v1",
            dimension=4,
            metadata_json={"provider": "local"},
        )
    ]

    await replace_resume_embeddings(session, "resume-1", first)
    await replace_resume_embeddings(session, "resume-1", second)

    assert len(session.resume_rows) == 1
    assert session.resume_rows[0].text == "FastAPI"
    assert session.commit_count == 2


async def test_replace_job_embeddings_is_idempotent() -> None:
    from app.ai.embeddings.indexing import replace_job_embeddings

    session = cast(Any, FakeSession())
    first = [
        JobEmbedding(
            job_id="job-1",
            requirement_type="required_skill",
            requirement_id="required_skill:0",
            text="Python",
            embedding=[0.1, 0.2, 0.3, 0.4],
            embedding_model="mini",
            embedding_version="v1",
            dimension=4,
            metadata_json={"provider": "local"},
        )
    ]
    second = [
        JobEmbedding(
            job_id="job-1",
            requirement_type="preferred_skill",
            requirement_id="preferred_skill:0",
            text="FastAPI",
            embedding=[0.2, 0.3, 0.4, 0.5],
            embedding_model="mini",
            embedding_version="v1",
            dimension=4,
            metadata_json={"provider": "local"},
        )
    ]

    await replace_job_embeddings(session, "job-1", first)
    await replace_job_embeddings(session, "job-1", second)

    assert len(session.job_rows) == 1
    assert session.job_rows[0].text == "FastAPI"
    assert session.commit_count == 2


def test_prepare_embeddings_persists_batch_metadata() -> None:
    from app.ai.embeddings.base import EmbeddingBatchResult
    from app.ai.embeddings.indexing import prepare_resume_embeddings

    class MetadataEmbeddingClient:
        provider = "deterministic-fallback"
        model_name = "deterministic-token-hash"
        dimension = 4

        def embed_texts(self, texts: list[str]) -> EmbeddingBatchResult:
            return EmbeddingBatchResult(
                provider=self.provider,
                model_name=self.model_name,
                dimension=self.dimension,
                vectors=[[1.0, 0.0, 0.0, 0.0] for _ in texts],
                metadata={"runtime": "deterministic", "fallback_reason": "missing runtime"},
            )

    embeddings = prepare_resume_embeddings(
        "resume-1",
        ResumeExtraction(skills=["Python"]),
        MetadataEmbeddingClient(),
        embedding_version="v1",
    )

    assert embeddings[0].metadata_json == {
        "provider": "deterministic-fallback",
        "runtime": "deterministic",
        "fallback_reason": "missing runtime",
    }
