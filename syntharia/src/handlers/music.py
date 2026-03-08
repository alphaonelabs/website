"""
Music composition handler — generates ABC notation and chord progressions
via Cloudflare Workers AI LLM.

Cloudflare Workers AI does not currently provide a dedicated music-generation
model, so we use a large-language model to produce structured music notation:

  * ABC notation — a plain-text format renderable by abcjs in the browser.
  * Chord progressions with rhythm suggestions.
  * Descriptive notes about instrumentation and mood.

Model: @cf/meta/llama-3.1-8b-instruct
"""

from workers import Response

_TEXT_MODEL = "@cf/meta/llama-3.1-8b-instruct"

_GENRE_GUIDES = {
    "classical": "Western classical music, voice-leading, counterpoint",
    "jazz": "jazz harmony, extended chords, swing rhythm, improvisation",
    "electronic": "electronic music, arpeggiated synths, driving bass, 4/4 dance",
    "ambient": "slow, evolving textures, drones, minimalist, meditative",
    "folk": "folk / acoustic, pentatonic melody, fingerpicking guitar",
    "cinematic": "film score, orchestral, dramatic dynamics, leitmotif",
}

_SYSTEM_PROMPT = """You are an expert music composer and music theorist.
When asked to compose a piece, reply ONLY with valid JSON (no markdown fences).
The JSON must contain exactly these keys:
  "title"        : (string) the composition title
  "abc_notation" : (string) a valid ABC notation block starting with X:1
  "chords"       : (array of strings) the chord progression, e.g. ["Am","F","C","G"]
  "tempo"        : (integer) beats per minute
  "time_signature": (string) e.g. "4/4"
  "key"          : (string) e.g. "A minor"
  "style_notes"  : (string) 2-3 sentences about mood, instrumentation, and performance tips
Do not include any text outside the JSON object."""


async def handle_music_compose(env, body: dict) -> Response:
    """Compose a piece of music described by a natural-language prompt.

    Expected body keys:
        prompt (str, required): Description of the desired music.
        genre  (str, optional): One of the keys in ``_GENRE_GUIDES``.
        tempo  (int, optional): Desired BPM (will be overridden by the model).
    """
    prompt = (body.get("prompt") or "").strip()
    if not prompt:
        return Response.json(
            {"success": False, "error": "prompt is required"},
            status=400,
        )

    genre = (body.get("genre") or "classical").lower()
    genre_guide = _GENRE_GUIDES.get(genre, _GENRE_GUIDES["classical"])
    requested_tempo = body.get("tempo")

    tempo_hint = f" Target tempo: {requested_tempo} BPM." if requested_tempo else ""
    user_message = (
        f"Compose a {genre} piece ({genre_guide}) based on this description: "
        f'"{prompt}".{tempo_hint}'
    )

    response = await env.AI.run(
        _TEXT_MODEL,
        {
            "messages": [
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": user_message},
            ],
            "max_tokens": 1024,
        },
    )

    raw_text = _extract_text(response)
    music_data = _parse_json_safe(raw_text)

    return Response.json(
        {
            "success": True,
            "genre": genre,
            "model": _TEXT_MODEL,
            "data": music_data,
        }
    )


def _extract_text(response) -> str:
    """Extract the text string from various Workers AI response shapes."""
    if isinstance(response, str):
        return response
    if isinstance(response, dict):
        return response.get("response") or response.get("output") or ""
    # JS proxy / object — try attribute access
    try:
        return str(response.response)
    except Exception:
        return str(response)


def _parse_json_safe(text: str) -> dict:
    """Try to extract a JSON object from the model output; fall back gracefully."""
    import json
    import re

    # Strip markdown code fences if present
    text = re.sub(r"```(?:json)?\s*", "", text).strip().rstrip("`").strip()

    # Find the first {...} block
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass

    # Return raw text wrapped so the frontend can still display it
    return {"raw": text, "error": "Model output was not valid JSON"}
