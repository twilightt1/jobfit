from __future__ import annotations

import math
from typing import Any

from app.ai.matching.normalization import normalize_skill
from app.db.models.embedding import JobEmbedding, ResumeEmbedding


def cosine_similarity(left: list[float], right: list[float]) -> float:
    if len(left) != len(right) or not left:
        return 0.0

    dot_product = sum(
        left_item * right_item
        for left_item, right_item in zip(left, right, strict=True)
    )
    left_norm = math.sqrt(sum(value * value for value in left))
    right_norm = math.sqrt(sum(value * value for value in right))
    if left_norm == 0.0 or right_norm == 0.0:
        return 0.0
    return dot_product / (left_norm * right_norm)


def find_best_semantic_skill_matches(
    resume_embeddings: list[ResumeEmbedding],
    job_embeddings: list[JobEmbedding],
    *,
    score_threshold: float,
) -> dict[str, dict[str, Any]]:
    matches: dict[str, dict[str, Any]] = {}
    for job_embedding in job_embeddings:
        if job_embedding.requirement_type not in {"required_skill", "preferred_skill"}:
            continue
        match = _best_resume_match_for_job_embedding(
            job_embedding,
            resume_embeddings,
            score_threshold=score_threshold,
        )
        if match is not None:
            matches[normalize_skill(job_embedding.text)] = match
    return matches


def find_best_semantic_requirement_matches(
    resume_embeddings: list[ResumeEmbedding],
    job_embeddings: list[JobEmbedding],
    *,
    score_threshold: float,
) -> dict[str, dict[str, Any]]:
    matches: dict[str, dict[str, Any]] = {}
    for job_embedding in job_embeddings:
        if job_embedding.requirement_type != "requirement":
            continue
        if not job_embedding.requirement_id:
            continue
        match = _best_resume_match_for_job_embedding(
            job_embedding,
            resume_embeddings,
            score_threshold=score_threshold,
        )
        if match is not None:
            matches[job_embedding.requirement_id] = match
    return matches


def _best_resume_match_for_job_embedding(
    job_embedding: JobEmbedding,
    resume_embeddings: list[ResumeEmbedding],
    *,
    score_threshold: float,
) -> dict[str, Any] | None:
    best_resume_embedding: ResumeEmbedding | None = None
    best_score = score_threshold

    for resume_embedding in resume_embeddings:
        if resume_embedding.embedding is None or job_embedding.embedding is None:
            continue
        score = cosine_similarity(list(job_embedding.embedding), list(resume_embedding.embedding))
        if score > best_score:
            best_score = score
            best_resume_embedding = resume_embedding

    if best_resume_embedding is None:
        return None

    return {
        "text": best_resume_embedding.text,
        "score": round(best_score, 4),
        "match_type": "semantic",
        "resume_section_id": best_resume_embedding.section_id,
        "resume_section_type": best_resume_embedding.section_type,
        "job_requirement_id": job_embedding.requirement_id,
        "job_requirement_type": job_embedding.requirement_type,
        "embedding_model": best_resume_embedding.embedding_model,
        "embedding_provider": _metadata_value(best_resume_embedding.metadata_json, "provider"),
        "score_threshold": score_threshold,
    }


def _metadata_value(metadata: dict[str, Any] | None, key: str) -> object | None:
    if metadata is None:
        return None
    return metadata.get(key)
