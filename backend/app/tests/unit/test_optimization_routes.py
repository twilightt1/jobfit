from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

NOW = datetime(2026, 6, 13, 0, 0, tzinfo=UTC)


def test_create_optimization_flow(client: TestClient) -> None:
    match_report = SimpleNamespace(
        id="report-123",
        resume_id="resume-123",
        job_id="job-123",
        overall_score=72,
    )
    resume_record = SimpleNamespace(
        id="resume-123",
        parsed_json={"skills": ["Python"], "experience_highlights": ["Built APIs."]},
    )
    job_record = SimpleNamespace(
        id="job-123",
        parsed_json={"required_skills": ["Python"], "requirements": []},
    )
    created_optimization = SimpleNamespace(id="opt-123")
    loaded_optimization = SimpleNamespace(
        id="opt-123",
        user_id=None,
        session_id="session-opt-1",
        resume_id="resume-123",
        job_id="job-123",
        match_report_id="report-123",
        version_name="Targeted resume draft",
        content_json={
            "summary": "Backend engineer aligned to the target role.",
            "skills": ["python", "fastapi"],
        },
        score_before=72,
        score_after=82,
        status="review_recommended",
        generated_by_ai_run_id="airun-opt-1",
        created_at=NOW,
        updated_at=NOW,
        suggestions=[
            SimpleNamespace(
                id="suggestion-1",
                optimized_resume_id="opt-123",
                section_type="summary",
                target_location="professional_summary",
                original_text="Backend engineer building APIs.",
                suggested_text="Backend engineer building APIs aligned to the target role.",
                user_edited_text=None,
                targeted_requirements=["Build production APIs"],
                keywords_added=["fastapi"],
                reason="Align the summary with the target role.",
                estimated_score_lift=5,
                truth_status="needs_review",
                new_claims_json=["target"],
                guardrail_reason="Suggestion adds wording not directly supported.",
                decision="pending",
                accepted_by_user=False,
                generated_by_ai_run_id="airun-guard-1",
                created_at=NOW,
                updated_at=NOW,
            )
        ],
    )

    with (
        patch(
            "app.api.routes.optimizations.get_latest_optimized_resume_for_match",
            new_callable=AsyncMock,
        ) as get_latest_optimization,
        patch(
            "app.api.routes.optimizations.get_match_report",
            new_callable=AsyncMock,
        ) as get_match_report,
        patch(
            "app.api.routes.optimizations.get_resume",
            new_callable=AsyncMock,
        ) as get_resume,
        patch(
            "app.api.routes.optimizations.get_job",
            new_callable=AsyncMock,
        ) as get_job,
        patch(
            "app.api.routes.optimizations.optimize_resume_for_match",
            new_callable=AsyncMock,
        ) as optimize_resume_for_match,
        patch(
            "app.api.routes.optimizations.get_optimized_resume",
            new_callable=AsyncMock,
        ) as get_optimized_resume,
    ):
        get_latest_optimization.return_value = None
        get_match_report.return_value = match_report
        get_resume.return_value = resume_record
        get_job.return_value = job_record
        optimize_resume_for_match.return_value = created_optimization
        get_optimized_resume.side_effect = [loaded_optimization, loaded_optimization]

        create_response = client.post(
            "/api/optimizations",
            json={"match_report_id": "report-123"},
        )
        assert create_response.status_code == 201
        payload = create_response.json()
        assert payload["id"] == "opt-123"
        assert payload["score_after"] == 82
        assert payload["suggestions"][0]["truth_status"] == "needs_review"

        get_response = client.get("/api/optimizations/opt-123")
        assert get_response.status_code == 200
        get_payload = get_response.json()
        assert get_payload["id"] == "opt-123"
        assert get_payload["suggestions"][0]["keywords_added"] == ["fastapi"]


def test_create_optimization_reuses_existing_result(client: TestClient) -> None:
    existing_optimization = SimpleNamespace(
        id="opt-existing",
        user_id=None,
        session_id="session-opt-1",
        resume_id="resume-123",
        job_id="job-123",
        match_report_id="report-123",
        version_name="Targeted resume draft",
        content_json={"skills": ["python"]},
        score_before=72,
        score_after=78,
        status="draft",
        generated_by_ai_run_id="airun-opt-existing",
        created_at=NOW,
        updated_at=NOW,
        suggestions=[],
    )

    with (
        patch(
            "app.api.routes.optimizations.get_latest_optimized_resume_for_match",
            new_callable=AsyncMock,
        ) as get_latest_optimization,
        patch(
            "app.api.routes.optimizations.optimize_resume_for_match",
            new_callable=AsyncMock,
        ) as optimize_resume_for_match,
    ):
        get_latest_optimization.return_value = existing_optimization

        response = client.post(
            "/api/optimizations",
            json={"match_report_id": "report-123"},
        )
        assert response.status_code == 201
        assert response.json()["id"] == "opt-existing"
        optimize_resume_for_match.assert_not_awaited()


def test_create_optimization_requires_parsed_inputs(client: TestClient) -> None:
    match_report = SimpleNamespace(id="report-123", resume_id="resume-unparsed", job_id="job-123")
    resume_record = SimpleNamespace(id="resume-unparsed", parsed_json=None)
    job_record = SimpleNamespace(id="job-123", parsed_json={"required_skills": ["Python"]})

    with (
        patch(
            "app.api.routes.optimizations.get_latest_optimized_resume_for_match",
            new_callable=AsyncMock,
        ) as get_latest_optimization,
        patch(
            "app.api.routes.optimizations.get_match_report",
            new_callable=AsyncMock,
        ) as get_match_report,
        patch(
            "app.api.routes.optimizations.get_resume",
            new_callable=AsyncMock,
        ) as get_resume,
        patch(
            "app.api.routes.optimizations.get_job",
            new_callable=AsyncMock,
        ) as get_job,
    ):
        get_latest_optimization.return_value = None
        get_match_report.return_value = match_report
        get_resume.return_value = resume_record
        get_job.return_value = job_record

        response = client.post(
            "/api/optimizations",
            json={"match_report_id": "report-123"},
        )
        assert response.status_code == 409
        assert response.json()["detail"] == "Resume must be parsed before optimization"
