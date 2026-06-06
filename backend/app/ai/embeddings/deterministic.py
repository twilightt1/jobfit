from __future__ import annotations

from app.ai.embeddings.base import EmbeddingBatchResult, EmbeddingClient


class DeterministicEmbeddingClient(EmbeddingClient):
    """Tiny deterministic fallback for clone-and-run flows without local ML deps."""

    def __init__(
        self,
        *,
        dimension: int = 384,
        provider: str = "deterministic-fallback",
        model_name: str = "deterministic-token-hash",
        fallback_reason: str | None = None,
    ) -> None:
        self.provider = provider
        self.model_name = model_name
        self.dimension = dimension
        self.fallback_reason = fallback_reason

    def embed_texts(self, texts: list[str]) -> EmbeddingBatchResult:
        metadata: dict[str, object] = {"runtime": "deterministic"}
        if self.fallback_reason:
            metadata["fallback_reason"] = self.fallback_reason
        return EmbeddingBatchResult(
            provider=self.provider,
            model_name=self.model_name,
            dimension=self.dimension,
            vectors=[self._embed_text(text) for text in texts],
            metadata=metadata,
        )

    def _embed_text(self, text: str) -> list[float]:
        vector = [0.0] * self.dimension
        for token in _tokenize(text):
            index = sum(ord(character) for character in token) % self.dimension
            vector[index] += 1.0
        norm = sum(value * value for value in vector) ** 0.5
        if norm == 0.0:
            return vector
        return [value / norm for value in vector]


def _tokenize(text: str) -> list[str]:
    normalized = "".join(character.casefold() if character.isalnum() else " " for character in text)
    return [token for token in normalized.split() if token]
