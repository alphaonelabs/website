"""
Tests for learning.ai.tutor.IntelligentTutor
"""

from unittest.mock import MagicMock, patch

from django.test import TestCase

from learning.ai.tutor import IntelligentTutor, _parse_evaluation


class ParseEvaluationTest(TestCase):
    """Unit tests for the evaluation response parser."""

    def test_parses_well_formed_response(self):
        raw = (
            "SCORE: 0.85\n"
            "FEEDBACK: Great answer! You correctly identified the key concept.\n"
            "CORRECT_ANSWER: A function that calls itself with a base case."
        )
        result = _parse_evaluation(raw)
        self.assertAlmostEqual(result["score"], 0.85)
        self.assertIn("Great answer", result["feedback"])
        self.assertIn("base case", result["correct_answer"])

    def test_falls_back_on_malformed_score(self):
        raw = "SCORE: not-a-number\nFEEDBACK: OK"
        result = _parse_evaluation(raw)
        # Default score preserved
        self.assertEqual(result["score"], 0.5)
        self.assertEqual(result["feedback"], "OK")

    def test_returns_defaults_for_empty_response(self):
        result = _parse_evaluation("")
        self.assertEqual(result["score"], 0.5)
        self.assertEqual(result["correct_answer"], "")


class IntelligentTutorTest(TestCase):
    """Integration-level tests using a mock AI client."""

    def _make_tutor(self, ai_response="Mock AI response"):
        mock_client = MagicMock()
        mock_client.chat.return_value = ai_response
        return IntelligentTutor(ai_client=mock_client)

    def test_explain_concept_calls_chat(self):
        tutor = self._make_tutor("Here is the explanation.")
        result = tutor.explain_concept("recursion", skill_level="beginner")
        self.assertEqual(result, "Here is the explanation.")
        tutor.ai.chat.assert_called_once()

    def test_explain_concept_includes_skill_level_in_prompt(self):
        tutor = self._make_tutor()
        tutor.explain_concept("sorting", skill_level="advanced", learning_style="kinesthetic")
        call_args = tutor.ai.chat.call_args
        messages = call_args.kwargs.get("messages") or call_args[1].get("messages", [])
        full_text = " ".join(m["content"] for m in messages)
        self.assertIn("advanced", full_text)
        self.assertIn("sorting", full_text)

    def test_generate_practice_question(self):
        tutor = self._make_tutor("**Question:** What is a loop?")
        result = tutor.generate_practice_question("Python loops", difficulty="beginner")
        self.assertIn("Question", result)

    def test_evaluate_answer_returns_dict(self):
        raw = "SCORE: 0.9\nFEEDBACK: Excellent!\nCORRECT_ANSWER: Correct."
        tutor = self._make_tutor(raw)
        result = tutor.evaluate_answer("What is a variable?", "A named storage location")
        self.assertIsInstance(result, dict)
        self.assertIn("score", result)
        self.assertIn("feedback", result)

    def test_continue_conversation_passes_history(self):
        tutor = self._make_tutor("Follow-up response")
        history = [
            {"role": "user", "content": "Explain lists"},
            {"role": "assistant", "content": "Lists are ordered collections."},
        ]
        result = tutor.continue_conversation(history, "Give me an example")
        self.assertEqual(result, "Follow-up response")
        tutor.ai.chat.assert_called_once()

    def test_generate_session_summary(self):
        tutor = self._make_tutor("Session covered recursion and loops.")
        conversation = [
            {"role": "user", "content": "What is recursion?"},
            {"role": "assistant", "content": "Recursion is self-referential."},
        ]
        result = tutor.generate_session_summary(conversation, "Python Loops")
        self.assertEqual(result, "Session covered recursion and loops.")
