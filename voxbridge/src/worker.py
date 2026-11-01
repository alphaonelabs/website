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
import json
import traceback

from workers import Response, WorkerEntrypoint

# ---------------------------------------------------------------------------
# Cloudflare AI model identifiers
# ---------------------------------------------------------------------------
MODEL_WHISPER = "@cf/openai/whisper"
MODEL_LLAMA = "@cf/meta/llama-3.1-8b-instruct"
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
        body = await request.json()
        audio_b64: str = body.get("audio", "")
        if not audio_b64:
            return _json({"error": "Missing required field: 'audio'"}, status=400)

        audio_bytes = base64.b64decode(audio_b64)
        result = await env.AI.run(MODEL_WHISPER, {"audio": list(audio_bytes)})
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
        body = await request.json()
        audio_b64: str = body.get("audio", "")
        language: str = body.get("language", "ASL")

        if not audio_b64:
            return _json({"error": "Missing required field: 'audio'"}, status=400)

        # Step 1 – transcribe with Whisper
        audio_bytes = base64.b64decode(audio_b64)
        whisper_result = await env.AI.run(MODEL_WHISPER, {"audio": list(audio_bytes)})
        transcript = (
            whisper_result.get("text", "") if isinstance(whisper_result, dict) else getattr(whisper_result, "text", str(whisper_result))
        )

        # Step 2 – generate sign-language instructions with LLaMA
        llm_result = await env.AI.run(
            MODEL_LLAMA,
            {
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
            },
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
        body = await request.json()
        image_b64: str = body.get("image", "")
        if not image_b64:
            return _json({"error": "Missing required field: 'image'"}, status=400)

        # Strip data-URL prefix if present ("data:image/jpeg;base64,...")
        if "," in image_b64:
            image_b64 = image_b64.split(",", 1)[1]

        image_bytes = base64.b64decode(image_b64)

        # Step 1 – identify the gesture with the vision model
        vision_result = await env.AI.run(
            MODEL_VISION,
            {
                "image": list(image_bytes),
                "prompt": (
                    "This image shows a person making a hand gesture or sign-language sign. "
                    "Describe the hand shape, finger positions, and any movement visible. "
                    "What sign or word does this gesture represent?"
                ),
            },
        )
        gesture_description = (
            vision_result.get("description", "") if isinstance(vision_result, dict) else getattr(vision_result, "description", str(vision_result))
        )

        # Step 2 – refine with LLaMA for a clean speech output
        llm_result = await env.AI.run(
            MODEL_LLAMA,
            {
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
            },
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
        body = await request.json()
        image_b64: str = body.get("image", "")
        detail_level: str = body.get("detail_level", "standard")

        if not image_b64:
            return _json({"error": "Missing required field: 'image'"}, status=400)

        if "," in image_b64:
            image_b64 = image_b64.split(",", 1)[1]

        image_bytes = base64.b64decode(image_b64)

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
            {"image": list(image_bytes), "prompt": prompt},
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

    async def fetch(self, request: object, env: object, ctx: object) -> Response:  # noqa: ARG002
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
