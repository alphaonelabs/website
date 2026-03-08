"""
Adaptive Curriculum module.

Uses Cloudflare Workers AI to personalise learning paths, adjust
difficulty in real time, and recommend the next best lesson based on
each learner's history and performance.
"""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING

from .cloudflare_ai import CloudflareAIClient, get_ai_client

if TYPE_CHECKING:
    from learning.models import AdaptivePath, LearnerProfile, Lesson, Topic

logger = logging.getLogger(__name__)

_CURRICULUM_SYSTEM_PROMPT = """You are an expert curriculum designer and learning \
scientist. You create highly personalised, adaptive learning paths that maximise \
learner engagement and knowledge retention. You base your recommendations on \
evidence-based learning principles such as spaced repetition, scaffolded \
instruction, and Bloom's taxonomy."""


class AdaptiveCurriculum:
    """
    AI-powered adaptive curriculum engine backed by Cloudflare Workers AI.

    Generates personalised learning paths, adjusts difficulty, and
    recommends the next lesson based on learner performance.
    """

    def __init__(self, ai_client: CloudflareAIClient | None = None):
        self.ai = ai_client or get_ai_client()

    # ------------------------------------------------------------------
    # Path generation
    # ------------------------------------------------------------------

    def generate_learning_path(
        self,
        topic_name: str,
        skill_level: str,
        learning_style: str,
        available_lessons: list[dict],
        goals: str = "",
    ) -> dict:
        """
        Generate a personalised ordered learning path.

        :param topic_name: The subject area (e.g., "Python Programming").
        :param skill_level: The learner's current level.
        :param learning_style: The learner's preferred modality.
        :param available_lessons: List of ``{id, title, type, difficulty}`` dicts.
        :param goals: Optional free-text learning goals.
        :returns: ``{ordered_lesson_ids: list[int], rationale: str}``
        """
        lesson_list = json.dumps(available_lessons, indent=2)
        goals_section = f"\nLearner goals: {goals}" if goals else ""

        prompt = f"""Create a personalised learning path for:
- Topic: {topic_name}
- Skill level: {skill_level}
- Learning style: {learning_style}{goals_section}

Available lessons (JSON):
{lesson_list}

Return a JSON object with exactly two keys:
{{
  "ordered_lesson_ids": [<list of integer lesson IDs in recommended order>],
  "rationale": "<2-3 sentence explanation of the path design>"
}}

Only include lessons that are appropriate for this learner. Order them from \
foundational to advanced."""

        raw = self.ai.chat(
            messages=[
                {"role": "system", "content": _CURRICULUM_SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ]
        )
        return _parse_json_response(raw, default={"ordered_lesson_ids": [], "rationale": raw})

    def recommend_next_lesson(
        self,
        topic_name: str,
        completed_lessons: list[dict],
        available_lessons: list[dict],
        recent_scores: list[float],
    ) -> dict:
        """
        Recommend the single best next lesson given the learner's history.

        :returns: ``{lesson_id: int | None, reason: str}``
        """
        completed_titles = [l["title"] for l in completed_lessons]
        avg_score = sum(recent_scores) / len(recent_scores) if recent_scores else 0.5

        prompt = f"""A learner is studying "{topic_name}".

Completed lessons: {json.dumps(completed_titles)}
Average recent score: {avg_score:.0%}
Available next lessons: {json.dumps(available_lessons, indent=2)}

Which single lesson should the learner tackle next? Return JSON:
{{
  "lesson_id": <integer id or null>,
  "reason": "<one sentence explanation>"
}}"""

        raw = self.ai.chat(
            messages=[
                {"role": "system", "content": _CURRICULUM_SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ]
        )
        return _parse_json_response(raw, default={"lesson_id": None, "reason": raw})

    # ------------------------------------------------------------------
    # Difficulty adaptation
    # ------------------------------------------------------------------

    def adapt_difficulty(
        self,
        topic_name: str,
        current_difficulty: str,
        recent_scores: list[float],
        struggles: list[str] | None = None,
    ) -> dict:
        """
        Recommend a difficulty adjustment based on recent performance.

        :returns: ``{new_difficulty: str, reasoning: str, action: str}``
        """
        avg = sum(recent_scores) / len(recent_scores) if recent_scores else 0.5
        struggle_text = ""
        if struggles:
            struggle_text = f"\nTopics the learner struggled with: {', '.join(struggles)}"

        prompt = f"""A learner studying "{topic_name}" at {current_difficulty} difficulty \
has achieved an average score of {avg:.0%} over their last {len(recent_scores)} attempt(s).{struggle_text}

Should the difficulty change? Respond with JSON:
{{
  "new_difficulty": "<beginner | intermediate | advanced>",
  "action": "<maintain | increase | decrease>",
  "reasoning": "<one sentence>"
}}"""

        raw = self.ai.chat(
            messages=[
                {"role": "system", "content": _CURRICULUM_SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ]
        )
        return _parse_json_response(
            raw,
            default={"new_difficulty": current_difficulty, "action": "maintain", "reasoning": raw},
        )

    # ------------------------------------------------------------------
    # Feedback & insights
    # ------------------------------------------------------------------

    def generate_progress_insights(
        self,
        learner_name: str,
        topic_name: str,
        progress_data: list[dict],
    ) -> str:
        """
        Produce a human-readable progress report with actionable insights.

        :param progress_data: List of ``{lesson, score, completed, attempts}`` dicts.
        """
        prompt = f"""Analyse {learner_name}'s learning progress in "{topic_name}":

{json.dumps(progress_data, indent=2)}

Write a concise progress report (4–6 sentences) that:
1. Summarises overall performance.
2. Identifies strengths.
3. Pinpoints areas needing improvement.
4. Recommends a concrete next action."""

        return self.ai.chat(
            messages=[
                {"role": "system", "content": _CURRICULUM_SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ]
        )


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

def _parse_json_response(raw: str, default: dict) -> dict:
    """
    Extract the first JSON object from *raw* text.

    Falls back to *default* if parsing fails.
    """
    # Find first '{' and last '}'
    start = raw.find("{")
    end = raw.rfind("}")
    if start == -1 or end == -1 or end <= start:
        logger.warning("Could not find JSON in AI response: %s", raw[:200])
        return default
    try:
        return json.loads(raw[start : end + 1])
    except json.JSONDecodeError as exc:
        logger.warning("Failed to parse JSON from AI response (%s): %s", exc, raw[:200])
        return default


def get_adaptive_curriculum(ai_client: CloudflareAIClient | None = None) -> AdaptiveCurriculum:
    """Return a configured :class:`AdaptiveCurriculum` instance."""
    return AdaptiveCurriculum(ai_client=ai_client)
