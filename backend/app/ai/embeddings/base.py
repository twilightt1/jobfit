from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol


@dataclass(slots=True)
class EmbeddingBatchResult:
    provider: str
    model_name: str
    dimension: int
    vectors: list[list[float]]
    metadata: dict[str, object] = field(default_factory=dict)


@dataclass(slots=True)
class ResumeEmbeddingInput:
    resume_id: str
    section_type: str
    section_id: str
    text: str
    metadata: dict[str, object] = field(default_factory=dict)


@dataclass(slots=True)
class JobEmbeddingInput:
    job_id: str
    requirement_type: str
    requirement_id: str
    text: str
    metadata: dict[str, object] = field(default_factory=dict)


class EmbeddingClient(Protocol):
    provider: str
    model_name: str
    dimension: int

    def embed_texts(self, texts: list[str]) -> EmbeddingBatchResult: ...
