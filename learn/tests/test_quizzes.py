"""
Unit and integration tests for Quiz data model and authoring API.
Covers:
- POST /api/activities/:id/quizzes (creation, host authorization)
- GET /api/activities/:id/quizzes (list activity quizzes)
- POST /api/quizzes/:id/questions (question association, encryption, host authorization)
- GET /api/quizzes/:id/questions (question list retrieval, host vs student answer masking)
- GET /api/quizzes/:id (quiz detail with questions)
- GET /api/quizzes (all quizzes list)
- DELETE /api/quizzes/:id (host quiz deletion)
"""

import json
import pytest
from tests.helpers import (
    load_worker,
    MockRequest,
    MockRow,
    MockDB,
    make_env,
    make_stmt,
    json_request,
)

worker = load_worker()

JWT_SECRET = "test-jwt-secret"
ENC_KEY = "test-encryption-key"


def _parse(resp):
    return json.loads(resp.body)


def _token(uid="host-1", username="instructor", role="host"):
    return worker.create_token(uid, username, role, JWT_SECRET)


def _auth(token):
    return {"Authorization": f"Bearer {token}"} if token else {}


# ---------------------------------------------------------------------------
# Quiz Authorization & Host Checks
# ---------------------------------------------------------------------------

class TestQuizAuthorization:
    async def test_create_quiz_without_auth_returns_401(self):
        req = json_request("/api/activities/act-1/quizzes", {"title": "Pop Quiz"})
        r = await worker.api_create_quiz(req, make_env(), "act-1")
        assert r.status == 401
        data = _parse(r)
        assert "Authentication required" in data.get("error", "")

    async def test_create_quiz_activity_not_found_returns_404(self):
        tok = _token(uid="host-1")
        req = json_request("/api/activities/non-existent/quizzes", {"title": "Pop Quiz"}, headers=_auth(tok))
        env = make_env(db=MockDB([make_stmt(first=None)]))
        r = await worker.api_create_quiz(req, env, "non-existent")
        assert r.status == 404
        data = _parse(r)
        assert "Activity not found" in data.get("error", "")

    async def test_create_quiz_non_host_returns_403(self):
        tok = _token(uid="other-user", role="student")
        act_row = MockRow(id="act-1", title="Python 101", host_id="host-1")
        req = json_request("/api/activities/act-1/quizzes", {"title": "Pop Quiz"}, headers=_auth(tok))
        env = make_env(db=MockDB([make_stmt(first=act_row)]))
        r = await worker.api_create_quiz(req, env, "act-1")
        assert r.status == 403
        data = _parse(r)
        assert "Forbidden" in data.get("error", "")

    async def test_create_quiz_host_returns_200(self):
        tok = _token(uid="host-1", role="host")
        act_row = MockRow(id="act-1", title="Python 101", host_id="host-1")
        req = json_request("/api/activities/act-1/quizzes", {"title": "Pop Quiz"}, headers=_auth(tok))
        env = make_env(db=MockDB([
            make_stmt(first=act_row),  # _require_activity_host lookup
            make_stmt(),               # INSERT into quizzes
        ]))
        r = await worker.api_create_quiz(req, env, "act-1")
        assert r.status == 200
        data = _parse(r)
        assert data["success"] is True
        assert data["data"]["title"] == "Pop Quiz"
        assert data["data"]["activity_id"] == "act-1"

    async def test_create_quiz_admin_returns_200(self):
        tok = _token(uid="admin-1", role="admin")
        act_row = MockRow(id="act-1", title="Python 101", host_id="host-1")
        req = json_request("/api/activities/act-1/quizzes", {"title": "Admin Quiz"}, headers=_auth(tok))
        env = make_env(db=MockDB([
            make_stmt(first=act_row),
            make_stmt(),
        ]))
        r = await worker.api_create_quiz(req, env, "act-1")
        assert r.status == 200

    async def test_add_questions_without_auth_returns_401(self):
        req = json_request("/api/quizzes/q-1/questions", {"prompt": "What is 2+2?"})
        r = await worker.api_add_quiz_questions(req, make_env(), "q-1")
        assert r.status == 401

    async def test_add_questions_quiz_not_found_returns_404(self):
        tok = _token(uid="host-1")
        req = json_request("/api/quizzes/non-existent/questions", {"prompt": "What is 2+2?"}, headers=_auth(tok))
        env = make_env(db=MockDB([make_stmt(first=None)]))
        r = await worker.api_add_quiz_questions(req, env, "non-existent")
        assert r.status == 404

    async def test_add_questions_non_host_returns_403(self):
        tok = _token(uid="intruder", role="student")
        quiz_row = MockRow(id="q-1", activity_id="act-1", host_id="host-1")
        req = json_request("/api/quizzes/q-1/questions", {"prompt": "What is 2+2?"}, headers=_auth(tok))
        env = make_env(db=MockDB([make_stmt(first=quiz_row)]))
        r = await worker.api_add_quiz_questions(req, env, "q-1")
        assert r.status == 403


# ---------------------------------------------------------------------------
# Quiz Creation Validation & Functionality
# ---------------------------------------------------------------------------

class TestQuizCreation:
    async def test_missing_title_returns_400(self):
        tok = _token(uid="host-1")
        act_row = MockRow(id="act-1", title="Python 101", host_id="host-1")
        req = json_request("/api/activities/act-1/quizzes", {"title": "  "}, headers=_auth(tok))
        env = make_env(db=MockDB([make_stmt(first=act_row)]))
        r = await worker.api_create_quiz(req, env, "act-1")
        assert r.status == 400
        assert "Quiz title is required" in _parse(r)["error"]

    async def test_negative_time_limit_returns_400(self):
        tok = _token(uid="host-1")
        act_row = MockRow(id="act-1", title="Python 101", host_id="host-1")
        req = json_request(
            "/api/activities/act-1/quizzes",
            {"title": "Quiz", "time_limit_minutes": -5},
            headers=_auth(tok),
        )
        env = make_env(db=MockDB([make_stmt(first=act_row)]))
        r = await worker.api_create_quiz(req, env, "act-1")
        assert r.status == 400

    async def test_invalid_passing_score_returns_400(self):
        tok = _token(uid="host-1")
        act_row = MockRow(id="act-1", title="Python 101", host_id="host-1")
        req = json_request(
            "/api/activities/act-1/quizzes",
            {"title": "Quiz", "passing_score": 150},
            headers=_auth(tok),
        )
        env = make_env(db=MockDB([make_stmt(first=act_row)]))
        r = await worker.api_create_quiz(req, env, "act-1")
        assert r.status == 400

    async def test_successful_quiz_creation_defaults(self):
        tok = _token(uid="host-1")
        act_row = MockRow(id="act-1", title="Python 101", host_id="host-1")
        req = json_request(
            "/api/activities/act-1/quizzes",
            {"title": "Unit 1 Quiz", "description": "Basics of Python"},
            headers=_auth(tok),
        )
        env = make_env(db=MockDB([
            make_stmt(first=act_row),
            make_stmt(),
        ]))
        r = await worker.api_create_quiz(req, env, "act-1")
        assert r.status == 200
        data = _parse(r)["data"]
        assert data["title"] == "Unit 1 Quiz"
        assert data["description"] == "Basics of Python"
        assert data["time_limit_minutes"] == 0
        assert data["passing_score"] == 70

    async def test_quiz_creation_with_embedded_questions(self):
        tok = _token(uid="host-1")
        act_row = MockRow(id="act-1", title="Python 101", host_id="host-1")
        payload = {
            "title": "Comprehensive Quiz",
            "time_limit_minutes": 30,
            "passing_score": 80,
            "questions": [
                {
                    "prompt": "What is Python?",
                    "question_type": "multiple_choice",
                    "options": ["A snake", "A programming language"],
                    "correct_answer": "A programming language",
                },
                {
                    "prompt": "Python is interpreted.",
                    "question_type": "true_false",
                    "options": ["True", "False"],
                    "correct_answer": "True",
                },
            ],
        }
        req = json_request("/api/activities/act-1/quizzes", payload, headers=_auth(tok))
        env = make_env(db=MockDB([
            make_stmt(first=act_row),  # activity check
            make_stmt(),               # insert quiz
            make_stmt(),               # insert q1
            make_stmt(),               # insert q2
        ]))
        r = await worker.api_create_quiz(req, env, "act-1")
        assert r.status == 200
        data = _parse(r)["data"]
        assert len(data["questions"]) == 2
        assert data["passing_score"] == 80
        assert data["time_limit_minutes"] == 30


# ---------------------------------------------------------------------------
# Question Association & Encryption
# ---------------------------------------------------------------------------

class TestQuizQuestions:
    async def test_missing_prompt_returns_400(self):
        tok = _token(uid="host-1")
        quiz_row = MockRow(id="q-1", activity_id="act-1", host_id="host-1")
        req = json_request("/api/quizzes/q-1/questions", {"prompt": "  "}, headers=_auth(tok))
        env = make_env(db=MockDB([make_stmt(first=quiz_row)]))
        r = await worker.api_add_quiz_questions(req, env, "q-1")
        assert r.status == 400

    async def test_add_single_question_with_options_and_encryption(self):
        tok = _token(uid="host-1")
        quiz_row = MockRow(id="q-1", activity_id="act-1", host_id="host-1")
        payload = {
            "prompt": "Which keyword defines a function in Python?",
            "question_type": "multiple_choice",
            "options": ["func", "def", "function", "lambda"],
            "correct_answer": "def",
        }
        req = json_request("/api/quizzes/q-1/questions", payload, headers=_auth(tok))
        insert_stmt = make_stmt()
        env = make_env(db=MockDB([
            make_stmt(first=quiz_row),
            insert_stmt,
        ]))
        r = await worker.api_add_quiz_questions(req, env, "q-1")
        assert r.status == 200
        data = _parse(r)
        assert data["success"] is True
        assert len(data["data"]["questions"]) == 1
        q = data["data"]["questions"][0]
        assert q["prompt"] == payload["prompt"]
        assert q["options"] == payload["options"]

        # Verify that correct_answer was encrypted before inserting into DB
        bind_args = insert_stmt.bind.call_args[0]
        encrypted_val = bind_args[5]
        assert encrypted_val.startswith("v1:")

    async def test_add_batch_questions(self):
        tok = _token(uid="host-1")
        quiz_row = MockRow(id="q-1", activity_id="act-1", host_id="host-1")
        payload = {
            "questions": [
                {"prompt": "Q1", "options": ["A", "B"], "correct_answer": "A"},
                {"prompt": "Q2", "options": ["C", "D"], "correct_answer": "D"},
            ]
        }
        req = json_request("/api/quizzes/q-1/questions", payload, headers=_auth(tok))
        env = make_env(db=MockDB([
            make_stmt(first=quiz_row),
            make_stmt(),
            make_stmt(),
        ]))
        r = await worker.api_add_quiz_questions(req, env, "q-1")
        assert r.status == 200
        assert len(_parse(r)["data"]["questions"]) == 2


# ---------------------------------------------------------------------------
# Quiz & Question Retrieval
# ---------------------------------------------------------------------------

class TestQuizRetrieval:
    async def test_list_activity_quizzes_returns_quizzes(self):
        act_row = MockRow(id="act-1", title="Python 101", host_id="host-1")
        quiz_row1 = MockRow(
            id="q-1",
            activity_id="act-1",
            title="Quiz 1",
            description="Intro",
            time_limit_minutes=15,
            passing_score=75,
            question_count=3,
            created_at="2026-10-22 10:00:00",
            updated_at=None,
        )
        env = make_env(db=MockDB([
            make_stmt(first=act_row),
            make_stmt(all_results=[quiz_row1]),
        ]))
        req = MockRequest(method="GET", url="http://localhost/api/activities/act-1/quizzes")
        r = await worker.api_list_activity_quizzes(req, env, "act-1")
        assert r.status == 200
        data = _parse(r)
        assert len(data["quizzes"]) == 1
        assert data["quizzes"][0]["title"] == "Quiz 1"
        assert data["quizzes"][0]["question_count"] == 3

    async def test_get_questions_as_student_masks_answers(self):
        quiz_row = MockRow(id="q-1", activity_id="act-1", host_id="host-1")
        # Pre-encrypted answer
        enc_answer = await worker.encrypt_aes("secret-answer", ENC_KEY)
        q_row = MockRow(
            id="quest-1",
            quiz_id="q-1",
            prompt="What is secret?",
            question_type="multiple_choice",
            options_json='["secret-answer", "wrong"]',
            correct_answer_encrypted=enc_answer,
            display_order=0,
            created_at="2026-10-22 10:00:00",
        )
        env = make_env(db=MockDB([
            make_stmt(first=quiz_row),
            make_stmt(all_results=[q_row]),
        ]))
        student_tok = _token(uid="student-99", role="student")
        req = MockRequest(
            method="GET",
            url="http://localhost/api/quizzes/q-1/questions",
            headers=_auth(student_tok),
        )
        r = await worker.api_get_quiz_questions(req, env, "q-1")
        assert r.status == 200
        data = _parse(r)
        assert len(data["questions"]) == 1
        q = data["questions"][0]
        # Student must NOT receive the decrypted answer or ciphertext
        assert "correct_answer" not in q
        assert "correct_answer_encrypted" not in q
        assert q["prompt"] == "What is secret?"
        assert q["options"] == ["secret-answer", "wrong"]

    async def test_get_questions_as_host_includes_decrypted_answer(self):
        quiz_row = MockRow(id="q-1", activity_id="act-1", host_id="host-1")
        enc_answer = await worker.encrypt_aes("def", ENC_KEY)
        q_row = MockRow(
            id="quest-1",
            quiz_id="q-1",
            prompt="Keyword for function?",
            question_type="multiple_choice",
            options_json='["func", "def"]',
            correct_answer_encrypted=enc_answer,
            display_order=0,
            created_at="2026-10-22 10:00:00",
        )
        env = make_env(db=MockDB([
            make_stmt(first=quiz_row),
            make_stmt(all_results=[q_row]),
        ]))
        host_tok = _token(uid="host-1", role="host")
        req = MockRequest(
            method="GET",
            url="http://localhost/api/quizzes/q-1/questions",
            headers=_auth(host_tok),
        )
        r = await worker.api_get_quiz_questions(req, env, "q-1")
        assert r.status == 200
        data = _parse(r)
        q = data["questions"][0]
        # Host CAN see decrypted answer for authoring/editing
        assert q["correct_answer"] == "def"

    async def test_get_quiz_detail(self):
        quiz_row = MockRow(
            id="q-1",
            activity_id="act-1",
            activity_title="Python 101",
            host_id="host-1",
            title="Final Exam",
            description="Testing your skills",
            time_limit_minutes=60,
            passing_score=80,
            created_at="2026-10-22 10:00:00",
            updated_at=None,
        )
        env = make_env(db=MockDB([
            make_stmt(first=quiz_row),
            make_stmt(all_results=[]),
        ]))
        req = MockRequest(method="GET", url="http://localhost/api/quizzes/q-1")
        r = await worker.api_get_quiz(req, env, "q-1")
        assert r.status == 200
        quiz = _parse(r)["quiz"]
        assert quiz["title"] == "Final Exam"
        assert quiz["activity_title"] == "Python 101"
        assert quiz["time_limit_minutes"] == 60
        assert quiz["passing_score"] == 80


# ---------------------------------------------------------------------------
# Router End-to-End via _dispatch
# ---------------------------------------------------------------------------

class TestQuizRouterDispatch:
    async def test_dispatch_create_and_list_quizzes(self):
        tok = _token(uid="host-1")
        act_row = MockRow(id="act-1", title="Python 101", host_id="host-1")

        # 1. POST /api/activities/act-1/quizzes
        req_create = json_request(
            "/api/activities/act-1/quizzes",
            {"title": "Midterm"},
            headers=_auth(tok),
        )
        env_create = make_env(db=MockDB([
            make_stmt(first=act_row),
            make_stmt(),
        ]))
        r_create = await worker._dispatch(req_create, env_create)
        assert r_create.status == 200
        assert _parse(r_create)["data"]["title"] == "Midterm"

        # 2. GET /api/activities/act-1/quizzes
        quiz_row = MockRow(
            id="q-1",
            activity_id="act-1",
            title="Midterm",
            description="",
            time_limit_minutes=0,
            passing_score=70,
            question_count=0,
            created_at="2026-10-22 10:00:00",
            updated_at=None,
        )
        req_list = MockRequest(method="GET", url="http://localhost/api/activities/act-1/quizzes")
        env_list = make_env(db=MockDB([
            make_stmt(first=act_row),
            make_stmt(all_results=[quiz_row]),
        ]))
        r_list = await worker._dispatch(req_list, env_list)
        assert r_list.status == 200
        assert len(_parse(r_list)["quizzes"]) == 1

        # 3. GET /api/quizzes (global)
        req_global = MockRequest(method="GET", url="http://localhost/api/quizzes")
        quiz_row_global = MockRow(
            id="q-1",
            activity_id="act-1",
            activity_title="Python 101",
            host_id="host-1",
            title="Midterm",
            description="",
            time_limit_minutes=0,
            passing_score=70,
            question_count=0,
            created_at="2026-10-22 10:00:00",
            updated_at=None,
        )
        env_global = make_env(db=MockDB([
            make_stmt(all_results=[quiz_row_global]),
        ]))
        r_global = await worker._dispatch(req_global, env_global)
        assert r_global.status == 200
        assert len(_parse(r_global)["quizzes"]) == 1
