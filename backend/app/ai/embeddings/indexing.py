from __future__ import annotations

from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.embeddings.base import (
    EmbeddingClient,
    JobEmbeddingInput,
    ResumeEmbeddingInput,
)
from app.ai.schemas import JobExtraction, ResumeExtraction
from app.db.models.embedding import JobEmbedding, ResumeEmbedding


def build_resume_embedding_inputs(
    resume_id: str,
    resume: ResumeExtraction,
) -> list[ResumeEmbeddingInput]:
    inputs: list[ResumeEmbeddingInput] = []

    if resume.summary:
        inputs.append(
            ResumeEmbeddingInput(
                resume_id=resume_id,
                section_type="summary",
                section_id="summary",
                text=resume.summary,
            )
        )

    for index, skill in enumerate(resume.skills):
        if skill.strip():
            inputs.append(
                ResumeEmbeddingInput(
                    resume_id=resume_id,
                    section_type="skill",
                    section_id=f"skill:{index}",
                    text=skill,
                )
            )

    for index, highlight in enumerate(resume.experience_highlights):
        if highlight.strip():
            inputs.append(
                ResumeEmbeddingInput(
                    resume_id=resume_id,
                    section_type="experience",
                    section_id=f"experience:{index}",
                    text=highlight,
                )
            )

    return inputs


def build_job_embedding_inputs(
    job_id: str,
    job: JobExtraction,
) -> list[JobEmbeddingInput]:
    inputs: list[JobEmbeddingInput] = []

    for index, skill in enumerate(job.required_skills):
        if skill.strip():
            inputs.append(
                JobEmbeddingInput(
                    job_id=job_id,
                    requirement_type="required_skill",
                    requirement_id=f"required_skill:{index}",
                    text=skill,
                )
            )

    for index, skill in enumerate(job.preferred_skills):
        if skill.strip():
            inputs.append(
                JobEmbeddingInput(
                    job_id=job_id,
                    requirement_type="preferred_skill",
                    requirement_id=f"preferred_skill:{index}",
                    text=skill,
                )
            )

    for index, requirement in enumerate(job.requirements):
        if requirement.requirement.strip():
            inputs.append(
                JobEmbeddingInput(
                    job_id=job_id,
                    requirement_type="requirement",
                    requirement_id=f"req:{index + 1}",
                    text=requirement.requirement,
                )
            )

    for index, responsibility in enumerate(job.responsibilities):
        if responsibility.strip():
            inputs.append(
                JobEmbeddingInput(
                    job_id=job_id,
                    requirement_type="responsibility",
                    requirement_id=f"responsibility:{index}",
                    text=responsibility,
                )
            )

    return inputs


def prepare_resume_embeddings(
    resume_id: str,
    resume: ResumeExtraction,
    embedding_client: EmbeddingClient,
    *,
    embedding_version: str,
) -> list[ResumeEmbedding]:
    inputs = build_resume_embedding_inputs(resume_id, resume)
    if not inputs:
        return []

    result = embedding_client.embed_texts([item.text for item in inputs])
    embeddings: list[ResumeEmbedding] = []

    for item, vector in zip(inputs, result.vectors, strict=True):
        embeddings.append(
            ResumeEmbedding(
                resume_id=item.resume_id,
                section_type=item.section_type,
                section_id=item.section_id,
                text=item.text,
                embedding=vector,
                embedding_model=result.model_name,
                embedding_version=embedding_version,
                dimension=result.dimension,
                metadata_json={"provider": result.provider, **result.metadata, **item.metadata},
            )
        )

    return embeddings


def prepare_job_embeddings(
    job_id: str,
    job: JobExtraction,
    embedding_client: EmbeddingClient,
    *,
    embedding_version: str,
) -> list[JobEmbedding]:
    inputs = build_job_embedding_inputs(job_id, job)
    if not inputs:
        return []

    result = embedding_client.embed_texts([item.text for item in inputs])
    embeddings: list[JobEmbedding] = []

    for item, vector in zip(inputs, result.vectors, strict=True):
        embeddings.append(
            JobEmbedding(
                job_id=item.job_id,
                requirement_type=item.requirement_type,
                requirement_id=item.requirement_id,
                text=item.text,
                embedding=vector,
                embedding_model=result.model_name,
                embedding_version=embedding_version,
                dimension=result.dimension,
                metadata_json={"provider": result.provider, **result.metadata, **item.metadata},
            )
        )

    return embeddings


async def replace_resume_embeddings(
    session: AsyncSession,
    resume_id: str,
    embeddings: list[ResumeEmbedding],
) -> None:
    await session.execute(delete(ResumeEmbedding).where(ResumeEmbedding.resume_id == resume_id))
    session.add_all(embeddings)
    await session.commit()


async def replace_job_embeddings(
    session: AsyncSession,
    job_id: str,
    embeddings: list[JobEmbedding],
) -> None:
    await session.execute(delete(JobEmbedding).where(JobEmbedding.job_id == job_id))
    session.add_all(embeddings)
    await session.commit()


__all__ = [
    "build_job_embedding_inputs",
    "build_resume_embedding_inputs",
    "prepare_job_embeddings",
    "prepare_resume_embeddings",
    "replace_job_embeddings",
    "replace_resume_embeddings",
]
