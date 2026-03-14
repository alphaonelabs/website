"""
Unit tests for src/worker.py helper functions.

These tests cover all pure-Python logic in the worker – the async handlers
are tested via mocked env.AI objects so they can run without a live
Cloudflare environment.
"""

import asyncio
import json
import sys
import types
import unittest
from unittest.mock import AsyncMock, MagicMock

# ---------------------------------------------------------------------------
# Shim: make the `Response` built-in available to worker.py without a real
# Cloudflare runtime. We define a minimal Response class and inject it into
# builtins before importing the module.
# ---------------------------------------------------------------------------

class Response:  # noqa: D101
    def __init__(self, body="", *, status=200, headers=None):
        self.body = body
        self.status = status
        self.headers = headers or {}


import builtins

builtins.Response = Response  # type: ignore[attr-defined]

# Now it is safe to import the worker module
sys.path.insert(0, "src")
import worker  # noqa: E402  (import after sys.path manipulation)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def run(coro):
    """Run a coroutine synchronously."""
    return asyncio.run(coro)


def _make_env(ai_response: dict) -> MagicMock:
    """Return a mock env whose AI.run returns *ai_response*."""
    env = MagicMock()
    env.AI.run = AsyncMock(return_value=ai_response)
    return env


def _make_request(method: str, url: str, body: dict | None = None) -> MagicMock:
    """Return a mock Request object."""
    req = MagicMock()
    req.method = method
    req.url = url
    if body is not None:
        req.json = AsyncMock(return_value=body)
    else:
        req.json = AsyncMock(side_effect=ValueError("no body"))
    return req


# ===========================================================================
# _parse_evaluation
# ===========================================================================

class TestParseEvaluation(unittest.TestCase):
    def test_parses_all_fields(self):
        raw = (
            "SCORE: 0.85\n"
            "FEEDBACK: Great answer, you covered the main points.\n"
            "CORRECT_ANSWER: A function that calls itself with a base case."
        )
        result = worker._parse_evaluation(raw)
        self.assertAlmostEqual(result["score"], 0.85)
        self.assertIn("Great answer", result["feedback"])
        self.assertIn("base case", result["correct_answer"])

    def test_falls_back_on_malformed_score(self):
        raw = "SCORE: not-a-number\nFEEDBACK: Okay"
        result = worker._parse_evaluation(raw)
        self.assertEqual(result["score"], 0.5)
        self.assertEqual(result["feedback"], "Okay")

    def test_returns_defaults_for_empty_string(self):
        result = worker._parse_evaluation("")
        self.assertEqual(result["score"], 0.5)
        self.assertEqual(result["feedback"], "")
        self.assertEqual(result["correct_answer"], "")

    def test_score_field_only(self):
        result = worker._parse_evaluation("SCORE: 1.0")
        self.assertAlmostEqual(result["score"], 1.0)

    def test_correct_answer_field_only(self):
        result = worker._parse_evaluation("CORRECT_ANSWER: Recursion terminates at the base case.")
        self.assertIn("base case", result["correct_answer"])


# ===========================================================================
# _tutor_system_prompt
# ===========================================================================

class TestTutorSystemPrompt(unittest.TestCase):
    def test_contains_learnpilot(self):
        prompt = worker._tutor_system_prompt()
        self.assertIn("LearnPilot", prompt)

    def test_appends_lesson_context(self):
        prompt = worker._tutor_system_prompt("Variables store values.")
        self.assertIn("Variables store values.", prompt)
        self.assertIn("lesson material", prompt)

    def test_no_context_by_default(self):
        prompt = worker._tutor_system_prompt()
        self.assertNotIn("lesson material", prompt)


# ===========================================================================
# _curriculum_system_prompt
# ===========================================================================

class TestCurriculumSystemPrompt(unittest.TestCase):
    def test_contains_curriculum_keywords(self):
        prompt = worker._curriculum_system_prompt()
        self.assertIn("curriculum", prompt.lower())
        self.assertIn("learning", prompt.lower())


# ===========================================================================
# _cors_response / _error
# ===========================================================================

class TestCorsResponse(unittest.TestCase):
    def test_status_code_is_preserved(self):
        resp = worker._cors_response('{"ok": true}', 201)
        self.assertEqual(resp.status, 201)

    def test_cors_headers_present(self):
        resp = worker._cors_response("{}", 200)
        self.assertIn("Access-Control-Allow-Origin", resp.headers)
        self.assertEqual(resp.headers["Access-Control-Allow-Origin"], "*")

    def test_error_returns_json_with_error_key(self):
        resp = worker._error("Bad request", 400)
        self.assertEqual(resp.status, 400)
        data = json.loads(resp.body)
        self.assertIn("error", data)
        self.assertEqual(data["error"], "Bad request")


# ===========================================================================
# on_fetch – routing
# ===========================================================================

class TestRouting(unittest.TestCase):
    def test_options_returns_204(self):
        req = _make_request("OPTIONS", "https://example.com/ai/chat")
        resp = run(worker.on_fetch(req, MagicMock()))
        self.assertEqual(resp.status, 204)

    def test_health_returns_200(self):
        req = _make_request("GET", "https://example.com/health")
        resp = run(worker.on_fetch(req, MagicMock()))
        self.assertEqual(resp.status, 200)
        data = json.loads(resp.body)
        self.assertEqual(data["status"], "ok")

    def test_unknown_route_returns_404(self):
        req = _make_request("GET", "https://example.com/unknown")
        resp = run(worker.on_fetch(req, MagicMock()))
        self.assertEqual(resp.status, 404)


# ===========================================================================
# /ai/chat handler
# ===========================================================================

class TestHandleChat(unittest.TestCase):
    def test_returns_ai_response(self):
        env = _make_env({"response": "Recursion is when a function calls itself."})
        req = _make_request(
            "POST",
            "https://w.example.com/ai/chat",
            {"messages": [{"role": "user", "content": "Explain recursion"}]},
        )
        resp = run(worker.on_fetch(req, env))
        self.assertEqual(resp.status, 200)
        data = json.loads(resp.body)
        self.assertIn("Recursion", data["response"])

    def test_missing_messages_returns_400(self):
        env = _make_env({})
        req = _make_request("POST", "https://w.example.com/ai/chat", {})
        resp = run(worker.on_fetch(req, env))
        self.assertEqual(resp.status, 400)

    def test_invalid_json_returns_400(self):
        env = _make_env({})
        req = _make_request("POST", "https://w.example.com/ai/chat")
        resp = run(worker.on_fetch(req, env))
        self.assertEqual(resp.status, 400)


# ===========================================================================
# /ai/explain handler
# ===========================================================================

class TestHandleExplain(unittest.TestCase):
    def test_returns_explanation(self):
        env = _make_env({"response": "Recursion means a function calls itself."})
        req = _make_request(
            "POST",
            "https://w.example.com/ai/explain",
            {"concept": "recursion", "skill_level": "beginner"},
        )
        resp = run(worker.on_fetch(req, env))
        self.assertEqual(resp.status, 200)
        data = json.loads(resp.body)
        self.assertIn("explanation", data)

    def test_missing_concept_returns_400(self):
        env = _make_env({})
        req = _make_request("POST", "https://w.example.com/ai/explain", {"skill_level": "beginner"})
        resp = run(worker.on_fetch(req, env))
        self.assertEqual(resp.status, 400)

    def test_learning_style_included_in_prompt(self):
        env = _make_env({"response": "Hands-on example …"})
        req = _make_request(
            "POST",
            "https://w.example.com/ai/explain",
            {"concept": "loops", "skill_level": "intermediate", "learning_style": "kinesthetic"},
        )
        resp = run(worker.on_fetch(req, env))
        self.assertEqual(resp.status, 200)
        # Verify the AI.run call contained the style hint
        call_payload = env.AI.run.call_args[0][1]
        full_text = " ".join(m["content"] for m in call_payload["messages"])
        self.assertIn("kinesthetic", full_text.lower())


# ===========================================================================
# /ai/practice handler
# ===========================================================================

class TestHandlePractice(unittest.TestCase):
    def test_returns_question(self):
        env = _make_env({"response": "**Question:** What is a for loop?"})
        req = _make_request(
            "POST",
            "https://w.example.com/ai/practice",
            {"topic": "Python loops", "difficulty": "beginner"},
        )
        resp = run(worker.on_fetch(req, env))
        self.assertEqual(resp.status, 200)
        data = json.loads(resp.body)
        self.assertIn("question", data)

    def test_missing_topic_returns_400(self):
        env = _make_env({})
        req = _make_request("POST", "https://w.example.com/ai/practice", {"difficulty": "beginner"})
        resp = run(worker.on_fetch(req, env))
        self.assertEqual(resp.status, 400)


# ===========================================================================
# /ai/evaluate handler
# ===========================================================================

class TestHandleEvaluate(unittest.TestCase):
    def test_returns_score_and_feedback(self):
        ai_raw = "SCORE: 0.9\nFEEDBACK: Excellent!\nCORRECT_ANSWER: A named storage location."
        env = _make_env({"response": ai_raw})
        req = _make_request(
            "POST",
            "https://w.example.com/ai/evaluate",
            {"question": "What is a variable?", "answer": "A box that holds a value"},
        )
        resp = run(worker.on_fetch(req, env))
        self.assertEqual(resp.status, 200)
        data = json.loads(resp.body)
        self.assertAlmostEqual(float(data["score"]), 0.9)
        self.assertIn("feedback", data)
        self.assertIn("correct_answer", data)

    def test_missing_question_returns_400(self):
        env = _make_env({})
        req = _make_request("POST", "https://w.example.com/ai/evaluate", {"answer": "something"})
        resp = run(worker.on_fetch(req, env))
        self.assertEqual(resp.status, 400)

    def test_missing_answer_returns_400(self):
        env = _make_env({})
        req = _make_request(
            "POST", "https://w.example.com/ai/evaluate", {"question": "What is X?"}
        )
        resp = run(worker.on_fetch(req, env))
        self.assertEqual(resp.status, 400)


# ===========================================================================
# /ai/path handler
# ===========================================================================

class TestHandleGeneratePath(unittest.TestCase):
    def test_returns_ordered_lesson_ids(self):
        ai_json = '{"ordered_lesson_ids": [3, 1, 2], "rationale": "Start simple."}'
        env = _make_env({"response": ai_json})
        req = _make_request(
            "POST",
            "https://w.example.com/ai/path",
            {
                "topic": "Python",
                "skill_level": "beginner",
                "learning_style": "visual",
                "available_lessons": [
                    {"id": 1, "title": "Variables", "type": "theory", "difficulty": "beginner"},
                    {"id": 2, "title": "Loops", "type": "practice", "difficulty": "beginner"},
                    {"id": 3, "title": "Intro", "type": "theory", "difficulty": "beginner"},
                ],
            },
        )
        resp = run(worker.on_fetch(req, env))
        self.assertEqual(resp.status, 200)
        data = json.loads(resp.body)
        self.assertIn("ordered_lesson_ids", data)
        self.assertEqual(data["ordered_lesson_ids"], [3, 1, 2])

    def test_falls_back_gracefully_on_malformed_json(self):
        env = _make_env({"response": "Sorry, cannot generate path."})
        req = _make_request(
            "POST",
            "https://w.example.com/ai/path",
            {"topic": "Python", "skill_level": "beginner", "learning_style": "visual", "available_lessons": []},
        )
        resp = run(worker.on_fetch(req, env))
        self.assertEqual(resp.status, 200)
        data = json.loads(resp.body)
        self.assertIn("ordered_lesson_ids", data)
        self.assertEqual(data["ordered_lesson_ids"], [])

    def test_missing_topic_returns_400(self):
        env = _make_env({})
        req = _make_request(
            "POST",
            "https://w.example.com/ai/path",
            {"skill_level": "beginner", "available_lessons": []},
        )
        resp = run(worker.on_fetch(req, env))
        self.assertEqual(resp.status, 400)


# ===========================================================================
# /ai/progress handler
# ===========================================================================

class TestHandleProgressInsights(unittest.TestCase):
    def test_returns_insights(self):
        env = _make_env({"response": "You're making steady progress. Keep practising loops."})
        req = _make_request(
            "POST",
            "https://w.example.com/ai/progress",
            {
                "learner_name": "Alice",
                "topic": "Python",
                "progress_data": [
                    {"lesson": "Variables", "score": 0.9, "completed": True, "attempts": 1}
                ],
            },
        )
        resp = run(worker.on_fetch(req, env))
        self.assertEqual(resp.status, 200)
        data = json.loads(resp.body)
        self.assertIn("insights", data)

    def test_missing_topic_returns_400(self):
        env = _make_env({})
        req = _make_request(
            "POST",
            "https://w.example.com/ai/progress",
            {"learner_name": "Alice", "progress_data": [{"lesson": "x", "score": 1.0}]},
        )
        resp = run(worker.on_fetch(req, env))
        self.assertEqual(resp.status, 400)

    def test_missing_progress_data_returns_400(self):
        env = _make_env({})
        req = _make_request(
            "POST",
            "https://w.example.com/ai/progress",
            {"learner_name": "Alice", "topic": "Python"},
        )
        resp = run(worker.on_fetch(req, env))
        self.assertEqual(resp.status, 400)


# ===========================================================================
# /ai/adapt handler
# ===========================================================================

class TestHandleAdaptDifficulty(unittest.TestCase):
    def test_returns_adapt_recommendation(self):
        ai_json = '{"new_difficulty": "intermediate", "action": "increase", "reasoning": "High scores."}'
        env = _make_env({"response": ai_json})
        req = _make_request(
            "POST",
            "https://w.example.com/ai/adapt",
            {"topic": "Python", "current_difficulty": "beginner", "recent_scores": [0.9, 0.95]},
        )
        resp = run(worker.on_fetch(req, env))
        self.assertEqual(resp.status, 200)
        data = json.loads(resp.body)
        self.assertEqual(data["action"], "increase")
        self.assertEqual(data["new_difficulty"], "intermediate")

    def test_missing_topic_returns_400(self):
        env = _make_env({})
        req = _make_request(
            "POST",
            "https://w.example.com/ai/adapt",
            {"current_difficulty": "beginner", "recent_scores": [0.9]},
        )
        resp = run(worker.on_fetch(req, env))
        self.assertEqual(resp.status, 400)

    def test_missing_recent_scores_returns_400(self):
        env = _make_env({})
        req = _make_request(
            "POST",
            "https://w.example.com/ai/adapt",
            {"topic": "Python", "current_difficulty": "beginner"},
        )
        resp = run(worker.on_fetch(req, env))
        self.assertEqual(resp.status, 400)


# ===========================================================================
# /ai/summary handler
# ===========================================================================

class TestHandleSessionSummary(unittest.TestCase):
    def test_returns_summary(self):
        env = _make_env({"response": "The session covered variables and loops."})
        req = _make_request(
            "POST",
            "https://w.example.com/ai/summary",
            {
                "lesson_title": "Python Variables",
                "conversation": [
                    {"role": "user", "content": "What is a variable?"},
                    {"role": "assistant", "content": "A variable is a named storage location."},
                ],
            },
        )
        resp = run(worker.on_fetch(req, env))
        self.assertEqual(resp.status, 200)
        data = json.loads(resp.body)
        self.assertIn("summary", data)

    def test_missing_lesson_title_returns_400(self):
        env = _make_env({})
        req = _make_request(
            "POST",
            "https://w.example.com/ai/summary",
            {"conversation": [{"role": "user", "content": "Hi"}]},
        )
        resp = run(worker.on_fetch(req, env))
        self.assertEqual(resp.status, 400)

    def test_missing_conversation_returns_400(self):
        env = _make_env({})
        req = _make_request(
            "POST",
            "https://w.example.com/ai/summary",
            {"lesson_title": "Python Variables"},
        )
        resp = run(worker.on_fetch(req, env))
        self.assertEqual(resp.status, 400)

    def test_system_messages_excluded_from_dialogue(self):
        env = _make_env({"response": "Good session."})
        req = _make_request(
            "POST",
            "https://w.example.com/ai/summary",
            {
                "lesson_title": "Test",
                "conversation": [
                    {"role": "system", "content": "SECRET INSTRUCTIONS"},
                    {"role": "user", "content": "Hello"},
                    {"role": "assistant", "content": "Hi!"},
                ],
            },
        )
        resp = run(worker.on_fetch(req, env))
        self.assertEqual(resp.status, 200)
        # Verify the AI was NOT passed the system message content in the user prompt
        call_payload = env.AI.run.call_args[0][1]
        user_prompt = call_payload["messages"][-1]["content"]
        self.assertNotIn("SECRET INSTRUCTIONS", user_prompt)


if __name__ == "__main__":
    unittest.main()
