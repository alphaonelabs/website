"""
Art generation handler — text-to-image using Cloudflare Workers AI.

Model: @cf/stabilityai/stable-diffusion-xl-base-1.0
"""

import json

from workers import Response

# Stable Diffusion XL for high-quality image generation
_IMAGE_MODEL = "@cf/stabilityai/stable-diffusion-xl-base-1.0"

# Style modifier prompts applied on top of the user prompt
_STYLE_MODIFIERS = {
    "photorealistic": "photorealistic, high detail, 8k, HDR photography",
    "artistic": "oil painting, brush strokes, impressionist, fine art",
    "abstract": "abstract art, geometric shapes, vivid colors, contemporary",
    "digital": "digital art, concept art, artstation, highly detailed",
    "watercolor": "watercolor painting, soft edges, artistic, pastel tones",
    "sketch": "pencil sketch, charcoal drawing, monochrome, hand-drawn",
}


async def handle_art_generate(env, body: dict) -> Response:
    """Generate an image from a text prompt via Stable Diffusion XL.

    Expected body keys:
        prompt (str, required): The image description.
        style  (str, optional): One of the keys in ``_STYLE_MODIFIERS``.
        negative_prompt (str, optional): Things to exclude from the image.
        num_steps (int, optional): Diffusion steps (1–20, default 8).
    """
    prompt = (body.get("prompt") or "").strip()
    if not prompt:
        return Response.json(
            {"success": False, "error": "prompt is required"},
            status=400,
        )

    style = (body.get("style") or "").lower()
    modifier = _STYLE_MODIFIERS.get(style, "")
    full_prompt = f"{prompt}, {modifier}" if modifier else prompt

    num_steps = int(body.get("num_steps") or 8)
    num_steps = max(1, min(20, num_steps))

    negative_prompt = (body.get("negative_prompt") or "").strip()

    inputs = {"prompt": full_prompt, "num_steps": num_steps}
    if negative_prompt:
        inputs["negative_prompt"] = negative_prompt

    image_bytes = await env.AI.run(_IMAGE_MODEL, inputs)

    return Response(
        image_bytes,
        headers={
            "content-type": "image/png",
            "x-syntharia-model": _IMAGE_MODEL,
            "x-syntharia-prompt": full_prompt[:200],
        },
    )
