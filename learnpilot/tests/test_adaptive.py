"""
Tests for learning.ai.adaptive.AdaptiveCurriculum
"""

from unittest.mock import MagicMock

from django.test import TestCase

from learning.ai.adaptive import AdaptiveCurriculum, _parse_json_response


class ParseJsonResponseTest(TestCase):
    def test_extracts_json_from_prose(self):
        raw = 'Here is the result: {"key": "value", "num": 42} – end.'
        result = _parse_json_response(raw, default={})
        self.assertEqual(result, {"key": "value", "num": 42})

    def test_returns_default_on_missing_json(self):
        result = _parse_json_response("No JSON here", default={"fallback": True})
        self.assertEqual(result, {"fallback": True})

    def test_returns_default_on_malformed_json(self):
        result = _parse_json_response("{bad json}", default={"fallback": True})
        self.assertEqual(result, {"fallback": True})


class AdaptiveCurriculumTest(TestCase):
    def _make_curriculum(self, ai_json_response: str):
        mock_client = MagicMock()
        mock_client.chat.return_value = ai_json_response
        return AdaptiveCurriculum(ai_client=mock_client)

    def test_generate_learning_path_returns_dict(self):
        ai_resp = '{"ordered_lesson_ids": [1, 2, 3], "rationale": "Start with basics."}'
        curriculum = self._make_curriculum(ai_resp)
        result = curriculum.generate_learning_path(
            topic_name="Python",
            skill_level="beginner",
            learning_style="visual",
            available_lessons=[
                {"id": 1, "title": "Variables", "type": "theory", "difficulty": "beginner"},
                {"id": 2, "title": "Loops", "type": "practice", "difficulty": "beginner"},
                {"id": 3, "title": "Functions", "type": "theory", "difficulty": "beginner"},
            ],
        )
        self.assertEqual(result["ordered_lesson_ids"], [1, 2, 3])
        self.assertEqual(result["rationale"], "Start with basics.")

    def test_generate_learning_path_falls_back_on_bad_ai_response(self):
        curriculum = self._make_curriculum("Sorry, I cannot generate a path.")
        result = curriculum.generate_learning_path("Python", "beginner", "visual", [])
        self.assertIn("ordered_lesson_ids", result)
        self.assertEqual(result["ordered_lesson_ids"], [])

    def test_recommend_next_lesson(self):
        ai_resp = '{"lesson_id": 5, "reason": "Next logical step."}'
        curriculum = self._make_curriculum(ai_resp)
        result = curriculum.recommend_next_lesson(
            topic_name="Python",
            completed_lessons=[{"title": "Variables"}],
            available_lessons=[{"id": 5, "title": "Loops", "type": "practice", "difficulty": "beginner"}],
            recent_scores=[0.8, 0.9],
        )
        self.assertEqual(result["lesson_id"], 5)

    def test_adapt_difficulty_returns_action(self):
        ai_resp = '{"new_difficulty": "intermediate", "action": "increase", "reasoning": "Scores are high."}'
        curriculum = self._make_curriculum(ai_resp)
        result = curriculum.adapt_difficulty(
            topic_name="Python",
            current_difficulty="beginner",
            recent_scores=[0.9, 0.95, 0.88],
        )
        self.assertEqual(result["action"], "increase")
        self.assertEqual(result["new_difficulty"], "intermediate")

    def test_generate_progress_insights_returns_string(self):
        curriculum = self._make_curriculum("You're doing great! Keep practising loops.")
        result = curriculum.generate_progress_insights(
            learner_name="Alice",
            topic_name="Python",
            progress_data=[{"lesson": "Variables", "score": 0.9, "completed": True, "attempts": 1}],
        )
        self.assertEqual(result, "You're doing great! Keep practising loops.")
