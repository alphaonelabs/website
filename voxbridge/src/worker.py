"""
VoxBridge – AI-powered accessibility and communication toolkit.

Cloudflare Python Worker providing four AI-driven features:
  • Real-time captioning   (audio  → text via Whisper)
  • Speech-to-sign         (audio  → sign-language instructions via Whisper + LLaMA)
  • Sign-to-speech         (image  → interpreted text via Vision + LLaMA)
  • Visual scene description (image → accessible description via Vision model)
"""

from __future__ import annotations

import base64
import binascii
import json
import traceback

from workers import Response, WorkerEntrypoint

try:  # Workers AI needs plain JS objects; a bare Python dict arrives as a JS Map.
    from js import Object
    from pyodide.ffi import to_js as _to_js

    def _js(value):
        return _to_js(value, dict_converter=Object.fromEntries)
except ImportError:  # local tests run outside Pyodide
    def _js(value):
        return value


def _py(value):
    """request.json() on the raw Workers request returns a JS object; make it a dict."""
    return value.to_py() if hasattr(value, "to_py") else value

# ---------------------------------------------------------------------------
# Cloudflare AI model identifiers
# ---------------------------------------------------------------------------
MODEL_WHISPER = "@cf/openai/whisper"
MODEL_LLAMA = "@cf/meta/llama-3.3-70b-instruct-fp8-fast"
MODEL_VISION = "@cf/unum/uform-gen2-qwen-500m"

# ---------------------------------------------------------------------------
# Response helpers
# ---------------------------------------------------------------------------

_CORS = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type",
}


def _json(data: dict, *, status: int = 200) -> Response:
    """Return a JSON response with CORS headers."""
    headers = {**_CORS, "Content-Type": "application/json"}
    return Response(json.dumps(data), status=status, headers=headers)


def _options() -> Response:
    """Return a CORS pre-flight response."""
    return Response("", status=204, headers=_CORS)


def _server_error(exc: Exception) -> Response:
    """Log exception details server-side and return a generic 500 response."""
    traceback.print_exc()
    return _json({"error": "An internal error occurred. Please try again."}, status=500)


# Decoded payload caps before sending bytes to Workers AI.
MAX_AUDIO_BYTES = 10 * 1024 * 1024  # 10 MB
MAX_IMAGE_BYTES = 5 * 1024 * 1024  # 5 MB


async def _read_json_object(request: object) -> tuple[dict | None, Response | None]:
    """Parse a JSON object body, or return a 400 response for client mistakes."""
    try:
        body = _py(await request.json())
    except Exception:  # noqa: BLE001 — invalid JSON / Workers parse errors
        return None, _json({"error": "Request body must be valid JSON"}, status=400)
    if not isinstance(body, dict):
        return None, _json({"error": "Request body must be a JSON object"}, status=400)
    return body, None


def _decode_base64(
    value: object,
    *,
    max_bytes: int,
    allow_data_url: bool = False,
) -> tuple[bytes | None, Response | None]:
    """Decode base64 (optionally stripping a data-URL prefix) with size limits."""
    if not isinstance(value, str) or not value:
        return None, _json({"error": "Missing or invalid base64 field"}, status=400)
    raw = value
    if allow_data_url and "," in raw:
        raw = raw.split(",", 1)[1]
    try:
        data = base64.b64decode(raw, validate=True)
    except (binascii.Error, ValueError):
        return None, _json({"error": "Invalid base64 encoding"}, status=400)
    if len(data) > max_bytes:
        return None, _json(
            {"error": f"Decoded payload exceeds {max_bytes} byte limit"},
            status=413,
        )
    return data, None


# ---------------------------------------------------------------------------
# Route handlers
# ---------------------------------------------------------------------------


async def _health(_request: object, _env: object) -> Response:
    """GET /api/health – liveness probe."""
    return _json({"status": "ok", "service": "voxbridge"})


async def _caption(request: object, env: object) -> Response:
    """
    POST /api/caption

    Body (JSON):
        audio: str  – Base64-encoded audio bytes (WAV/MP3/WebM)

    Returns:
        text: str   – Transcript produced by Whisper
    """
    try:
        body, err = await _read_json_object(request)
        if err is not None:
            return err
        audio_bytes, err = _decode_base64(body.get("audio", ""), max_bytes=MAX_AUDIO_BYTES)
        if err is not None:
            return err

        result = await env.AI.run(MODEL_WHISPER, _js({"audio": list(audio_bytes)}))
        transcript = result.get("text", "") if isinstance(result, dict) else getattr(result, "text", str(result))

        return _json({"text": transcript, "model": MODEL_WHISPER})
    except Exception as exc:  # noqa: BLE001
        return _server_error(exc)


async def _speech_to_sign(request: object, env: object) -> Response:
    """
    POST /api/speech-to-sign

    Body (JSON):
        audio:    str  – Base64-encoded audio bytes
        language: str  – Sign language variant (default: "ASL")

    Returns:
        transcript:   str – Spoken words transcribed from audio
        sign_language: str – Requested sign language variant
        instructions: str – Step-by-step signing instructions
    """
    try:
        body, err = await _read_json_object(request)
        if err is not None:
            return err
        language: str = body.get("language", "ASL") if isinstance(body.get("language", "ASL"), str) else "ASL"
        audio_bytes, err = _decode_base64(body.get("audio", ""), max_bytes=MAX_AUDIO_BYTES)
        if err is not None:
            return err

        # Step 1 – transcribe with Whisper
        whisper_result = await env.AI.run(MODEL_WHISPER, _js({"audio": list(audio_bytes)}))
        transcript = (
            whisper_result.get("text", "") if isinstance(whisper_result, dict) else getattr(whisper_result, "text", str(whisper_result))
        )

        # Step 2 – generate sign-language instructions with LLaMA
        llm_result = await env.AI.run(
            MODEL_LLAMA,
            _js({
                "messages": [
                    {
                        "role": "system",
                        "content": (
                            f"You are an expert {language} interpreter. "
                            "Convert spoken text into clear, step-by-step hand-sign descriptions. "
                            "For each key word provide the hand shape, palm orientation, location, and movement."
                        ),
                    },
                    {
                        "role": "user",
                        "content": (
                            f"Convert this spoken sentence into {language} sign instructions:\n\n"
                            f'"{transcript}"'
                        ),
                    },
                ],
                "max_tokens": 1024,
            }),
        )
        instructions = (
            llm_result.get("response", "") if isinstance(llm_result, dict) else getattr(llm_result, "response", str(llm_result))
        )

        return _json(
            {
                "transcript": transcript,
                "sign_language": language,
                "instructions": instructions,
                "models": [MODEL_WHISPER, MODEL_LLAMA],
            }
        )
    except Exception as exc:  # noqa: BLE001
        return _server_error(exc)


async def _sign_to_speech(request: object, env: object) -> Response:
    """
    POST /api/sign-to-speech

    Body (JSON):
        image: str – Base64-encoded image (JPEG/PNG) or a data-URL

    Returns:
        gesture_description: str – Raw vision-model analysis
        speech_text:         str – Interpreted spoken equivalent
    """
    try:
        body, err = await _read_json_object(request)
        if err is not None:
            return err
        image_bytes, err = _decode_base64(
            body.get("image", ""), max_bytes=MAX_IMAGE_BYTES, allow_data_url=True
        )
        if err is not None:
            return err

        # Step 1 – identify the gesture with the vision model
        vision_result = await env.AI.run(
            MODEL_VISION,
            _js({
                "image": list(image_bytes),
                "prompt": (
                    "This image shows a person making a hand gesture or sign-language sign. "
                    "Describe the hand shape, finger positions, and any movement visible. "
                    "What sign or word does this gesture represent?"
                ),
            }),
        )
        gesture_description = (
            vision_result.get("description", "") if isinstance(vision_result, dict) else getattr(vision_result, "description", str(vision_result))
        )

        # Step 2 – refine with LLaMA for a clean speech output
        llm_result = await env.AI.run(
            MODEL_LLAMA,
            _js({
                "messages": [
                    {
                        "role": "system",
                        "content": (
                            "You are an expert sign-language interpreter. "
                            "Given a description of a sign-language gesture, provide the most likely "
                            "spoken word or phrase it represents. Reply with just the word or short phrase."
                        ),
                    },
                    {
                        "role": "user",
                        "content": (
                            f"Gesture description: {gesture_description}\n\n"
                            "What word or phrase is this person signing?"
                        ),
                    },
                ],
                "max_tokens": 256,
            }),
        )
        speech_text = (
            llm_result.get("response", "") if isinstance(llm_result, dict) else getattr(llm_result, "response", str(llm_result))
        )

        return _json(
            {
                "gesture_description": gesture_description,
                "speech_text": speech_text,
                "models": [MODEL_VISION, MODEL_LLAMA],
            }
        )
    except Exception as exc:  # noqa: BLE001
        return _server_error(exc)


async def _visual_scene(request: object, env: object) -> Response:
    """
    POST /api/visual-scene

    Body (JSON):
        image:        str  – Base64-encoded image or data-URL
        detail_level: str  – "brief" | "standard" | "detailed"  (default: "standard")

    Returns:
        description:  str – Accessible scene description
        detail_level: str – Echo of the requested detail level
    """
    try:
        body, err = await _read_json_object(request)
        if err is not None:
            return err
        detail_level: str = body.get("detail_level", "standard") if isinstance(body.get("detail_level", "standard"), str) else "standard"
        image_bytes, err = _decode_base64(
            body.get("image", ""), max_bytes=MAX_IMAGE_BYTES, allow_data_url=True
        )
        if err is not None:
            return err

        prompts = {
            "brief": "Briefly describe this image in one sentence.",
            "standard": (
                "Describe this scene clearly for accessibility purposes. "
                "Include the main subjects, setting, and important details."
            ),
            "detailed": (
                "Provide a comprehensive, detailed description of this scene for someone "
                "who cannot see it. Include objects, people, colours, spatial relationships, "
                "lighting, mood, and any visible text. Be as descriptive as possible."
            ),
        }
        prompt = prompts.get(detail_level, prompts["standard"])

        vision_result = await env.AI.run(
            MODEL_VISION,
            _js({"image": list(image_bytes), "prompt": prompt}),
        )
        description = (
            vision_result.get("description", "") if isinstance(vision_result, dict) else getattr(vision_result, "description", str(vision_result))
        )

        return _json(
            {
                "description": description,
                "detail_level": detail_level,
                "model": MODEL_VISION,
            }
        )
    except Exception as exc:  # noqa: BLE001
        return _server_error(exc)


# ---------------------------------------------------------------------------
# Router
# ---------------------------------------------------------------------------

_ROUTES: dict[tuple[str, str], object] = {
    ("GET", "/api/health"): _health,
    ("POST", "/api/caption"): _caption,
    ("POST", "/api/speech-to-sign"): _speech_to_sign,
    ("POST", "/api/sign-to-speech"): _sign_to_speech,
    ("POST", "/api/visual-scene"): _visual_scene,
}


# ---------------------------------------------------------------------------
# Worker entry point
# ---------------------------------------------------------------------------


class VoxBridgeWorker(WorkerEntrypoint):
    """Cloudflare Python Worker entry point."""

    async def fetch(self, request: object) -> Response:
        env = self.env
        method: str = request.method
        url: str = request.url
        # Extract path (everything between host and query string)
        path = url.split("?")[0]
        path = "/" + "/".join(path.split("/")[3:]) if "/" in url else "/"
        if not path.startswith("/"):
            path = "/" + path

        # CORS pre-flight
        if method == "OPTIONS":
            return _options()

        handler = _ROUTES.get((method, path))
        if handler is not None:
            return await handler(request, env)

        # Fall back to static assets served by the ASSETS binding
        if hasattr(env, "ASSETS"):
            return await env.ASSETS.fetch(request)

        return _json({"error": "Not found", "path": path}, status=404)


async def on_fetch(request, env, ctx=None):
    """Module-level handler: this compatibility date dispatches to on_fetch, not entrypoint classes."""
    entry = VoxBridgeWorker.__new__(VoxBridgeWorker)
    entry.env = env
    entry.ctx = ctx
    return await entry.fetch(request)
