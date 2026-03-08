"""
Poetry generation handler — uses Cloudflare Workers AI LLM to write poems.

Model: @cf/meta/llama-3.1-8b-instruct
"""

from workers import Response

_TEXT_MODEL = "@cf/meta/llama-3.1-8b-instruct"

_FORM_GUIDES = {
    "sonnet": (
        "a 14-line Shakespearean sonnet (three quatrains + couplet), "
        "iambic pentameter, ABAB CDCD EFEF GG rhyme scheme"
    ),
    "haiku": "a traditional 5-7-5 syllable haiku (3 lines only)",
    "free": "free verse with evocative imagery, varied line lengths, no strict rhyme",
    "ballad": "a narrative ballad with alternating 8/6 syllable lines, ABCB rhyme scheme",
    "ode": "a lyric ode in 3+ stanzas, elevated diction, apostrophe to the subject",
    "limerick": "a humorous 5-line AABBA limerick with anapestic meter",
}

_TONE_GUIDES = {
    "romantic": "tender, passionate, longing, sensory imagery of warmth and beauty",
    "melancholic": "bittersweet, elegiac, quiet grief, introspective",
    "joyful": "celebratory, light, vivid colors, exuberant language",
    "philosophical": "contemplative, universal questions, paradox, wisdom",
    "mysterious": "ambiguous, shadowy imagery, unanswered questions, eerie",
    "hopeful": "optimistic, forward-looking, imagery of light and growth",
}

_SYSTEM_PROMPT = """You are a celebrated poet laureate with mastery of many poetic forms.
Reply ONLY with valid JSON (no markdown fences). The JSON must contain exactly:
  "title"  : (string) a short evocative title
  "poem"   : (string) the full poem text, lines separated by \\n
  "form"   : (string) the poetic form used
  "notes"  : (string) 1-2 sentences of craft commentary
Do not include any text outside the JSON object."""


async def handle_poetry_generate(env, body: dict) -> Response:
    """Generate a poem based on a theme or subject prompt.

    Expected body keys:
        prompt (str, required): Theme, subject, or first line inspiration.
        form   (str, optional): Poetic form — key from ``_FORM_GUIDES``.
        tone   (str, optional): Emotional tone — key from ``_TONE_GUIDES``.
    """
    prompt = (body.get("prompt") or "").strip()
    if not prompt:
        return Response.json(
            {"success": False, "error": "prompt is required"},
            status=400,
        )

    form = (body.get("form") or "free").lower()
    tone = (body.get("tone") or "").lower()

    form_guide = _FORM_GUIDES.get(form, _FORM_GUIDES["free"])
    tone_guide = _TONE_GUIDES.get(tone, "")

    tone_fragment = f" Tone: {tone_guide}." if tone_guide else ""
    user_message = (
        f'Write {form_guide} about: "{prompt}".{tone_fragment}'
    )

    response = await env.AI.run(
        _TEXT_MODEL,
        {
            "messages": [
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": user_message},
            ],
            "max_tokens": 512,
        },
    )

    raw_text = _extract_text(response)
    poem_data = _parse_json_safe(raw_text)

    return Response.json(
        {
            "success": True,
            "form": form,
            "tone": tone or "unspecified",
            "model": _TEXT_MODEL,
            "data": poem_data,
        }
    )


def _extract_text(response) -> str:
    """Extract the text string from various Workers AI response shapes."""
    if isinstance(response, str):
        return response
    if isinstance(response, dict):
        return response.get("response") or response.get("output") or ""
    try:
        return str(response.response)
    except Exception:
        return str(response)


def _parse_json_safe(text: str) -> dict:
    """Try to extract a JSON object from the model output; fall back gracefully."""
    import json
    import re

    text = re.sub(r"```(?:json)?\s*", "", text).strip().rstrip("`").strip()
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass

    return {"raw": text, "error": "Model output was not valid JSON"}
