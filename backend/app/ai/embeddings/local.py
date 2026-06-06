from __future__ import annotations

from typing import Any

from app.ai.embeddings.base import EmbeddingBatchResult, EmbeddingClient
from app.core.config import Settings


def _load_sentence_transformer(model_name: str) -> Any:
    from sentence_transformers import SentenceTransformer  # type: ignore[import-not-found]

    return SentenceTransformer(model_name)


class LocalEmbeddingClient(EmbeddingClient):
    provider = "local"

    def __init__(self, settings: Settings) -> None:
        self.model_name = settings.embedding_model
        self.dimension = settings.embedding_dimension
        self._model = _load_sentence_transformer(self.model_name)

    def embed_texts(self, texts: list[str]) -> EmbeddingBatchResult:
        if not texts:
            return EmbeddingBatchResult(
                provider=self.provider,
                model_name=self.model_name,
                dimension=self.dimension,
                vectors=[],
            )

        vectors = self._model.encode(
            texts,
            convert_to_numpy=False,
            normalize_embeddings=True,
        )
        normalized_vectors = [list(vector) for vector in vectors]
        self._validate_dimensions(normalized_vectors)
        return EmbeddingBatchResult(
            provider=self.provider,
            model_name=self.model_name,
            dimension=self.dimension,
            vectors=normalized_vectors,
        )

    def _validate_dimensions(self, vectors: list[list[float]]) -> None:
        for vector in vectors:
            if len(vector) != self.dimension:
                raise ValueError(
                    f"Embedding dimension mismatch: expected {self.dimension}, got {len(vector)}."
                )
