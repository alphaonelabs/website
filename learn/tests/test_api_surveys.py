"""Tests for POST /api/surveys/:id/submit (api_submit_survey)."""

import base64
import json
from unittest.mock import AsyncMock, patch

from tests.helpers import (
    load_worker, MockRow, make_env, json_request, StrictD1, row_as_dict,
)

worker = load_worker()

JWT_SEC = "test-jwt-secret"
SURVEY_ID = "srv-1"
USER_ID = "uid-bob"


def _parse(resp):
    return json.loads(resp.body)


def _enc(val: str) -> str:
    return "v1:" + base64.b64encode(b"\x00" * 12 + val.encode()).decode()


def _auth(uid=USER_ID):
    return {"Authorization": f"Bearer {worker.create_token(uid, 'bob', 'member', JWT_SEC)}"}


def _survey_db(already_submitted=False, mcq_required=True, batch_error=None):
    survey = MockRow(
        id=SURVEY_ID, title="Course feedback", description="",
        user_id="uid-alice", created_at="2026-11-01", author_name=_enc("Alice"),
    )
    questions = [
        MockRow(id="q-mcq", text="Rate it", type="mcq", required=int(mcq_required), position=0),
        MockRow(id="q-text", text="Comments", type="text", required=0, position=1),
        MockRow(id="q-check", text="Topics", type="checkbox", required=0, position=2),
    ]
    choices = [
        MockRow(id="c1", question_id="q-mcq", text="Good", position=0),
        MockRow(id="c2", question_id="q-mcq", text="Bad", position=1),
        MockRow(id="c3", question_id="q-check", text="Python", position=0),
        MockRow(id="c4", question_id="q-check", text="SQL", position=1),
    ]

    def first(sql, args):
        if "FROM surveys s" in sql:
            return survey
        if "FROM survey_responses" in sql:
            return MockRow(id="resp-old") if already_submitted else None
        return None

    def all_(sql, args):
        if "FROM survey_choices" in sql:      # must be checked before survey_questions
            return choices
        if "FROM survey_questions" in sql:
            return questions
        return []

    return StrictD1(first=first, all_=all_, batch_error=batch_error)


def _req(answers, authed=True):
    return json_request(
        f"/api/surveys/{SURVEY_ID}/submit",
        {"answers": answers},
        headers=_auth() if authed else None,
    )


def _saved_answers(db):
    """Return (response_row, [answer_rows]) from the single recorded batch."""
    assert len(db.batches) == 1
    batch = db.batches[0]
    return row_as_dict(*batch[0]), [row_as_dict(sql, args) for sql, args in batch[1:]]


class TestSubmitSurveySaving:
    async def test_choice_answer_saves_null_text_value(self):
        db = _survey_db(mcq_required=False)
        r = await worker.api_submit_survey(_req({"q-mcq": "c1"}), make_env(db=db), SURVEY_ID)
        assert r.status == 200
        resp, answers = _saved_answers(db)
        assert resp["survey_id"] == SURVEY_ID and resp["user_id"] == USER_ID
        assert len(answers) == 1
        assert answers[0]["question_id"] == "q-mcq"
        assert answers[0]["choice_id"] == "c1"
        assert answers[0]["text_value"] is None
        assert answers[0]["response_id"] == resp["id"]

    async def test_text_answer_saves_null_choice_id_and_encrypted_text(self):
        db = _survey_db(mcq_required=False)
        r = await worker.api_submit_survey(
            _req({"q-text": "Great course"}), make_env(db=db), SURVEY_ID
        )
        assert r.status == 200
        _, answers = _saved_answers(db)
        assert len(answers) == 1
        assert answers[0]["question_id"] == "q-text"
        assert answers[0]["choice_id"] is None
        assert answers[0]["text_value"] == _enc("Great course")

    async def test_mixed_survey_saves_every_answer(self):
        db = _survey_db()
        r = await worker.api_submit_survey(
            _req({"q-mcq": "c2", "q-text": "Fine", "q-check": ["c3", "c4"]}),
            make_env(db=db), SURVEY_ID,
        )
        assert r.status == 200
        resp, answers = _saved_answers(db)
        assert len(answers) == 4
        assert all(a["response_id"] == resp["id"] for a in answers)
        checks = [a for a in answers if a["question_id"] == "q-check"]
        assert {a["choice_id"] for a in checks} == {"c3", "c4"}
        assert all(a["text_value"] is None for a in checks)


class TestSubmitSurveyValidation:
    async def test_requires_auth(self):
        db = _survey_db()
        r = await worker.api_submit_survey(_req({}, authed=False), make_env(db=db), SURVEY_ID)
        assert r.status == 401
        assert db.batches == []

    async def test_missing_required_answer_returns_400(self):
        db = _survey_db()
        r = await worker.api_submit_survey(_req({}), make_env(db=db), SURVEY_ID)
        assert r.status == 400
        assert db.batches == []

    async def test_invalid_choice_returns_400(self):
        db = _survey_db()
        r = await worker.api_submit_survey(_req({"q-mcq": "bogus"}), make_env(db=db), SURVEY_ID)
        assert r.status == 400
        assert db.batches == []

    async def test_already_submitted_returns_409(self):
        db = _survey_db(already_submitted=True)
        r = await worker.api_submit_survey(_req({"q-mcq": "c1"}), make_env(db=db), SURVEY_ID)
        assert r.status == 409
        assert db.batches == []


class TestSubmitSurveyDbErrors:
    async def test_unique_violation_returns_409(self):
        db = _survey_db(batch_error=Exception("UNIQUE constraint failed: survey_responses"))
        r = await worker.api_submit_survey(_req({"q-mcq": "c1"}), make_env(db=db), SURVEY_ID)
        assert r.status == 409

    async def test_other_batch_error_returns_500(self):
        db = _survey_db(batch_error=Exception("boom"))
        with patch.object(worker, "capture_exception", new=AsyncMock()) as cap:
            r = await worker.api_submit_survey(_req({"q-mcq": "c1"}), make_env(db=db), SURVEY_ID)
        assert r.status == 500
        cap.assert_awaited_once()