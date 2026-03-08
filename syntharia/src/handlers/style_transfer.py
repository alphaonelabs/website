"""
Style-transfer handler — applies an artistic style to an uploaded image
using Cloudflare Workers AI image-to-image model.

Model: @cf/runwayml/stable-diffusion-v1-5-img2img
"""

import base64

from workers import Response

_IMG2IMG_MODEL = "@cf/runwayml/stable-diffusion-v1-5-img2img"

# Pre-defined style presets the user can pick from the UI
_STYLE_PRESETS = {
    "van_gogh": "in the style of Van Gogh, swirling brushstrokes, vivid colors",
    "monet": "in the style of Monet, impressionist, soft light, painterly",
    "picasso": "in the style of Picasso, cubism, geometric, fragmented",
    "anime": "anime style, Studio Ghibli, cel-shaded, vibrant",
    "watercolor": "watercolor painting, soft washes, artistic, dreamy",
    "cyberpunk": "cyberpunk, neon lights, dark, futuristic cityscape",
    "oil_painting": "oil painting, old masters, textured canvas, chiaroscuro",
    "sketch": "pencil sketch, detailed cross-hatching, monochrome",
}


async def handle_style_transfer(env, body: dict) -> Response:
    """Apply a style to a user-supplied image.

    Expected body keys:
        image         (str, required): Base64-encoded source image (PNG or JPEG).
        style_prompt  (str, optional): Free-text style description.
        style_preset  (str, optional): Key from ``_STYLE_PRESETS``.
        strength      (float, optional): How strongly to apply the style (0.0–1.0).
        num_steps     (int, optional): Diffusion steps (1–20, default 10).

    Either ``style_prompt`` or ``style_preset`` must be provided.
    """
    image_b64 = (body.get("image") or "").strip()
    if not image_b64:
        return Response.json(
            {"success": False, "error": "image (base64) is required"},
            status=400,
        )

    style_prompt = (body.get("style_prompt") or "").strip()
    preset_key = (body.get("style_preset") or "").lower()
    preset_text = _STYLE_PRESETS.get(preset_key, "")

    if not style_prompt and not preset_text:
        return Response.json(
            {"success": False, "error": "style_prompt or style_preset is required"},
            status=400,
        )

    combined_style = " ".join(filter(None, [preset_text, style_prompt]))

    strength = float(body.get("strength") or 0.6)
    strength = max(0.01, min(1.0, strength))

    num_steps = int(body.get("num_steps") or 10)
    num_steps = max(1, min(20, num_steps))

    # Decode base64 image → raw bytes list for Workers AI
    try:
        image_bytes = base64.b64decode(image_b64)
    except Exception:
        return Response.json(
            {"success": False, "error": "image must be valid base64"},
            status=400,
        )

    inputs = {
        "prompt": combined_style,
        "image": list(image_bytes),
        "strength": strength,
        "num_steps": num_steps,
    }

    styled_bytes = await env.AI.run(_IMG2IMG_MODEL, inputs)

    return Response(
        styled_bytes,
        headers={
            "content-type": "image/png",
            "x-syntharia-model": _IMG2IMG_MODEL,
            "x-syntharia-style": combined_style[:200],
        },
    )
