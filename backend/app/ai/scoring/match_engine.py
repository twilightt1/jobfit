from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.ai.matching.normalization import (
    extract_keywords,
    normalize_skill,
    normalize_skill_list,
    skill_aliases_for,
)
from app.ai.schemas import JobExtraction, JobRequirementItem, ResumeExtraction
from app.db.models.enums import MatchStatus, MatchType

SKILL_WEIGHT = 0.5
REQUIREMENT_WEIGHT = 0.3
EXPERIENCE_WEIGHT = 0.1
LANGUAGE_WEIGHT = 0.1


@dataclass(slots=True)
class MatchEvidenceDraft:
    requirement_id: str | None
    job_requirement_text: str
    resume_section_id: str | None
    resume_section_type: str | None
    resume_evidence_text: str | None
    match_type: str
    match_status: str
    similarity_score: float | None
    confidence: float | None
    explanation: str
    metadata_json: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class MatchComputationResult:
    overall_score: int
    analysis_confidence: float
    breakdown: dict[str, Any]
    strengths: list[str]
    gaps: list[str]
    recommendations: list[str]
    ats_report: dict[str, Any]
    explanation: dict[str, Any]
    evidence: list[MatchEvidenceDraft]
    missing_skills: list[str]
    matched_skills: list[str]


class DeterministicMatchEngine:
    """Rule-based match engine for the MVP scoring flow."""

    def compute(
        self,
        resume: ResumeExtraction,
        job: JobExtraction,
        *,
        resume_parse_confidence: float | None = None,
        job_parse_confidence: float | None = None,
    ) -> MatchComputationResult:
        normalized_resume_skills = normalize_skill_list(resume.skills)
        normalized_job_skills = normalize_skill_list(
            job.required_skills + job.preferred_skills
        )
        experience_texts = resume.experience_highlights + (
            [resume.summary] if resume.summary else []
        )
        matched_skill_records: list[tuple[str, str]] = []
        evidence: list[MatchEvidenceDraft] = []
        strengths: list[str] = []
        gaps: list[str] = []
        recommendations: list[str] = []

        for skill in normalized_job_skills:
            matched_text = self._find_skill_match(skill, normalized_resume_skills, experience_texts)
            if matched_text is None:
                gaps.append(f"Missing explicit support for {skill}.")
                recommendations.append(
                    f"Add verified resume evidence or measurable impact related to {skill}."
                )
                evidence.append(
                    MatchEvidenceDraft(
                        requirement_id=f"skill:{skill}",
                        job_requirement_text=skill,
                        resume_section_id=None,
                        resume_section_type=None,
                        resume_evidence_text=None,
                        match_type=MatchType.MISSING.value,
                        match_status=MatchStatus.MISSING.value,
                        similarity_score=0.0,
                        confidence=0.55,
                        explanation=(
                            "No normalized resume skill or experience evidence matched "
                            f"{skill}."
                        ),
                        metadata_json={"category": "skill"},
                    )
                )
                continue

            matched_skill_records.append((skill, matched_text))
            strengths.append(f"Resume demonstrates {skill}.")
            evidence.append(
                MatchEvidenceDraft(
                    requirement_id=f"skill:{skill}",
                    job_requirement_text=skill,
                    resume_section_id=f"skill:{skill}",
                    resume_section_type=(
                        "skill"
                        if normalize_skill(matched_text) == skill
                        else "experience"
                    ),
                    resume_evidence_text=matched_text,
                    match_type=self._infer_match_type(skill, matched_text),
                    match_status=MatchStatus.STRONG.value,
                    similarity_score=1.0 if normalize_skill(matched_text) == skill else 0.84,
                    confidence=0.82,
                    explanation=f"Normalized skill match found for {skill}.",
                    metadata_json={"category": "skill"},
                )
            )

        requirement_records = self._score_requirements(job.requirements, experience_texts)
        evidence.extend(requirement_records)

        required_languages = self._extract_language_requirements(job)
        language_overlap = sorted(
            set(language.lower() for language in resume.languages) & set(required_languages)
        )
        language_score = 1.0 if not required_languages else min(
            1.0,
            len(language_overlap) / max(1, len(required_languages)),
        )
        if language_overlap:
            strengths.append(
                "Resume includes language coverage for " + ", ".join(language_overlap) + "."
            )
        elif required_languages:
            gaps.append("Job mentions language requirements not found in the resume.")
            recommendations.append("Add confirmed language proficiency details if applicable.")

        experience_score = self._score_experience(resume, job)
        skill_score = len(matched_skill_records) / max(1, len(normalized_job_skills))
        requirement_score = self._aggregate_requirement_score(requirement_records)

        weighted_score = (
            skill_score * SKILL_WEIGHT
            + requirement_score * REQUIREMENT_WEIGHT
            + experience_score * EXPERIENCE_WEIGHT
            + language_score * LANGUAGE_WEIGHT
        )
        overall_score = round(weighted_score * 100)
        analysis_confidence = round(
            min(
                0.97,
                0.6
                + 0.15 * ((resume_parse_confidence or 0.5) + (job_parse_confidence or 0.5))
                + 0.1 * requirement_score,
            ),
            2,
        )

        matched_skills = [skill for skill, _ in matched_skill_records]
        missing_skills = [skill for skill in normalized_job_skills if skill not in matched_skills]

        breakdown = {
            "skills": {
                "score": round(skill_score * 100),
                "matched": matched_skills,
                "missing": missing_skills,
            },
            "requirements": {
                "score": round(requirement_score * 100),
                "evaluated": len(job.requirements),
            },
            "experience": {
                "score": round(experience_score * 100),
                "years": resume.total_years_experience,
            },
            "languages": {
                "score": round(language_score * 100),
                "matched": language_overlap,
            },
        }
        ats_report = {
            "keywords_matched": matched_skills,
            "keywords_missing": missing_skills,
            "coverage_ratio": round(skill_score, 2),
            "warnings": gaps[:4],
        }
        explanation = {
            "summary": self._build_summary(overall_score, matched_skills, missing_skills),
            "top_strengths": strengths[:5],
            "top_gaps": gaps[:5],
        }

        return MatchComputationResult(
            overall_score=overall_score,
            analysis_confidence=analysis_confidence,
            breakdown=breakdown,
            strengths=strengths[:6],
            gaps=gaps[:6],
            recommendations=recommendations[:6],
            ats_report=ats_report,
            explanation=explanation,
            evidence=evidence,
            missing_skills=missing_skills,
            matched_skills=matched_skills,
        )

    def _find_skill_match(
        self,
        skill: str,
        normalized_resume_skills: list[str],
        experience_texts: list[str],
    ) -> str | None:
        if skill in normalized_resume_skills:
            return skill

        aliases = skill_aliases_for(skill)
        for text in experience_texts:
            keywords = extract_keywords(text)
            if aliases & keywords:
                return text
        return None

    def _score_requirements(
        self,
        requirements: list[JobRequirementItem],
        experience_texts: list[str],
    ) -> list[MatchEvidenceDraft]:
        requirement_evidence: list[MatchEvidenceDraft] = []
        for index, requirement in enumerate(requirements, start=1):
            matched_text = self._find_requirement_evidence(
                requirement.requirement,
                experience_texts,
            )
            if matched_text is None:
                requirement_evidence.append(
                    MatchEvidenceDraft(
                        requirement_id=f"req:{index}",
                        job_requirement_text=requirement.requirement,
                        resume_section_id=None,
                        resume_section_type=None,
                        resume_evidence_text=None,
                        match_type=MatchType.MISSING.value,
                        match_status=MatchStatus.MISSING.value,
                        similarity_score=0.0,
                        confidence=0.5,
                        explanation="No direct resume bullet or summary support found.",
                        metadata_json={"category": requirement.requirement_type},
                    )
                )
                continue

            overlap = self._keyword_overlap(requirement.requirement, matched_text)
            requirement_evidence.append(
                MatchEvidenceDraft(
                    requirement_id=f"req:{index}",
                    job_requirement_text=requirement.requirement,
                    resume_section_id=f"exp:{index}",
                    resume_section_type="experience",
                    resume_evidence_text=matched_text,
                    match_type=MatchType.FUZZY.value,
                    match_status=(
                        MatchStatus.STRONG.value if overlap >= 0.5 else MatchStatus.PARTIAL.value
                    ),
                    similarity_score=round(overlap, 2),
                    confidence=round(min(0.9, 0.55 + overlap * 0.5), 2),
                    explanation=(
                        "Keyword overlap found between job requirement and "
                        "resume evidence."
                    ),
                    metadata_json={"category": requirement.requirement_type},
                )
            )
        return requirement_evidence

    def _find_requirement_evidence(
        self,
        requirement_text: str,
        experience_texts: list[str],
    ) -> str | None:
        best_text: str | None = None
        best_overlap = 0.0
        for text in experience_texts:
            overlap = self._keyword_overlap(requirement_text, text)
            if overlap > best_overlap:
                best_text = text
                best_overlap = overlap
        return best_text if best_overlap >= 0.2 else None

    def _keyword_overlap(self, left: str, right: str) -> float:
        left_keywords = extract_keywords(left)
        right_keywords = extract_keywords(right)
        if not left_keywords:
            return 0.0
        return len(left_keywords & right_keywords) / len(left_keywords)

    def _aggregate_requirement_score(self, evidence: list[MatchEvidenceDraft]) -> float:
        if not evidence:
            return 0.0

        total = 0.0
        for item in evidence:
            if item.match_status == MatchStatus.STRONG.value:
                total += 1.0
            elif item.match_status == MatchStatus.PARTIAL.value:
                total += 0.6
        return total / len(evidence)

    def _score_experience(self, resume: ResumeExtraction, job: JobExtraction) -> float:
        if resume.total_years_experience is None:
            return 0.55 if resume.experience_highlights else 0.3

        target_years = 5.0 if job.seniority == "senior" else 3.0 if job.seniority == "mid" else 1.0
        ratio = resume.total_years_experience / max(1.0, target_years)
        return min(1.0, max(0.0, ratio))

    def _extract_language_requirements(self, job: JobExtraction) -> list[str]:
        combined = " ".join([job.summary or "", *job.responsibilities, *job.required_skills])
        languages = ["english", "vietnamese", "japanese", "french", "german"]
        return [language for language in languages if language in combined.lower()]

    def _infer_match_type(self, skill: str, matched_text: str) -> str:
        return MatchType.EXACT.value if matched_text == skill else MatchType.HYBRID.value

    def _build_summary(
        self,
        overall_score: int,
        matched_skills: list[str],
        missing_skills: list[str],
    ) -> str:
        if overall_score >= 80:
            verdict = "strong"
        elif overall_score >= 60:
            verdict = "promising"
        else:
            verdict = "limited"

        matched_preview = ", ".join(matched_skills[:4]) or "no major required skills"
        missing_preview = ", ".join(missing_skills[:3]) or "no critical gaps"
        return (
            f"This candidate shows a {verdict} deterministic fit. "
            f"Matched signals include {matched_preview}; gaps include {missing_preview}."
        )
