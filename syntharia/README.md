# syntharia

A creative AI studio where users collaborate with models to generate art, music, and poetry. Provides tools for image generation, music composition, style transfer, and iterative refinement. Designed as an interactive environment for exploring generative creativity and building multimedia AI-assisted projects.

Built on **[Cloudflare Python Workers](https://developers.cloudflare.com/workers/languages/python/)** and **[Cloudflare Workers AI](https://developers.cloudflare.com/workers-ai/)**.

---

## Features

| Feature | Endpoint | Model |
|---------|----------|-------|
| 🎨 **Image Generation** | `POST /api/art/generate` | `@cf/stabilityai/stable-diffusion-xl-base-1.0` |
| 🖼️ **Style Transfer** | `POST /api/art/style-transfer` | `@cf/runwayml/stable-diffusion-v1-5-img2img` |
| 🎵 **Music Composition** | `POST /api/music/compose` | `@cf/meta/llama-3.1-8b-instruct` (ABC notation) |
| 📝 **Poetry** | `POST /api/poetry/generate` | `@cf/meta/llama-3.1-8b-instruct` |
| ✨ **Iterative Refinement** | `POST /api/refine` | All of the above |

---

## Project Structure

```
syntharia/
├── wrangler.toml               # Cloudflare Worker configuration
├── requirements-dev.txt        # Dev/test dependencies
├── src/
│   ├── entry.py                # Worker entry point & URL router
│   ├── ui.py                   # Inline HTML single-page app
│   └── handlers/
│       ├── art.py              # Image generation handler
│       ├── music.py            # Music composition handler
│       ├── poetry.py           # Poetry generation handler
│       ├── style_transfer.py   # Style-transfer handler
│       └── refine.py           # Iterative refinement handler
└── tests/
    ├── conftest.py             # Mock workers module for local testing
    ├── test_entry.py           # Entry point / routing tests
    └── test_handlers.py        # Handler unit tests
```

---

## Local Development

### Prerequisites

- [Node.js](https://nodejs.org/) (for `wrangler` CLI)
- [uv](https://docs.astral.sh/uv/) Python package manager
- A Cloudflare account with Workers AI enabled

### Run locally

```bash
# Install pywrangler (Cloudflare Python Workers CLI)
uvx --from workers-py pywrangler dev
```

Press `b` to open the browser, or visit `http://localhost:8787`.

### Deploy

```bash
uvx --from workers-py pywrangler deploy
```

---

## API Reference

### `POST /api/art/generate`

Generate an image from a text prompt.

```json
{
  "prompt": "A surreal landscape with floating islands",
  "style": "watercolor",
  "num_steps": 8,
  "negative_prompt": "blurry, low quality"
}
```

**Style options:** `photorealistic`, `artistic`, `abstract`, `digital`, `watercolor`, `sketch`

Returns: `image/png` binary

---

### `POST /api/art/style-transfer`

Apply an artistic style to an existing image.

```json
{
  "image": "<base64-encoded PNG or JPEG>",
  "style_preset": "van_gogh",
  "style_prompt": "vivid swirling brushstrokes",
  "strength": 0.65,
  "num_steps": 10
}
```

**Style presets:** `van_gogh`, `monet`, `picasso`, `anime`, `watercolor`, `cyberpunk`, `oil_painting`, `sketch`

Returns: `image/png` binary

---

### `POST /api/music/compose`

Compose a piece of music as ABC notation and chord progressions.

```json
{
  "prompt": "A melancholic piano piece evoking rain on a quiet morning",
  "genre": "classical",
  "tempo": 80
}
```

**Genres:** `classical`, `jazz`, `electronic`, `ambient`, `folk`, `cinematic`

Returns:

```json
{
  "success": true,
  "genre": "classical",
  "model": "@cf/meta/llama-3.1-8b-instruct",
  "data": {
    "title": "Morning Rain",
    "abc_notation": "X:1\nT:Morning Rain\nM:4/4\nK:Am\n...",
    "chords": ["Am", "F", "C", "G"],
    "tempo": 80,
    "time_signature": "4/4",
    "key": "A minor",
    "style_notes": "Soft and introspective."
  }
}
```

---

### `POST /api/poetry/generate`

Generate a poem.

```json
{
  "prompt": "The passage of time observed through changing seasons",
  "form": "sonnet",
  "tone": "melancholic"
}
```

**Forms:** `free`, `sonnet`, `haiku`, `ballad`, `ode`, `limerick`  
**Tones:** `romantic`, `melancholic`, `joyful`, `philosophical`, `mysterious`, `hopeful`

Returns:

```json
{
  "success": true,
  "form": "sonnet",
  "tone": "melancholic",
  "data": {
    "title": "Autumn's Edge",
    "poem": "Leaves fall like whispered words,\n...",
    "form": "free",
    "notes": "Employs synesthesia."
  }
}
```

---

### `POST /api/refine`

Iteratively refine any previous output.

```json
{
  "content_type": "poetry",
  "instruction": "Make it darker and more mysterious",
  "prompt": "autumn leaves",
  "poem": "The leaves are golden...",
  "form": "free",
  "tone": "melancholic"
}
```

`content_type` must be one of: `art`, `music`, `poetry`

For art with an existing image, include `"image": "<base64>"` to use style transfer.

---

## Running Tests

```bash
pip install -r requirements-dev.txt
python -m pytest tests/ -v
```

---

## Technology

- **[Cloudflare Python Workers](https://developers.cloudflare.com/workers/languages/python/)** — Python serverless runtime on Cloudflare's global network
- **[Cloudflare Workers AI](https://developers.cloudflare.com/workers-ai/)** — serverless GPU inference with Stable Diffusion XL, Llama 3, and more
- **[abcjs](https://www.abcjs.net/)** — in-browser ABC notation renderer for music output

