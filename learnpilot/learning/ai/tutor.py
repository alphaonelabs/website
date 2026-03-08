"""
Intelligent Tutor module.

Uses Cloudflare Workers AI to provide adaptive explanations, generate
practice questions, evaluate learner answers, and produce personalised
feedback – all in real time.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from .cloudflare_ai import CloudflareAIClient, get_ai_client

if TYPE_CHECKING:
    from learning.models import Lesson, LearnerProfile

logger = logging.getLogger(__name__)

# System prompt that frames the AI as an educational tutor
_TUTOR_SYSTEM_PROMPT = """You are LearnPilot, an expert AI tutor specialising in \
personalised education. You adapt your explanations to the learner's skill level \
and preferred learning style. You are patient, encouraging, and precise.

Guidelines:
- Keep explanations clear, structured, and appropriately concise.
- Use analogies and real-world examples to illuminate abstract concepts.
- When a learner struggles, break concepts into smaller steps.
- Acknowledge correct answers warmly; redirect incorrect ones gently.
- Ask clarifying questions when the learner's intent is ambiguous.
- Always end tutoring responses with an invitation to ask follow-up questions."""


class IntelligentTutor:
    """
    AI-powered tutoring engine backed by Cloudflare Workers AI.

    Each public method builds a targeted prompt and calls the AI model,
    returning the generated text directly.
    """

    def __init__(self, ai_client: CloudflareAIClient | None = None):
        self.ai = ai_client or get_ai_client()

    # ------------------------------------------------------------------
    # Core tutoring operations
    # ------------------------------------------------------------------

    def explain_concept(
        self,
        concept: str,
        skill_level: str = "beginner",
        learning_style: str = "visual",
        context: str = "",
    ) -> str:
        """
        Generate a personalised explanation of *concept*.

        :param concept: The topic or term to explain.
        :param skill_level: One of ``beginner``, ``intermediate``, ``advanced``.
        :param learning_style: Learner's preferred style (visual, reading, kinesthetic …).
        :param context: Optional extra context (e.g., surrounding lesson material).
        """
        style_hints = {
            "visual": "Use diagrams described in text, flowcharts, and visual metaphors.",
            "auditory": "Explain as if speaking aloud; use rhythm and narrative flow.",
            "reading": "Provide structured text with numbered lists and definitions.",
            "kinesthetic": "Emphasise hands-on examples, exercises, and step-by-step tasks.",
        }
        style_hint = style_hints.get(learning_style, "")
        context_section = f"\n\nLesson context:\n{context}" if context else ""

        prompt = f"""Explain the following concept to a {skill_level}-level learner.
Learning style: {learning_style}. {style_hint}

Concept: {concept}{context_section}

Structure your response as:
1. **Core Explanation** – what it is and why it matters (2–4 sentences).
2. **Analogy** – a memorable real-world comparison.
3. **Key Points** – 3–5 bullet points summarising what to remember.
4. **Quick Example** – a short, concrete illustration."""

        return self.ai.chat(
            messages=[
                {"role": "system", "content": _TUTOR_SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ]
        )

    def generate_practice_question(
        self,
        topic: str,
        difficulty: str = "beginner",
        question_type: str = "open-ended",
    ) -> str:
        """
        Generate a practice question to reinforce learning.

        :param topic: The topic to test.
        :param difficulty: ``beginner``, ``intermediate``, or ``advanced``.
        :param question_type: ``open-ended``, ``multiple-choice``, or ``true-false``.
        """
        prompt = f"""Generate a {difficulty}-level {question_type} practice question about:
"{topic}"

Format:
- **Question:** <the question>
- **Hint:** <a brief hint without giving the answer>
- **Expected Answer:** <what a correct response covers>"""

        return self.ai.chat(
            messages=[
                {"role": "system", "content": _TUTOR_SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ]
        )

    def evaluate_answer(
        self,
        question: str,
        learner_answer: str,
        expected_answer: str = "",
        topic: str = "",
    ) -> dict[str, str | float]:
        """
        Evaluate a learner's answer and return a score plus feedback.

        Returns a dict with keys ``score`` (0.0–1.0), ``feedback``, and
        ``correct_answer``.
        """
        context = f"Topic: {topic}\n" if topic else ""
        expected = f"Expected answer context: {expected_answer}\n" if expected_answer else ""
        prompt = f"""{context}Question: {question}
{expected}
Learner's answer: {learner_answer}

Evaluate this answer and respond in exactly this format:
SCORE: <number between 0.0 and 1.0>
FEEDBACK: <2-3 sentences of constructive feedback>
CORRECT_ANSWER: <a concise correct answer for reference>"""

        raw = self.ai.chat(
            messages=[
                {"role": "system", "content": _TUTOR_SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ]
        )
        return _parse_evaluation(raw)

    def continue_conversation(
        self,
        history: list[dict[str, str]],
        user_message: str,
        lesson_context: str = "",
    ) -> str:
        """
        Continue an ongoing tutoring conversation.

        :param history: Prior ``[{role, content}, …]`` messages.
        :param user_message: The learner's latest message.
        :param lesson_context: The current lesson's content for grounding.
        """
        system = _TUTOR_SYSTEM_PROMPT
        if lesson_context:
            system += f"\n\nCurrent lesson material:\n{lesson_context}"

        messages = [{"role": "system", "content": system}]
        messages.extend(history[-10:])  # keep last 10 turns for context window
        messages.append({"role": "user", "content": user_message})

        return self.ai.chat(messages=messages)

    def generate_session_summary(
        self,
        conversation: list[dict[str, str]],
        lesson_title: str,
    ) -> str:
        """
        Summarise a completed tutoring session for the learner.

        Returns a brief summary with key takeaways and recommended next steps.
        """
        dialogue = "\n".join(
            f"{m['role'].upper()}: {m['content']}" for m in conversation if m["role"] != "system"
        )
        prompt = f"""A tutoring session on "{lesson_title}" just ended.
Conversation:
{dialogue}

Write a concise session summary (3–5 sentences) that:
1. Highlights the key concepts covered.
2. Notes any misconceptions that were corrected.
3. Suggests 1–2 concrete next steps for the learner."""

        return self.ai.chat(
            messages=[
                {"role": "system", "content": _TUTOR_SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ]
        )


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

def _parse_evaluation(raw: str) -> dict[str, str | float]:
    """Parse the structured evaluation response from the AI."""
    result: dict[str, str | float] = {
        "score": 0.5,
        "feedback": raw,
        "correct_answer": "",
    }
    for line in raw.splitlines():
        line = line.strip()
        if line.startswith("SCORE:"):
            try:
                result["score"] = float(line.split(":", 1)[1].strip())
            except ValueError:
                pass
        elif line.startswith("FEEDBACK:"):
            result["feedback"] = line.split(":", 1)[1].strip()
        elif line.startswith("CORRECT_ANSWER:"):
            result["correct_answer"] = line.split(":", 1)[1].strip()
    return result


def get_tutor(ai_client: CloudflareAIClient | None = None) -> IntelligentTutor:
    """Return a configured :class:`IntelligentTutor` instance."""
    return IntelligentTutor(ai_client=ai_client)
