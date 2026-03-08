# VoxBridge

> AI-powered accessibility & communication toolkit — built with [Cloudflare Python Workers](https://developers.cloudflare.com/workers/languages/python/) and [Workers AI](https://developers.cloudflare.com/workers-ai/).

VoxBridge reduces communication barriers through four AI-driven features:

| Feature | Endpoint | AI Models |
|---------|----------|-----------|
| 🎤 **Real-time Captioning** | `POST /api/caption` | Whisper (`@cf/openai/whisper`) |
| 🗣️ **Speech → Sign Language** | `POST /api/speech-to-sign` | Whisper + LLaMA 3.1 |
| 🤟 **Sign → Speech** | `POST /api/sign-to-speech` | UForm Vision + LLaMA 3.1 |
| 🖼️ **Visual Scene Description** | `POST /api/visual-scene` | UForm Vision (`@cf/unum/uform-gen2-qwen-500m`) |

---

## Project structure

```
voxbridge/
├── wrangler.toml          # Cloudflare Workers configuration
├── src/
│   └── worker.py          # Python Worker – routing + AI handler functions
├── public/
│   └── index.html         # Interactive demo UI (served as a static asset)
└── tests/
    └── test_worker.py     # Unit tests (pytest, no CF runtime required)
```

---

## Prerequisites

- [Node.js](https://nodejs.org/) ≥ 18 (required by Wrangler CLI)
- [Wrangler](https://developers.cloudflare.com/workers/wrangler/) ≥ 3.x
  ```bash
  npm install -g wrangler
  ```
- A Cloudflare account with **Workers AI** enabled

---

## Local development

```bash
# Install Wrangler (if you haven't already)
npm install -g wrangler

# Log in to Cloudflare
wrangler login

# Start the local dev server (Python Workers + AI binding)
wrangler dev
```

The worker will be available at `http://localhost:8787`.  
Open `http://localhost:8787/` to use the interactive demo UI.

---

## Deployment

```bash
wrangler deploy
```

Wrangler will print the deployed Worker URL (e.g. `https://voxbridge.<your-subdomain>.workers.dev`).

---

## API reference

All endpoints accept and return `application/json`.  
CORS is enabled for all origins.

### `GET /api/health`
Returns service liveness status.

```json
{ "status": "ok", "service": "voxbridge" }
```

---

### `POST /api/caption`
Transcribe audio to text using OpenAI Whisper.

**Request body**
```json
{ "audio": "<base64-encoded audio bytes>" }
```

**Response**
```json
{ "text": "Hello world", "model": "@cf/openai/whisper" }
```

---

### `POST /api/speech-to-sign`
Transcribe audio, then generate step-by-step sign-language instructions.

**Request body**
```json
{
  "audio":    "<base64-encoded audio bytes>",
  "language": "ASL"   // optional: "ASL" (default) | "BSL" | "ISL"
}
```

**Response**
```json
{
  "transcript":    "Good morning",
  "sign_language": "ASL",
  "instructions":  "GOOD: open hand, palm facing out...\nMORNING: ...",
  "models": ["@cf/openai/whisper", "@cf/meta/llama-3.1-8b-instruct"]
}
```

---

### `POST /api/sign-to-speech`
Analyse a sign-language gesture image and return the spoken equivalent.

**Request body**
```json
{ "image": "<base64-encoded image or data-URL>" }
```

**Response**
```json
{
  "gesture_description": "Hand raised, open palm facing viewer...",
  "speech_text":         "Hello",
  "models": ["@cf/unum/uform-gen2-qwen-500m", "@cf/meta/llama-3.1-8b-instruct"]
}
```

---

### `POST /api/visual-scene`
Describe an image accessibly for visually impaired users.

**Request body**
```json
{
  "image":        "<base64-encoded image or data-URL>",
  "detail_level": "standard"   // optional: "brief" | "standard" (default) | "detailed"
}
```

**Response**
```json
{
  "description":  "A sunny park with children playing...",
  "detail_level": "standard",
  "model":        "@cf/unum/uform-gen2-qwen-500m"
}
```

---

## Running tests

The unit tests run against pure-Python stubs — no Cloudflare runtime required.

```bash
pip install pytest
pytest tests/ -v
```

---

## License

[MIT](LICENSE)
