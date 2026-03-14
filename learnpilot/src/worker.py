# LearnPilot AI Worker
#
# A Cloudflare Python Worker that exposes an AI tutoring API backed
# by Cloudflare Workers AI. Deploy with:
#
#   npx wrangler deploy
#
# The worker uses the Workers AI binding (env.AI) to run inference
# on Cloudflare's global edge network, providing low-latency responses.
#
# Endpoints:
#   POST /ai/chat       – continue a tutoring conversation
#   POST /ai/explain    – explain a concept at the learner's level
#   POST /ai/practice   – generate a practice question
#   POST /ai/evaluate   – evaluate a learner's answer
#   POST /ai/path       – generate a personalised learning path
#   POST /ai/progress   – produce personalised progress insights
#   GET  /health        – liveness check

import json


async def on_fetch(request, env):
    """Entry point for all incoming HTTP requests."""
    url = request.url
    method = request.method

    # CORS preflight
    if method == "OPTIONS":
        return _cors_response("", 204)

    # Route dispatch
    if "/ai/chat" in url and method == "POST":
        return await _handle_chat(request, env)

    if "/ai/explain" in url and method == "POST":
        return await _handle_explain(request, env)

    if "/ai/practice" in url and method == "POST":
        return await _handle_practice(request, env)

    if "/ai/evaluate" in url and method == "POST":
        return await _handle_evaluate(request, env)

    if "/ai/path" in url and method == "POST":
        return await _handle_generate_path(request, env)

    if "/ai/progress" in url and method == "POST":
        return await _handle_progress_insights(request, env)

    if "/ai/adapt" in url and method == "POST":
        return await _handle_adapt_difficulty(request, env)

    if "/ai/summary" in url and method == "POST":
        return await _handle_session_summary(request, env)

    if "/health" in url:
        return _cors_response(json.dumps({"status": "ok", "service": "learnpilot-ai"}), 200)

    return _cors_response(json.dumps({"error": "Not found"}), 404)


# ---------------------------------------------------------------------------
# Handlers
# ---------------------------------------------------------------------------

async def _handle_chat(request, env):
    """
    Continue a tutoring conversation.

    Request body:
        {
          "messages": [{"role": "user"|"assistant"|"system", "content": "…"}, …],
          "lesson_context": "…",   // optional
          "max_tokens": 1024        // optional
        }
    """
    try:
        body = await request.json()
    except Exception:
        return _error("Invalid JSON", 400)

    messages = body.get("messages", [])
    lesson_context = body.get("lesson_context", "")
    max_tokens = int(body.get("max_tokens", 1024))

    if not messages:
        return _error("messages is required", 400)

    system_prompt = _tutor_system_prompt(lesson_context)
    full_messages = [{"role": "system", "content": system_prompt}] + messages[-10:]

    result = await env.AI.run(
        "@cf/meta/llama-3.1-8b-instruct",
        {"messages": full_messages, "max_tokens": max_tokens},
    )
    response_text = result.get("response", "") if isinstance(result, dict) else ""
    return _cors_response(json.dumps({"response": response_text}), 200)


async def _handle_explain(request, env):
    """
    Explain a concept at the learner's level.

    Request body:
        {
          "concept": "recursion",
          "skill_level": "beginner",
          "learning_style": "visual",
          "context": "…"   // optional
        }
    """
    try:
        body = await request.json()
    except Exception:
        return _error("Invalid JSON", 400)

    concept = body.get("concept", "").strip()
    if not concept:
        return _error("concept is required", 400)

    skill_level = body.get("skill_level", "beginner")
    learning_style = body.get("learning_style", "visual")
    context = body.get("context", "")

    style_hints = {
        "visual": "Use text-described diagrams and visual metaphors.",
        "auditory": "Explain conversationally as if speaking aloud.",
        "reading": "Use numbered lists and clear definitions.",
        "kinesthetic": "Emphasise hands-on examples and step-by-step tasks.",
    }
    style_hint = style_hints.get(learning_style, "")
    context_section = f"\n\nLesson context:\n{context}" if context else ""

    prompt = (
        f"Explain the following concept to a {skill_level}-level learner.\n"
        f"Learning style: {learning_style}. {style_hint}\n\n"
        f"Concept: {concept}{context_section}\n\n"
        "Structure your response as:\n"
        "1. **Core Explanation** (2–4 sentences)\n"
        "2. **Analogy** – a memorable real-world comparison\n"
        "3. **Key Points** – 3–5 bullet points\n"
        "4. **Quick Example** – a short, concrete illustration"
    )

    result = await env.AI.run(
        "@cf/meta/llama-3.1-8b-instruct",
        {
            "messages": [
                {"role": "system", "content": _tutor_system_prompt()},
                {"role": "user", "content": prompt},
            ],
            "max_tokens": 1024,
        },
    )
    text = result.get("response", "") if isinstance(result, dict) else ""
    return _cors_response(json.dumps({"explanation": text}), 200)


async def _handle_practice(request, env):
    """
    Generate a practice question.

    Request body:
        {
          "topic": "…",
          "difficulty": "beginner|intermediate|advanced",
          "question_type": "open-ended|multiple-choice|true-false"
        }
    """
    try:
        body = await request.json()
    except Exception:
        return _error("Invalid JSON", 400)

    topic = body.get("topic", "").strip()
    if not topic:
        return _error("topic is required", 400)

    difficulty = body.get("difficulty", "beginner")
    question_type = body.get("question_type", "open-ended")

    prompt = (
        f"Generate a {difficulty}-level {question_type} practice question about: \"{topic}\"\n\n"
        "Format:\n"
        "- **Question:** <the question>\n"
        "- **Hint:** <a brief hint without giving the answer>\n"
        "- **Expected Answer:** <what a correct response covers>"
    )

    result = await env.AI.run(
        "@cf/meta/llama-3.1-8b-instruct",
        {
            "messages": [
                {"role": "system", "content": _tutor_system_prompt()},
                {"role": "user", "content": prompt},
            ],
            "max_tokens": 512,
        },
    )
    text = result.get("response", "") if isinstance(result, dict) else ""
    return _cors_response(json.dumps({"question": text}), 200)


async def _handle_evaluate(request, env):
    """
    Evaluate a learner's answer.

    Request body:
        {
          "question": "…",
          "answer": "…",
          "expected_answer": "…",  // optional
          "topic": "…"             // optional
        }
    """
    try:
        body = await request.json()
    except Exception:
        return _error("Invalid JSON", 400)

    question = body.get("question", "").strip()
    answer = body.get("answer", "").strip()
    if not question or not answer:
        return _error("question and answer are required", 400)

    expected = body.get("expected_answer", "")
    topic = body.get("topic", "")

    context = f"Topic: {topic}\n" if topic else ""
    expected_section = f"Expected answer context: {expected}\n" if expected else ""

    prompt = (
        f"{context}Question: {question}\n"
        f"{expected_section}\n"
        f"Learner's answer: {answer}\n\n"
        "Evaluate this answer and respond in exactly this format:\n"
        "SCORE: <number between 0.0 and 1.0>\n"
        "FEEDBACK: <2-3 sentences of constructive feedback>\n"
        "CORRECT_ANSWER: <a concise correct answer for reference>"
    )

    result = await env.AI.run(
        "@cf/meta/llama-3.1-8b-instruct",
        {
            "messages": [
                {"role": "system", "content": _tutor_system_prompt()},
                {"role": "user", "content": prompt},
            ],
            "max_tokens": 512,
        },
    )
    raw = result.get("response", "") if isinstance(result, dict) else ""
    parsed = _parse_evaluation(raw)
    return _cors_response(json.dumps(parsed), 200)


async def _handle_generate_path(request, env):
    """
    Generate a personalised learning path.

    Request body:
        {
          "topic": "…",
          "skill_level": "…",
          "learning_style": "…",
          "available_lessons": [{id, title, type, difficulty}, …],
          "goals": "…"  // optional
        }
    """
    try:
        body = await request.json()
    except Exception:
        return _error("Invalid JSON", 400)

    topic = body.get("topic", "").strip()
    skill_level = body.get("skill_level", "beginner")
    learning_style = body.get("learning_style", "visual")
    available_lessons = body.get("available_lessons", [])
    goals = body.get("goals", "")

    if not topic:
        return _error("topic is required", 400)

    goals_section = f"\nLearner goals: {goals}" if goals else ""
    lesson_list = json.dumps(available_lessons, indent=2)

    prompt = (
        f"Create a personalised learning path for:\n"
        f"- Topic: {topic}\n"
        f"- Skill level: {skill_level}\n"
        f"- Learning style: {learning_style}{goals_section}\n\n"
        f"Available lessons (JSON):\n{lesson_list}\n\n"
        'Return a JSON object with exactly two keys:\n'
        '{\n'
        '  "ordered_lesson_ids": [<list of integer lesson IDs in recommended order>],\n'
        '  "rationale": "<2-3 sentence explanation of the path design>"\n'
        '}\n\n'
        "Only include lessons appropriate for this learner."
    )

    result = await env.AI.run(
        "@cf/meta/llama-3.1-8b-instruct",
        {
            "messages": [
                {"role": "system", "content": _curriculum_system_prompt()},
                {"role": "user", "content": prompt},
            ],
            "max_tokens": 1024,
        },
    )
    raw = result.get("response", "") if isinstance(result, dict) else ""

    # Extract JSON from the response
    start = raw.find("{")
    end = raw.rfind("}")
    if start != -1 and end > start:
        try:
            path_data = json.loads(raw[start : end + 1])
            return _cors_response(json.dumps(path_data), 200)
        except (json.JSONDecodeError, ValueError):
            pass

    return _cors_response(json.dumps({"ordered_lesson_ids": [], "rationale": raw}), 200)


async def _handle_progress_insights(request, env):
    """
    Generate personalised progress insights for a learner.

    Request body:
        {
          "learner_name": "Alice",
          "topic": "Python Programming",
          "progress_data": [
            {"lesson": "Variables", "score": 0.9, "completed": true, "attempts": 1},
            …
          ]
        }

    Returns:
        {"insights": "<4-6 sentence progress report>"}
    """
    try:
        body = await request.json()
    except Exception:
        return _error("Invalid JSON", 400)

    learner_name = body.get("learner_name", "the learner")
    topic = body.get("topic", "").strip()
    progress_data = body.get("progress_data", [])

    if not topic:
        return _error("topic is required", 400)
    if not progress_data:
        return _error("progress_data is required", 400)

    prompt = (
        f"Analyse {learner_name}'s learning progress in \"{topic}\":\n\n"
        f"{json.dumps(progress_data, indent=2)}\n\n"
        "Write a concise progress report (4–6 sentences) that:\n"
        "1. Summarises overall performance.\n"
        "2. Identifies strengths.\n"
        "3. Pinpoints areas needing improvement.\n"
        "4. Recommends a concrete next action."
    )

    result = await env.AI.run(
        "@cf/meta/llama-3.1-8b-instruct",
        {
            "messages": [
                {"role": "system", "content": _curriculum_system_prompt()},
                {"role": "user", "content": prompt},
            ],
            "max_tokens": 512,
        },
    )
    text = result.get("response", "") if isinstance(result, dict) else ""
    return _cors_response(json.dumps({"insights": text}), 200)


async def _handle_adapt_difficulty(request, env):
    """
    Recommend a difficulty adjustment based on recent performance.

    Request body:
        {
          "topic": "Python Programming",
          "current_difficulty": "beginner",
          "recent_scores": [0.9, 0.85, 0.95],
          "struggles": ["recursion", "decorators"]   // optional
        }

    Returns:
        {"new_difficulty": "intermediate", "action": "increase", "reasoning": "…"}
    """
    try:
        body = await request.json()
    except Exception:
        return _error("Invalid JSON", 400)

    topic = body.get("topic", "").strip()
    current_difficulty = body.get("current_difficulty", "beginner")
    recent_scores = body.get("recent_scores", [])
    struggles = body.get("struggles", [])

    if not topic:
        return _error("topic is required", 400)
    if not recent_scores:
        return _error("recent_scores is required", 400)

    avg = sum(recent_scores) / len(recent_scores)
    struggle_text = ""
    if struggles:
        struggle_text = f"\nTopics the learner struggled with: {', '.join(struggles)}"

    prompt = (
        f"A learner studying \"{topic}\" at {current_difficulty} difficulty "
        f"has achieved an average score of {avg:.0%} over their last "
        f"{len(recent_scores)} attempt(s).{struggle_text}\n\n"
        "Should the difficulty change? Respond with JSON:\n"
        "{\n"
        '  "new_difficulty": "<beginner | intermediate | advanced>",\n'
        '  "action": "<maintain | increase | decrease>",\n'
        '  "reasoning": "<one sentence>"\n'
        "}"
    )

    result = await env.AI.run(
        "@cf/meta/llama-3.1-8b-instruct",
        {
            "messages": [
                {"role": "system", "content": _curriculum_system_prompt()},
                {"role": "user", "content": prompt},
            ],
            "max_tokens": 256,
        },
    )
    raw = result.get("response", "") if isinstance(result, dict) else ""

    start = raw.find("{")
    end = raw.rfind("}")
    if start != -1 and end > start:
        try:
            adapt_data = json.loads(raw[start : end + 1])
            return _cors_response(json.dumps(adapt_data), 200)
        except (json.JSONDecodeError, ValueError):
            pass

    return _cors_response(
        json.dumps(
            {
                "new_difficulty": current_difficulty,
                "action": "maintain",
                "reasoning": raw,
            }
        ),
        200,
    )


async def _handle_session_summary(request, env):
    """
    Summarise a completed tutoring session.

    Request body:
        {
          "lesson_title": "Python Variables",
          "conversation": [
            {"role": "user", "content": "…"},
            {"role": "assistant", "content": "…"},
            …
          ]
        }

    Returns:
        {"summary": "<3-5 sentence session summary with takeaways and next steps>"}
    """
    try:
        body = await request.json()
    except Exception:
        return _error("Invalid JSON", 400)

    lesson_title = body.get("lesson_title", "").strip()
    conversation = body.get("conversation", [])

    if not lesson_title:
        return _error("lesson_title is required", 400)
    if not conversation:
        return _error("conversation is required", 400)

    dialogue = "\n".join(
        f"{m.get('role', 'user').upper()}: {m.get('content', '')}"
        for m in conversation
        if m.get("role") != "system"
    )

    prompt = (
        f"A tutoring session on \"{lesson_title}\" just ended.\n"
        f"Conversation:\n{dialogue}\n\n"
        "Write a concise session summary (3–5 sentences) that:\n"
        "1. Highlights the key concepts covered.\n"
        "2. Notes any misconceptions that were corrected.\n"
        "3. Suggests 1–2 concrete next steps for the learner."
    )

    result = await env.AI.run(
        "@cf/meta/llama-3.1-8b-instruct",
        {
            "messages": [
                {"role": "system", "content": _tutor_system_prompt()},
                {"role": "user", "content": prompt},
            ],
            "max_tokens": 512,
        },
    )
    text = result.get("response", "") if isinstance(result, dict) else ""
    return _cors_response(json.dumps({"summary": text}), 200)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _tutor_system_prompt(lesson_context: str = "") -> str:
    base = (
        "You are LearnPilot, an expert AI tutor specialising in personalised education. "
        "You adapt your explanations to the learner's skill level and preferred learning style. "
        "You are patient, encouraging, and precise.\n\n"
        "Guidelines:\n"
        "- Keep explanations clear, structured, and appropriately concise.\n"
        "- Use analogies and real-world examples.\n"
        "- When a learner struggles, break concepts into smaller steps.\n"
        "- Acknowledge correct answers warmly; redirect incorrect ones gently.\n"
        "- Always end with an invitation to ask follow-up questions."
    )
    if lesson_context:
        base += f"\n\nCurrent lesson material:\n{lesson_context}"
    return base


def _curriculum_system_prompt() -> str:
    return (
        "You are an expert curriculum designer. "
        "You create highly personalised, adaptive learning paths that maximise "
        "learner engagement and knowledge retention based on evidence-based "
        "learning principles such as spaced repetition and scaffolded instruction."
    )


def _parse_evaluation(raw: str) -> dict:
    result = {"score": 0.5, "feedback": raw, "correct_answer": ""}
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


def _cors_response(body: str, status: int):
    headers = {
        "Content-Type": "application/json",
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type, Authorization",
    }
    return Response(body, status=status, headers=headers)


def _error(message: str, status: int):
    return _cors_response(json.dumps({"error": message}), status)
