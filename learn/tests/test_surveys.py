"""Tests for the Learn survey API handlers."""

import json
from unittest.mock import AsyncMock

from tests.helpers import MockDB, MockRow, json_request, load_worker, make_env, make_stmt


worker = load_worker()

JWT_SECRET = "test-jwt-secret"


def _parse(response):
    return json.loads(response.body)


def _token(uid="user-1", username="Survey User", role="student"):
    return worker.create_token(uid, username, role, JWT_SECRET)


def _auth(uid="user-1", role="student"):
    return {"Authorization": f"Bearer {_token(uid=uid, role=role)}"}


def _env_with(db):
    env = make_env(db=db)
    env.DB.batch = AsyncMock(return_value=None)
    return env


def _survey(owner_id="user-1", survey_id="survey-1"):
    return MockRow(
        id=survey_id,
        title="Course Survey",
        description="Your feedback",
        user_id=owner_id,
        created_at="2026-11-01",
        author_name="Instructor",
    )


class TestListSurveys:
    async def test_unauthenticated_request_lists_public_surveys(self):
        row = MockRow(
            id="survey-1",
            title="Course Survey",
            description="Feedback",
            user_id="user-2",
            created_at="2026-11-01",
            author_name="Instructor",
            question_count=2,
            response_count=1,
        )
        env = make_env(db=MockDB([make_stmt(all_results=[row])]))
        response = await worker.api_list_surveys(json_request("/api/surveys", {}, method="GET"), env)

        assert response.status == 200
        assert _parse(response)["surveys"][0]["title"] == "Course Survey"
        assert _parse(response)["surveys"][0]["is_own"] is False

    async def test_empty_list_is_a_successful_response(self):
        env = make_env(db=MockDB([make_stmt(all_results=[])]))
        response = await worker.api_list_surveys(json_request("/api/surveys", {}, method="GET"), env)

        assert response.status == 200
        assert _parse(response)["surveys"] == []


class TestCreateSurvey:
    async def test_create_without_auth_returns_401(self):
        response = await worker.api_create_survey(
            json_request("/api/surveys", {"title": "Survey"}),
            make_env(),
        )

        assert response.status == 401

    async def test_create_without_title_returns_400(self):
        response = await worker.api_create_survey(
            json_request("/api/surveys", {"title": "  ", "questions": [{"text": "Question?", "type": "mcq", "choices": ["A", "B"]}]}, headers=_auth()),
            make_env(),
        )

        assert response.status == 400
        assert "Survey title is required" in _parse(response)["error"]

    async def test_create_without_questions_returns_400(self):
        response = await worker.api_create_survey(
            json_request("/api/surveys", {"title": "Survey", "questions": []}, headers=_auth()),
            make_env(),
        )

        assert response.status == 400

    async def test_create_survey_happy_path(self):
        env = _env_with(make_env().DB)
        response = await worker.api_create_survey(
            json_request(
                "/api/surveys",
                {
                    "title": "Course Survey",
                    "description": "Your feedback",
                    "questions": [
                        {"text": "Pick one", "type": "mcq", "required": True, "choices": ["A", "B"]},
                        {"text": "Comments", "type": "text", "required": False},
                    ],
                },
                headers=_auth(),
            ),
            env,
        )

        assert response.status == 200
        assert _parse(response)["success"] is True
        assert _parse(response)["data"]["id"]
        assert env.DB.batch.await_count == 1


class TestGetSurvey:
    async def test_get_missing_survey_returns_404(self):
        env = make_env(db=MockDB([make_stmt(first=None)]))
        response = await worker.api_get_survey(
            json_request("/api/surveys/missing", {}, method="GET"),
            env,
            "missing",
        )

        assert response.status == 404

    async def test_get_survey_happy_path(self):
        survey = _survey()
        questions = [MockRow(id="q-1", text="Pick one", type="mcq", required=1, position=0)]
        choices = [MockRow(id="c-1", question_id="q-1", text="A", position=0)]
        env = make_env(db=MockDB([
            make_stmt(first=survey),
            make_stmt(all_results=questions),
            make_stmt(all_results=choices),
            make_stmt(first=None),
        ]))

        response = await worker.api_get_survey(
            json_request("/api/surveys/survey-1", {}, method="GET", headers=_auth()),
            env,
            "survey-1",
        )

        assert response.status == 200
        data = _parse(response)
        assert data["title"] == "Course Survey"
        assert data["questions"][0]["choices"][0]["text"] == "A"


class TestSubmitSurvey:
    async def test_submit_without_auth_returns_401(self):
        response = await worker.api_submit_survey(
            json_request("/api/surveys/survey-1/submissions", {"answers": {"q-1": "c-1"}}),
            make_env(),
            "survey-1",
        )

        assert response.status == 401

    async def test_submit_required_question_missing_returns_400(self):
        survey = _survey()
        questions = [MockRow(id="q-1", text="Pick one", type="mcq", required=1, position=0)]
        choices = [MockRow(id="c-1", question_id="q-1", text="A", position=0)]
        env = make_env(db=MockDB([
            make_stmt(first=survey),
            make_stmt(all_results=questions),
            make_stmt(all_results=choices),
            make_stmt(first=None),
        ]))

        response = await worker.api_submit_survey(
            json_request("/api/surveys/survey-1/submissions", {"answers": {}}, headers=_auth()),
            env,
            "survey-1",
        )

        assert response.status == 400
        assert "required" in _parse(response)["error"]

    async def test_submit_invalid_answers_type_returns_400(self):
        response = await worker.api_submit_survey(
            json_request("/api/surveys/survey-1/submissions", {"answers": []}, headers=_auth()),
            make_env(),
            "survey-1",
        )

        assert response.status == 400

    async def test_submit_survey_happy_path(self):
        survey = _survey()
        questions = [MockRow(id="q-1", text="Pick one", type="mcq", required=1, position=0)]
        choices = [
            MockRow(id="c-1", question_id="q-1", text="A", position=0),
            MockRow(id="c-2", question_id="q-1", text="B", position=1),
        ]
        env = _env_with(MockDB([
            make_stmt(first=survey),
            make_stmt(all_results=questions),
            make_stmt(all_results=choices),
            make_stmt(first=None),
        ]))

        response = await worker.api_submit_survey(
            json_request("/api/surveys/survey-1/submissions", {"answers": {"q-1": "c-1"}}, headers=_auth()),
            env,
            "survey-1",
        )

        assert response.status == 200
        assert _parse(response)["message"] == "Survey submitted"
        assert env.DB.batch.await_count == 1


class TestDeleteSurvey:
    async def test_delete_without_auth_returns_401(self):
        response = await worker.api_delete_survey(
            json_request("/api/surveys/survey-1", {}, method="DELETE"),
            make_env(),
            "survey-1",
        )

        assert response.status == 401

    async def test_delete_missing_survey_returns_404(self):
        env = make_env(db=MockDB([make_stmt(first=None)]))
        response = await worker.api_delete_survey(
            json_request("/api/surveys/missing", {}, method="DELETE", headers=_auth()),
            env,
            "missing",
        )

        assert response.status == 404

    async def test_delete_by_non_owner_returns_403(self):
        survey = MockRow(id="survey-1", user_id="owner-1")
        env = make_env(db=MockDB([make_stmt(first=survey)]))
        response = await worker.api_delete_survey(
            json_request("/api/surveys/survey-1", {}, method="DELETE", headers=_auth(uid="other-user")),
            env,
            "survey-1",
        )

        assert response.status == 403

    async def test_delete_owner_happy_path(self):
        survey = MockRow(id="survey-1", user_id="user-1")
        env = make_env(db=MockDB([make_stmt(first=survey)] + [make_stmt() for _ in range(5)]))
        response = await worker.api_delete_survey(
            json_request("/api/surveys/survey-1", {}, method="DELETE", headers=_auth()),
            env,
            "survey-1",
        )

        assert response.status == 200
        assert _parse(response)["message"] == "Survey deleted"


class TestSurveyResults:
    async def test_results_without_auth_returns_401(self):
        response = await worker.api_survey_results(
            json_request("/api/surveys/survey-1/results", {}, method="GET"),
            make_env(),
            "survey-1",
        )

        assert response.status == 401

    async def test_results_missing_survey_returns_404(self):
        env = make_env(db=MockDB([make_stmt(first=None)]))
        response = await worker.api_survey_results(
            json_request("/api/surveys/missing/results", {}, method="GET", headers=_auth()),
            env,
            "missing",
        )

        assert response.status == 404

    async def test_results_by_non_owner_returns_403(self):
        survey = MockRow(id="survey-1", title="Course Survey", user_id="owner-1")
        env = make_env(db=MockDB([make_stmt(first=survey)]))
        response = await worker.api_survey_results(
            json_request("/api/surveys/survey-1/results", {}, method="GET", headers=_auth(uid="other-user")),
            env,
            "survey-1",
        )

        assert response.status == 403

    async def test_results_owner_happy_path(self):
        survey = MockRow(id="survey-1", title="Course Survey", user_id="user-1")
        questions = [MockRow(id="q-1", text="Pick one", type="mcq", required=1, position=0)]
        choices = [
            MockRow(id="c-1", question_id="q-1", text="A", position=0),
            MockRow(id="c-2", question_id="q-1", text="B", position=1),
        ]
        responses = [MockRow(id="response-1")]
        answers = [MockRow(question_id="q-1", choice_id="c-1", text_value=None, response_id="response-1")]
        env = make_env(db=MockDB([
            make_stmt(first=survey),
            make_stmt(all_results=questions),
            make_stmt(all_results=choices),
            make_stmt(all_results=responses),
            make_stmt(all_results=answers),
        ]))

        response = await worker.api_survey_results(
            json_request("/api/surveys/survey-1/results", {}, method="GET", headers=_auth()),
            env,
            "survey-1",
        )

        assert response.status == 200
        data = _parse(response)
        assert data["title"] == "Course Survey"
        assert data["total_participants"] == 1
        assert data["results"][0]["data"] == [1, 0]
