from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

NOW = datetime(2026, 6, 13, 0, 0, tzinfo=UTC)


def test_create_match_report_flow(client: TestClient) -> None:
    resume_record = SimpleNamespace(
        id="resume-123",
        user_id=None,
        title="Senior Backend Resume",
        raw_text="Jane Doe\nSenior Backend Engineer\nSkills: Python, FastAPI\n",
        session_id="session-match-1",
        parse_status="completed",
        parse_confidence=0.88,
        parsed_json={
            "candidate_name": "Jane Doe",
            "summary": "Backend engineer building APIs and ML services.",
            "skills": ["Python", "FastAPI", "PostgreSQL"],
            "experience_highlights": [
                "Built FastAPI services for ML inference and PostgreSQL-backed pipelines.",
                "Deployed Python APIs with Docker and CI/CD automation.",
            ],
            "languages": ["English"],
            "total_years_experience": 5,
        },
        parse_warnings=None,
        parse_error=None,
        created_at=NOW,
        updated_at=NOW,
    )
    job_record = SimpleNamespace(
        id="job-123",
        user_id=None,
        title="Senior ML Engineer",
        company="Acme AI",
        description="Senior ML Engineer\nRequirements: Python, FastAPI, PostgreSQL\n",
        status="saved",
        session_id="session-match-1",
        parse_status="completed",
        parse_confidence=0.91,
        parsed_json={
            "title": "Senior ML Engineer",
            "company": "Acme AI",
            "summary": "Build production ML APIs in English-speaking environments.",
            "required_skills": ["Python", "FastAPI", "PostgreSQL"],
            "preferred_skills": ["Docker"],
            "requirements": [
                {
                    "requirement": "Build FastAPI services for ML inference and APIs.",
                    "requirement_type": "required",
                },
                {
                    "requirement": "Collaborate in English with cross-functional teams.",
                    "requirement_type": "required",
                },
            ],
            "responsibilities": ["Own backend services for model deployment."],
            "seniority": "senior",
        },
        parse_warnings=None,
        parse_error=None,
        created_at=NOW,
        updated_at=NOW,
    )
    created_report = SimpleNamespace(id="report-123")
    loaded_report = SimpleNamespace(
        id="report-123",
        user_id=None,
        session_id="session-match-1",
        resume_id="resume-123",
        job_id="job-123",
        overall_score=87,
        analysis_confidence=0.83,
        breakdown_json={
            "skills": {"score": 75, "matched": ["python", "fastapi", "postgresql"]},
            "requirements": {"score": 80, "evaluated": 2},
        },
        strengths_json=["Resume demonstrates python."],
        gaps_json=["Missing explicit support for docker."],
        recommendations_json=["Add verified resume evidence related to docker."],
        ats_report_json={"coverage_ratio": 0.75},
        explanation_json={"summary": "Strong deterministic fit."},
        model_metadata_json={"engine": "deterministic-v1"},
        created_at=NOW,
        updated_at=NOW,
        evidence=[
            SimpleNamespace(
                id="evidence-1",
                requirement_id="skill:python",
                job_requirement_text="python",
                resume_section_id="skill:python",
                resume_section_type="skill",
                resume_evidence_text="python",
                match_type="exact",
                match_status="strong",
                similarity_score=1.0,
                confidence=0.82,
                explanation="Normalized skill match found for python.",
                metadata_json={"category": "skill"},
                created_at=NOW,
            )
        ],
    )

    with (
        patch(
            "app.api.routes.match_reports.get_match_report_by_resume_job",
            new_callable=AsyncMock,
        ) as get_existing_report,
        patch(
            "app.api.routes.match_reports.get_resume",
            new_callable=AsyncMock,
        ) as get_resume,
        patch(
            "app.api.routes.match_reports.get_job",
            new_callable=AsyncMock,
        ) as get_job,
        patch(
            "app.api.routes.match_reports.create_match_report_record",
            new_callable=AsyncMock,
        ) as create_match_report_record,
        patch(
            "app.api.routes.match_reports.get_match_report",
            new_callable=AsyncMock,
        ) as get_match_report,
    ):
        get_existing_report.return_value = None
        get_resume.return_value = resume_record
        get_job.return_value = job_record
        create_match_report_record.return_value = created_report
        get_match_report.side_effect = [loaded_report, loaded_report]

        create_response = client.post(
            "/api/match-reports",
            json={"resume_id": "resume-123", "job_id": "job-123"},
        )
        assert create_response.status_code == 201
        payload = create_response.json()
        assert payload["id"] == "report-123"
        assert payload["overall_score"] == 87
        assert payload["evidence"][0]["match_status"] == "strong"

        get_response = client.get("/api/match-reports/report-123")
        assert get_response.status_code == 200
        get_payload = get_response.json()
        assert get_payload["id"] == "report-123"
        assert get_payload["breakdown_json"]["skills"]["score"] == 75


def test_create_match_report_requires_parsed_inputs(client: TestClient) -> None:
    resume_record = SimpleNamespace(
        id="resume-unparsed",
        parsed_json=None,
    )
    job_record = SimpleNamespace(
        id="job-123",
        parsed_json={"required_skills": ["Python"]},
    )

    with (
        patch(
            "app.api.routes.match_reports.get_match_report_by_resume_job",
            new_callable=AsyncMock,
        ) as get_existing_report,
        patch(
            "app.api.routes.match_reports.get_resume",
            new_callable=AsyncMock,
        ) as get_resume,
        patch(
            "app.api.routes.match_reports.get_job",
            new_callable=AsyncMock,
        ) as get_job,
    ):
        get_existing_report.return_value = None
        get_resume.return_value = resume_record
        get_job.return_value = job_record

        response = client.post(
            "/api/match-reports",
            json={"resume_id": "resume-unparsed", "job_id": "job-123"},
        )
        assert response.status_code == 409
        assert response.json()["detail"] == "Resume must be parsed before creating a match report"
