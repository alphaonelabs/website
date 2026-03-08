"""
Unit tests for individual Syntharia handlers.

The ``workers`` module is mocked by ``conftest.py`` so these tests can run
outside the Cloudflare Workers runtime.
"""

import base64
import json
import sys
import os
import pytest

# Make src/ importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from unittest.mock import AsyncMock, MagicMock, patch


# ---------------------------------------------------------------------------
# Shared env fixture
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_env():
    """Return a mock ``env`` object whose ``AI.run`` is an AsyncMock."""
    env = MagicMock()
    env.AI = MagicMock()
    env.AI.run = AsyncMock()
    return env


# ===========================================================================
# Art handler
# ===========================================================================

class TestArtHandler:
    @pytest.mark.asyncio
    async def test_generate_returns_image_bytes(self, mock_env):
        from handlers.art import handle_art_generate

        fake_image = b"\x89PNG\r\n\x1a\n" + b"\x00" * 64
        mock_env.AI.run.return_value = fake_image

        resp = await handle_art_generate(mock_env, {"prompt": "a glowing forest"})

        assert resp.status == 200
        assert resp.headers.get("content-type") == "image/png"
        assert resp.body == fake_image

    @pytest.mark.asyncio
    async def test_generate_missing_prompt_returns_400(self, mock_env):
        from handlers.art import handle_art_generate

        resp = await handle_art_generate(mock_env, {})
        data = resp._json()

        assert resp.status == 400
        assert data["success"] is False
        assert "prompt" in data["error"]

    @pytest.mark.asyncio
    async def test_generate_applies_style_modifier(self, mock_env):
        from handlers.art import handle_art_generate

        mock_env.AI.run.return_value = b"\x89PNG fake"

        await handle_art_generate(mock_env, {"prompt": "sunset", "style": "watercolor"})

        call_args = mock_env.AI.run.call_args
        inputs = call_args[0][1]
        assert "watercolor" in inputs["prompt"].lower()

    @pytest.mark.asyncio
    async def test_generate_clamps_num_steps(self, mock_env):
        from handlers.art import handle_art_generate

        mock_env.AI.run.return_value = b"fakepng"

        await handle_art_generate(mock_env, {"prompt": "x", "num_steps": 999})
        call_args = mock_env.AI.run.call_args
        assert call_args[0][1]["num_steps"] == 20

        await handle_art_generate(mock_env, {"prompt": "x", "num_steps": -5})
        call_args = mock_env.AI.run.call_args
        assert call_args[0][1]["num_steps"] == 1

    @pytest.mark.asyncio
    async def test_generate_passes_negative_prompt(self, mock_env):
        from handlers.art import handle_art_generate

        mock_env.AI.run.return_value = b"fakepng"

        await handle_art_generate(mock_env, {
            "prompt": "castle",
            "negative_prompt": "blurry, dark",
        })

        call_args = mock_env.AI.run.call_args
        assert call_args[0][1]["negative_prompt"] == "blurry, dark"


# ===========================================================================
# Music handler
# ===========================================================================

VALID_MUSIC_JSON = json.dumps({
    "title": "Moonlit Reverie",
    "abc_notation": "X:1\nT:Moonlit Reverie\nM:4/4\nK:Am\nABcd|efga|",
    "chords": ["Am", "F", "C", "G"],
    "tempo": 80,
    "time_signature": "4/4",
    "key": "A minor",
    "style_notes": "Soft and contemplative.",
})


class TestMusicHandler:
    @pytest.mark.asyncio
    async def test_compose_returns_json(self, mock_env):
        from handlers.music import handle_music_compose

        mock_env.AI.run.return_value = {"response": VALID_MUSIC_JSON}

        resp = await handle_music_compose(mock_env, {"prompt": "a rainy day piano piece"})
        data = resp._json()

        assert resp.status == 200
        assert data["success"] is True
        assert data["data"]["title"] == "Moonlit Reverie"
        assert "Am" in data["data"]["chords"]

    @pytest.mark.asyncio
    async def test_compose_missing_prompt_returns_400(self, mock_env):
        from handlers.music import handle_music_compose

        resp = await handle_music_compose(mock_env, {})
        data = resp._json()

        assert resp.status == 400
        assert data["success"] is False

    @pytest.mark.asyncio
    async def test_compose_genre_included_in_response(self, mock_env):
        from handlers.music import handle_music_compose

        mock_env.AI.run.return_value = {"response": VALID_MUSIC_JSON}

        resp = await handle_music_compose(mock_env, {"prompt": "upbeat", "genre": "jazz"})
        data = resp._json()

        assert data["genre"] == "jazz"

    @pytest.mark.asyncio
    async def test_compose_handles_invalid_json_gracefully(self, mock_env):
        from handlers.music import handle_music_compose

        mock_env.AI.run.return_value = {"response": "This is not JSON at all!"}

        resp = await handle_music_compose(mock_env, {"prompt": "anything"})
        data = resp._json()

        assert resp.status == 200
        assert data["success"] is True
        assert "raw" in data["data"] or "error" in data["data"]


# ===========================================================================
# Poetry handler
# ===========================================================================

VALID_POEM_JSON = json.dumps({
    "title": "Autumn's Edge",
    "poem": "Leaves fall like whispered words,\nThe sky a bruised violet.",
    "form": "free",
    "notes": "Employs synesthesia to merge sight and sound.",
})


class TestPoetryHandler:
    @pytest.mark.asyncio
    async def test_generate_returns_poem(self, mock_env):
        from handlers.poetry import handle_poetry_generate

        mock_env.AI.run.return_value = {"response": VALID_POEM_JSON}

        resp = await handle_poetry_generate(mock_env, {"prompt": "autumn"})
        data = resp._json()

        assert resp.status == 200
        assert data["success"] is True
        assert data["data"]["title"] == "Autumn's Edge"
        assert "Leaves fall" in data["data"]["poem"]

    @pytest.mark.asyncio
    async def test_generate_missing_prompt_returns_400(self, mock_env):
        from handlers.poetry import handle_poetry_generate

        resp = await handle_poetry_generate(mock_env, {})
        data = resp._json()

        assert resp.status == 400
        assert data["success"] is False

    @pytest.mark.asyncio
    async def test_generate_includes_form_and_tone(self, mock_env):
        from handlers.poetry import handle_poetry_generate

        mock_env.AI.run.return_value = {"response": VALID_POEM_JSON}

        resp = await handle_poetry_generate(mock_env, {
            "prompt": "the sea",
            "form": "haiku",
            "tone": "melancholic",
        })
        data = resp._json()

        assert data["form"] == "haiku"
        assert data["tone"] == "melancholic"

    @pytest.mark.asyncio
    async def test_generate_passes_system_prompt_to_model(self, mock_env):
        from handlers.poetry import handle_poetry_generate

        mock_env.AI.run.return_value = {"response": VALID_POEM_JSON}

        await handle_poetry_generate(mock_env, {"prompt": "stars"})

        call_args = mock_env.AI.run.call_args
        messages = call_args[0][1]["messages"]
        assert messages[0]["role"] == "system"
        assert "poet" in messages[0]["content"].lower()


# ===========================================================================
# Style-transfer handler
# ===========================================================================

class TestStyleTransferHandler:
    @pytest.fixture
    def tiny_png_b64(self):
        """Return a base64-encoded 1×1 white PNG."""
        # Minimal valid PNG bytes
        png = (
            b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01"
            b"\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00"
            b"\x00\x0cIDATx\x9cc\xf8\x0f\x00\x00\x01\x01\x00\x05\x18"
            b"\xd8N\x00\x00\x00\x00IEND\xaeB`\x82"
        )
        return base64.b64encode(png).decode()

    @pytest.mark.asyncio
    async def test_apply_style_returns_image(self, mock_env, tiny_png_b64):
        from handlers.style_transfer import handle_style_transfer

        fake_styled = b"\x89PNG styled"
        mock_env.AI.run.return_value = fake_styled

        resp = await handle_style_transfer(mock_env, {
            "image": tiny_png_b64,
            "style_preset": "van_gogh",
        })

        assert resp.status == 200
        assert resp.headers.get("content-type") == "image/png"
        assert resp.body == fake_styled

    @pytest.mark.asyncio
    async def test_missing_image_returns_400(self, mock_env):
        from handlers.style_transfer import handle_style_transfer

        resp = await handle_style_transfer(mock_env, {"style_preset": "monet"})
        data = resp._json()

        assert resp.status == 400
        assert "image" in data["error"]

    @pytest.mark.asyncio
    async def test_missing_style_returns_400(self, mock_env, tiny_png_b64):
        from handlers.style_transfer import handle_style_transfer

        resp = await handle_style_transfer(mock_env, {"image": tiny_png_b64})
        data = resp._json()

        assert resp.status == 400
        assert "style" in data["error"]

    @pytest.mark.asyncio
    async def test_invalid_base64_returns_400(self, mock_env):
        from handlers.style_transfer import handle_style_transfer

        resp = await handle_style_transfer(mock_env, {
            "image": "not-valid-base64!!!",
            "style_preset": "monet",
        })
        data = resp._json()

        assert resp.status == 400
        assert "base64" in data["error"]

    @pytest.mark.asyncio
    async def test_strength_clamped(self, mock_env, tiny_png_b64):
        from handlers.style_transfer import handle_style_transfer

        mock_env.AI.run.return_value = b"fake"

        await handle_style_transfer(mock_env, {
            "image": tiny_png_b64,
            "style_preset": "anime",
            "strength": 999,
        })

        call_args = mock_env.AI.run.call_args
        assert call_args[0][1]["strength"] == 1.0


# ===========================================================================
# Refine handler
# ===========================================================================

class TestRefineHandler:
    @pytest.mark.asyncio
    async def test_invalid_content_type_returns_400(self, mock_env):
        from handlers.refine import handle_refine

        resp = await handle_refine(mock_env, {
            "content_type": "video",
            "instruction": "make it faster",
        })
        data = resp._json()

        assert resp.status == 400
        assert "content_type" in data["error"]

    @pytest.mark.asyncio
    async def test_missing_instruction_returns_400(self, mock_env):
        from handlers.refine import handle_refine

        resp = await handle_refine(mock_env, {"content_type": "poetry"})
        data = resp._json()

        assert resp.status == 400
        assert "instruction" in data["error"]

    @pytest.mark.asyncio
    async def test_refine_poetry_delegates_to_poetry_handler(self, mock_env):
        from handlers.refine import handle_refine

        mock_env.AI.run.return_value = {"response": VALID_POEM_JSON}

        resp = await handle_refine(mock_env, {
            "content_type": "poetry",
            "instruction": "make it darker",
            "prompt": "autumn",
            "poem": "The leaves are golden.",
            "form": "free",
        })
        data = resp._json()

        assert resp.status == 200
        assert data["success"] is True

    @pytest.mark.asyncio
    async def test_refine_music_delegates_to_music_handler(self, mock_env):
        from handlers.refine import handle_refine

        mock_env.AI.run.return_value = {"response": VALID_MUSIC_JSON}

        resp = await handle_refine(mock_env, {
            "content_type": "music",
            "instruction": "add a jazz swing feel",
            "prompt": "peaceful morning",
            "abc_notation": "X:1\nT:Morning\nK:C\nCDEF|",
            "genre": "jazz",
        })
        data = resp._json()

        assert resp.status == 200
        assert data["success"] is True

    @pytest.mark.asyncio
    async def test_refine_art_without_image_augments_prompt(self, mock_env):
        from handlers.refine import handle_refine

        # First call: augment prompt. Second call: generate image.
        mock_env.AI.run.side_effect = [
            {"response": "a glowing forest with dramatic storm clouds"},
            b"\x89PNG refined",
        ]

        resp = await handle_refine(mock_env, {
            "content_type": "art",
            "instruction": "add dramatic storm clouds",
            "prompt": "a glowing forest",
        })

        assert resp.status == 200
        assert resp.headers.get("content-type") == "image/png"
        # The AI was called twice: once for prompt augmentation, once for image gen
        assert mock_env.AI.run.call_count == 2
