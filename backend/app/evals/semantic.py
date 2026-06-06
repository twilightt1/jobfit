from __future__ import annotations

from dataclasses import dataclass

from app.ai.embeddings.factory import get_embedding_client
from app.ai.embeddings.indexing import prepare_job_embeddings, prepare_resume_embeddings
from app.ai.embeddings.semantic import (
    find_best_semantic_requirement_matches,
    find_best_semantic_skill_matches,
)
from app.ai.schemas import JobExtraction, ResumeExtraction
from app.core.config import Settings


@dataclass(slots=True)
class SemanticEvalMatches:
    skill_matches: dict[str, dict[str, object]]
    requirement_matches: dict[str, dict[str, object]]
    warning: str | None = None



def build_semantic_eval_matches(
    *,
    resume_id: str,
    job_id: str,
    resume: ResumeExtraction,
    job: JobExtraction,
    settings: Settings,
    score_threshold: float = 0.2,
) -> SemanticEvalMatches:
    embedding_selection = get_embedding_client(settings)
    embedding_client = embedding_selection.client
    warning = embedding_selection.warning

    resume_embeddings = prepare_resume_embeddings(
        resume_id,
        resume,
        embedding_client,
        embedding_version="eval-v1",
    )
    job_embeddings = prepare_job_embeddings(
        job_id,
        job,
        embedding_client,
        embedding_version="eval-v1",
    )
    return SemanticEvalMatches(
        skill_matches=find_best_semantic_skill_matches(
            resume_embeddings,
            job_embeddings,
            score_threshold=score_threshold,
        ),
        requirement_matches=find_best_semantic_requirement_matches(
            resume_embeddings,
            job_embeddings,
            score_threshold=score_threshold,
        ),
        warning=warning,
    )
