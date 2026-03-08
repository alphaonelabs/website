"""
Iterative refinement handler — takes a previous Syntharia output and an
instruction, then generates a refined version using the appropriate model.

Supported content types: "art", "music", "poetry"
"""

import base64

from workers import Response

from handlers.art import handle_art_generate
from handlers.music import handle_music_compose
from handlers.poetry import handle_poetry_generate
from handlers.style_transfer import handle_style_transfer

_TEXT_MODEL = "@cf/meta/llama-3.1-8b-instruct"

_REFINE_SYSTEM_PROMPT = """You are a creative AI assistant helping to refine artistic work.
The user will give you their original content and a refinement instruction.
Produce an improved version that incorporates the requested changes while
preserving the strengths of the original.
Reply ONLY with the refined content — no preamble, no explanation."""


async def handle_refine(env, body: dict) -> Response:
    """Refine a previously generated piece of content.

    Expected body keys:
        content_type (str, required): "art", "music", or "poetry".
        instruction  (str, required): What to change or improve.

        --- For art ---
        prompt          (str): Original prompt used to generate the image.
        style           (str): Original style key.
        image           (str): Base64-encoded image to refine (uses style transfer).
        style_prompt    (str): New style description (required if image provided).

        --- For music ---
        prompt  (str): Original music prompt.
        genre   (str): Original genre.
        abc_notation (str): The ABC notation to refine (fed back to the model).

        --- For poetry ---
        prompt  (str): Original poetry prompt.
        form    (str): Original poetic form.
        tone    (str): Original tone.
        poem    (str): The poem text to refine.
    """
    content_type = (body.get("content_type") or "").lower().strip()
    instruction = (body.get("instruction") or "").strip()

    if content_type not in {"art", "music", "poetry"}:
        return Response.json(
            {
                "success": False,
                "error": "content_type must be one of: art, music, poetry",
            },
            status=400,
        )

    if not instruction:
        return Response.json(
            {"success": False, "error": "instruction is required"},
            status=400,
        )

    if content_type == "art":
        return await _refine_art(env, body, instruction)
    elif content_type == "music":
        return await _refine_music(env, body, instruction)
    else:  # poetry
        return await _refine_poetry(env, body, instruction)


# ---------------------------------------------------------------------------
# Art refinement
# ---------------------------------------------------------------------------

async def _refine_art(env, body: dict, instruction: str) -> Response:
    """Refine an image.

    If ``image`` (base64) is provided, use style transfer with the instruction
    as the style prompt.  Otherwise, augment the original prompt with the
    instruction and re-generate.
    """
    if body.get("image"):
        # Style-transfer route: apply instruction as style
        refined_body = {
            "image": body["image"],
            "style_prompt": instruction,
            "strength": float(body.get("strength") or 0.65),
            "num_steps": int(body.get("num_steps") or 10),
        }
        return await handle_style_transfer(env, refined_body)

    # Prompt-augmentation route
    original_prompt = (body.get("prompt") or "").strip()
    refined_prompt = await _augment_prompt(env, original_prompt, instruction)

    refined_body = {
        "prompt": refined_prompt,
        "style": body.get("style", ""),
        "num_steps": int(body.get("num_steps") or 10),
    }
    return await handle_art_generate(env, refined_body)


# ---------------------------------------------------------------------------
# Music refinement
# ---------------------------------------------------------------------------

async def _refine_music(env, body: dict, instruction: str) -> Response:
    """Refine a musical composition."""
    original_prompt = (body.get("prompt") or "").strip()
    abc_notation = (body.get("abc_notation") or "").strip()

    context_parts = []
    if original_prompt:
        context_parts.append(f"Original prompt: {original_prompt}")
    if abc_notation:
        context_parts.append(f"Original ABC notation:\n{abc_notation}")

    context = "\n".join(context_parts)
    refined_prompt = (
        f"{context}\n\nRefinement instruction: {instruction}" if context else instruction
    )

    refined_body = {
        "prompt": refined_prompt,
        "genre": body.get("genre", "classical"),
        "tempo": body.get("tempo"),
    }
    return await handle_music_compose(env, refined_body)


# ---------------------------------------------------------------------------
# Poetry refinement
# ---------------------------------------------------------------------------

async def _refine_poetry(env, body: dict, instruction: str) -> Response:
    """Refine a poem."""
    original_prompt = (body.get("prompt") or "").strip()
    poem_text = (body.get("poem") or "").strip()

    context_parts = []
    if original_prompt:
        context_parts.append(f"Original prompt: {original_prompt}")
    if poem_text:
        context_parts.append(f"Original poem:\n{poem_text}")

    context = "\n".join(context_parts)
    refined_prompt = (
        f"{context}\n\nRefinement instruction: {instruction}" if context else instruction
    )

    refined_body = {
        "prompt": refined_prompt,
        "form": body.get("form", "free"),
        "tone": body.get("tone", ""),
    }
    return await handle_poetry_generate(env, refined_body)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _augment_prompt(env, original_prompt: str, instruction: str) -> str:
    """Ask the LLM to rewrite the original prompt incorporating the instruction."""
    if not original_prompt:
        return instruction

    user_message = (
        f'Original image prompt: "{original_prompt}"\n'
        f'Refinement instruction: "{instruction}"\n'
        f"Write a single improved image generation prompt that incorporates "
        f"the refinement. Output only the prompt text, nothing else."
    )

    response = await env.AI.run(
        _TEXT_MODEL,
        {
            "messages": [
                {
                    "role": "system",
                    "content": _REFINE_SYSTEM_PROMPT,
                },
                {"role": "user", "content": user_message},
            ],
            "max_tokens": 256,
        },
    )

    if isinstance(response, str):
        return response.strip() or original_prompt
    if isinstance(response, dict):
        return (response.get("response") or original_prompt).strip()
    try:
        return str(response.response).strip() or original_prompt
    except Exception:
        return original_prompt
