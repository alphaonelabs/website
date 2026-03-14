"""
Unit tests for VoxBridge worker helper logic.

These tests exercise pure-Python helpers that do not require the
Cloudflare Workers runtime.  AI binding calls are mocked so that the
full handler code-paths can be validated without deploying the worker.
"""

from __future__ import annotations

import base64
import json
import sys
import types
import unittest
from unittest.mock import AsyncMock


# ---------------------------------------------------------------------------
# Minimal stubs for Cloudflare-specific modules so we can import worker.py
# ---------------------------------------------------------------------------

def _install_cf_stubs() -> None:
    """Inject minimal stubs for `workers` before importing the module under test."""
    if "workers" in sys.modules:
        return

    workers_mod = types.ModuleType("workers")

    class Response:
        def __init__(self, body="", *, status=200, headers=None):
            self.body = body
            self.status = status
            self.headers = headers or {}

        def json(self):
            return json.loads(self.body)

    class WorkerEntrypoint:
        pass

    workers_mod.Response = Response
    workers_mod.WorkerEntrypoint = WorkerEntrypoint
    sys.modules["workers"] = workers_mod


_install_cf_stubs()

# ---------------------------------------------------------------------------
# Import module under test (pytest.ini adds src/ to sys.path automatically)
# ---------------------------------------------------------------------------

import worker  # noqa: E402  (side-effect import after stubs)

Response = sys.modules["workers"].Response


# ---------------------------------------------------------------------------
# Helper: make a mock Cloudflare Request-like object
# ---------------------------------------------------------------------------

class _MockRequest:
    def __init__(self, method="GET", url="https://example.com/api/health", body=None):
        self.method = method
        self.url = url
        self._body = body or {}

    async def json(self):
        return self._body


class _MockEnv:
    def __init__(self, ai_results=None):
        self.AI = AsyncMock()
        if ai_results:
            self.AI.run.side_effect = ai_results


class _MockCtx:
    pass


# ---------------------------------------------------------------------------
# Tests for module constants
# ---------------------------------------------------------------------------

class TestModelConstants(unittest.TestCase):
    def test_model_names_are_strings(self):
        self.assertIsInstance(worker.MODEL_WHISPER, str)
        self.assertIsInstance(worker.MODEL_LLAMA, str)
        self.assertIsInstance(worker.MODEL_VISION, str)

    def test_whisper_model_identifier(self):
        self.assertIn("whisper", worker.MODEL_WHISPER.lower())

    def test_llama_model_identifier(self):
        self.assertIn("llama", worker.MODEL_LLAMA.lower())

    def test_vision_model_identifier(self):
        # model name should be a Cloudflare-style path
        self.assertTrue(worker.MODEL_VISION.startswith("@cf/"))


# ---------------------------------------------------------------------------
# Tests for _json / _options helpers
# ---------------------------------------------------------------------------

class TestResponseHelpers(unittest.TestCase):
    def test_json_returns_response(self):
        resp = worker._json({"hello": "world"})
        self.assertIsInstance(resp, Response)

    def test_json_default_status_200(self):
        resp = worker._json({"ok": True})
        self.assertEqual(resp.status, 200)

    def test_json_custom_status(self):
        resp = worker._json({"error": "bad"}, status=400)
        self.assertEqual(resp.status, 400)

    def test_json_body_is_valid_json(self):
        data = {"key": "value", "num": 42}
        resp = worker._json(data)
        parsed = json.loads(resp.body)
        self.assertEqual(parsed, data)

    def test_json_cors_header(self):
        resp = worker._json({})
        self.assertIn("Access-Control-Allow-Origin", resp.headers)
        self.assertEqual(resp.headers["Access-Control-Allow-Origin"], "*")

    def test_options_status_204(self):
        resp = worker._options()
        self.assertEqual(resp.status, 204)

    def test_options_cors_allow_methods(self):
        resp = worker._options()
        self.assertIn("POST", resp.headers.get("Access-Control-Allow-Methods", ""))


# ---------------------------------------------------------------------------
# Tests for route table
# ---------------------------------------------------------------------------

class TestRoutes(unittest.TestCase):
    def test_health_route_exists(self):
        self.assertIn(("GET", "/api/health"), worker._ROUTES)

    def test_caption_route_exists(self):
        self.assertIn(("POST", "/api/caption"), worker._ROUTES)

    def test_speech_to_sign_route_exists(self):
        self.assertIn(("POST", "/api/speech-to-sign"), worker._ROUTES)

    def test_sign_to_speech_route_exists(self):
        self.assertIn(("POST", "/api/sign-to-speech"), worker._ROUTES)

    def test_visual_scene_route_exists(self):
        self.assertIn(("POST", "/api/visual-scene"), worker._ROUTES)

    def test_all_handlers_are_callable(self):
        for key, handler in worker._ROUTES.items():
            with self.subTest(route=key):
                self.assertTrue(callable(handler))


# ---------------------------------------------------------------------------
# Tests for _health handler
# ---------------------------------------------------------------------------

class TestHealthHandler(unittest.IsolatedAsyncioTestCase):
    async def test_health_returns_ok(self):
        req = _MockRequest()
        resp = await worker._health(req, _MockEnv())
        data = json.loads(resp.body)
        self.assertEqual(data["status"], "ok")
        self.assertEqual(data["service"], "voxbridge")

    async def test_health_status_200(self):
        req = _MockRequest()
        resp = await worker._health(req, _MockEnv())
        self.assertEqual(resp.status, 200)


# ---------------------------------------------------------------------------
# Tests for _caption handler
# ---------------------------------------------------------------------------

class TestCaptionHandler(unittest.IsolatedAsyncioTestCase):
    def _audio_b64(self, content: bytes = b"fake-audio") -> str:
        return base64.b64encode(content).decode()

    async def test_caption_returns_text(self):
        env = _MockEnv()
        env.AI.run.return_value = {"text": "hello world"}
        req = _MockRequest(method="POST", body={"audio": self._audio_b64()})
        resp = await worker._caption(req, env)
        data = json.loads(resp.body)
        self.assertEqual(data["text"], "hello world")

    async def test_caption_missing_audio_returns_400(self):
        req = _MockRequest(method="POST", body={})
        resp = await worker._caption(req, _MockEnv())
        self.assertEqual(resp.status, 400)
        data = json.loads(resp.body)
        self.assertIn("error", data)

    async def test_caption_calls_whisper_model(self):
        env = _MockEnv()
        env.AI.run.return_value = {"text": "test"}
        req = _MockRequest(method="POST", body={"audio": self._audio_b64()})
        await worker._caption(req, env)
        call_args = env.AI.run.call_args
        self.assertEqual(call_args[0][0], worker.MODEL_WHISPER)

    async def test_caption_passes_audio_bytes_list(self):
        env = _MockEnv()
        env.AI.run.return_value = {"text": "ok"}
        raw = b"\x00\x01\x02\x03"
        req = _MockRequest(method="POST", body={"audio": base64.b64encode(raw).decode()})
        await worker._caption(req, env)
        _, payload = env.AI.run.call_args[0]
        self.assertEqual(payload["audio"], list(raw))

    async def test_caption_returns_model_name(self):
        env = _MockEnv()
        env.AI.run.return_value = {"text": "ok"}
        req = _MockRequest(method="POST", body={"audio": self._audio_b64()})
        resp = await worker._caption(req, env)
        data = json.loads(resp.body)
        self.assertEqual(data["model"], worker.MODEL_WHISPER)


# ---------------------------------------------------------------------------
# Tests for _speech_to_sign handler
# ---------------------------------------------------------------------------

class TestSpeechToSignHandler(unittest.IsolatedAsyncioTestCase):
    def _audio_b64(self) -> str:
        return base64.b64encode(b"audio-data").decode()

    async def test_returns_transcript_and_instructions(self):
        env = _MockEnv()
        env.AI.run.side_effect = [
            {"text": "Good morning"},
            {"response": "GOOD: open hand, fingers together..."},
        ]
        req = _MockRequest(method="POST", body={"audio": self._audio_b64(), "language": "ASL"})
        resp = await worker._speech_to_sign(req, env)
        data = json.loads(resp.body)
        self.assertEqual(data["transcript"], "Good morning")
        self.assertIn("instructions", data)
        self.assertEqual(data["sign_language"], "ASL")

    async def test_missing_audio_returns_400(self):
        req = _MockRequest(method="POST", body={"language": "ASL"})
        resp = await worker._speech_to_sign(req, _MockEnv())
        self.assertEqual(resp.status, 400)

    async def test_calls_whisper_then_llama(self):
        env = _MockEnv()
        env.AI.run.side_effect = [{"text": "hi"}, {"response": "wave hand"}]
        req = _MockRequest(method="POST", body={"audio": self._audio_b64()})
        await worker._speech_to_sign(req, env)
        calls = env.AI.run.call_args_list
        self.assertEqual(calls[0][0][0], worker.MODEL_WHISPER)
        self.assertEqual(calls[1][0][0], worker.MODEL_LLAMA)

    async def test_default_language_is_asl(self):
        env = _MockEnv()
        env.AI.run.side_effect = [{"text": "hi"}, {"response": "wave"}]
        req = _MockRequest(method="POST", body={"audio": self._audio_b64()})
        resp = await worker._speech_to_sign(req, env)
        data = json.loads(resp.body)
        self.assertEqual(data["sign_language"], "ASL")

    async def test_custom_language_passed_through(self):
        env = _MockEnv()
        env.AI.run.side_effect = [{"text": "hi"}, {"response": "wave"}]
        req = _MockRequest(method="POST", body={"audio": self._audio_b64(), "language": "BSL"})
        resp = await worker._speech_to_sign(req, env)
        data = json.loads(resp.body)
        self.assertEqual(data["sign_language"], "BSL")

    async def test_response_includes_model_names(self):
        env = _MockEnv()
        env.AI.run.side_effect = [{"text": "hello"}, {"response": "sign"}]
        req = _MockRequest(method="POST", body={"audio": self._audio_b64()})
        resp = await worker._speech_to_sign(req, env)
        data = json.loads(resp.body)
        self.assertIn(worker.MODEL_WHISPER, data["models"])
        self.assertIn(worker.MODEL_LLAMA, data["models"])


# ---------------------------------------------------------------------------
# Tests for _sign_to_speech handler
# ---------------------------------------------------------------------------

class TestSignToSpeechHandler(unittest.IsolatedAsyncioTestCase):
    def _img_b64(self) -> str:
        return base64.b64encode(b"fake-image-bytes").decode()

    async def test_returns_gesture_and_speech(self):
        env = _MockEnv()
        env.AI.run.side_effect = [
            {"description": "Hand raised, open palm"},
            {"response": "Hello"},
        ]
        req = _MockRequest(method="POST", body={"image": self._img_b64()})
        resp = await worker._sign_to_speech(req, env)
        data = json.loads(resp.body)
        self.assertIn("gesture_description", data)
        self.assertIn("speech_text", data)

    async def test_missing_image_returns_400(self):
        req = _MockRequest(method="POST", body={})
        resp = await worker._sign_to_speech(req, _MockEnv())
        self.assertEqual(resp.status, 400)

    async def test_data_url_prefix_stripped(self):
        env = _MockEnv()
        env.AI.run.side_effect = [{"description": "x"}, {"response": "y"}]
        raw = b"\xff\xd8"  # fake JPEG header
        data_url = "data:image/jpeg;base64," + base64.b64encode(raw).decode()
        req = _MockRequest(method="POST", body={"image": data_url})
        await worker._sign_to_speech(req, env)
        _, payload = env.AI.run.call_args_list[0][0]
        self.assertEqual(payload["image"], list(raw))

    async def test_calls_vision_then_llama(self):
        env = _MockEnv()
        env.AI.run.side_effect = [{"description": "g"}, {"response": "Hello"}]
        req = _MockRequest(method="POST", body={"image": self._img_b64()})
        await worker._sign_to_speech(req, env)
        calls = env.AI.run.call_args_list
        self.assertEqual(calls[0][0][0], worker.MODEL_VISION)
        self.assertEqual(calls[1][0][0], worker.MODEL_LLAMA)


# ---------------------------------------------------------------------------
# Tests for _visual_scene handler
# ---------------------------------------------------------------------------

class TestVisualSceneHandler(unittest.IsolatedAsyncioTestCase):
    def _img_b64(self) -> str:
        return base64.b64encode(b"img").decode()

    async def test_returns_description(self):
        env = _MockEnv()
        env.AI.run.return_value = {"description": "A park with trees"}
        req = _MockRequest(method="POST", body={"image": self._img_b64()})
        resp = await worker._visual_scene(req, env)
        data = json.loads(resp.body)
        self.assertEqual(data["description"], "A park with trees")

    async def test_missing_image_returns_400(self):
        req = _MockRequest(method="POST", body={})
        resp = await worker._visual_scene(req, _MockEnv())
        self.assertEqual(resp.status, 400)

    async def test_default_detail_level_standard(self):
        env = _MockEnv()
        env.AI.run.return_value = {"description": "scene"}
        req = _MockRequest(method="POST", body={"image": self._img_b64()})
        resp = await worker._visual_scene(req, env)
        data = json.loads(resp.body)
        self.assertEqual(data["detail_level"], "standard")

    async def test_brief_detail_level(self):
        env = _MockEnv()
        env.AI.run.return_value = {"description": "A cat."}
        req = _MockRequest(method="POST", body={"image": self._img_b64(), "detail_level": "brief"})
        resp = await worker._visual_scene(req, env)
        data = json.loads(resp.body)
        self.assertEqual(data["detail_level"], "brief")

    async def test_detailed_level_prompt_mentions_comprehensive(self):
        env = _MockEnv()
        env.AI.run.return_value = {"description": "full desc"}
        req = _MockRequest(method="POST", body={"image": self._img_b64(), "detail_level": "detailed"})
        await worker._visual_scene(req, env)
        _, payload = env.AI.run.call_args[0]
        self.assertIn("comprehensive", payload["prompt"].lower())

    async def test_returns_model_name(self):
        env = _MockEnv()
        env.AI.run.return_value = {"description": "desc"}
        req = _MockRequest(method="POST", body={"image": self._img_b64()})
        resp = await worker._visual_scene(req, env)
        data = json.loads(resp.body)
        self.assertEqual(data["model"], worker.MODEL_VISION)

    async def test_data_url_prefix_stripped(self):
        env = _MockEnv()
        env.AI.run.return_value = {"description": "ok"}
        raw = b"\x89PNG"
        data_url = "data:image/png;base64," + base64.b64encode(raw).decode()
        req = _MockRequest(method="POST", body={"image": data_url})
        await worker._visual_scene(req, env)
        _, payload = env.AI.run.call_args[0]
        self.assertEqual(payload["image"], list(raw))


# ---------------------------------------------------------------------------
# Tests for VoxBridgeWorker (routing layer)
# ---------------------------------------------------------------------------

class TestVoxBridgeWorkerRouting(unittest.IsolatedAsyncioTestCase):
    async def _fetch(self, method, path, body=None):
        url = "https://voxbridge.example.com" + path
        req = _MockRequest(method=method, url=url, body=body or {})
        env = _MockEnv()
        env.AI.run.return_value = {"text": "ok", "response": "ok", "description": "ok"}
        w = worker.VoxBridgeWorker()
        return await w.fetch(req, env, _MockCtx())

    async def test_options_returns_204(self):
        url = "https://voxbridge.example.com/api/health"
        req = _MockRequest(method="OPTIONS", url=url)
        env = _MockEnv()
        w = worker.VoxBridgeWorker()
        resp = await w.fetch(req, env, _MockCtx())
        self.assertEqual(resp.status, 204)

    async def test_health_route(self):
        resp = await self._fetch("GET", "/api/health")
        data = json.loads(resp.body)
        self.assertEqual(data["status"], "ok")

    async def test_unknown_route_returns_404(self):
        resp = await self._fetch("GET", "/api/nonexistent")
        self.assertEqual(resp.status, 404)

    async def test_worker_is_worker_entrypoint_subclass(self):
        from workers import WorkerEntrypoint
        self.assertTrue(issubclass(worker.VoxBridgeWorker, WorkerEntrypoint))


if __name__ == "__main__":
    unittest.main()
