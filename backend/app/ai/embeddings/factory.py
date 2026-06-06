from __future__ import annotations

from dataclasses import dataclass

from app.ai.embeddings.base import EmbeddingClient
from app.ai.embeddings.deterministic import DeterministicEmbeddingClient
from app.ai.embeddings.local import LocalEmbeddingClient
from app.core.config import Settings


@dataclass(slots=True)
class EmbeddingClientSelection:
    client: EmbeddingClient
    warning: str | None = None


def get_embedding_client(settings: Settings) -> EmbeddingClientSelection:
    """Create the configured embedding client with clone-and-run fallback behavior."""

    if settings.embedding_provider == "local":
        try:
            return EmbeddingClientSelection(client=LocalEmbeddingClient(settings))
        except Exception as exc:
            warning = f"Local embedding runtime unavailable; using deterministic fallback: {exc}"
            return EmbeddingClientSelection(
                client=DeterministicEmbeddingClient(
                    dimension=settings.embedding_dimension,
                    fallback_reason=str(exc),
                ),
                warning=warning,
            )

    warning = (
        f"Unsupported embedding provider '{settings.embedding_provider}'; "
        "using deterministic fallback."
    )
    return EmbeddingClientSelection(
        client=DeterministicEmbeddingClient(
            dimension=settings.embedding_dimension,
            provider=f"{settings.embedding_provider}-fallback",
            fallback_reason=warning,
        ),
        warning=warning,
    )
