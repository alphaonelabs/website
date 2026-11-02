# ⚗️ QuantaLab

**Interactive virtual laboratory** where students explore physics, chemistry, and biology experiments through simulation. Guided by an **AI mentor** (powered by Cloudflare Workers AI) that explains concepts, answers questions, and suggests experiments. Designed to make scientific exploration accessible, safe, and engaging through hands-on digital experimentation.

---

## ✨ Features

| Domain | Experiments |
|---|---|
| ⚛️ **Physics** | Simple Pendulum, Projectile Motion, Ohm's Law |
| 🧪 **Chemistry** | Acid–Base Reactions, Boyle's Law, Acid–Base Titration |
| 🧬 **Biology** | Mitosis, Natural Selection, Photosynthesis |

- **Real-time simulations** rendered on an HTML5 Canvas with live parameter controls
- **AI Mentor** chat powered by `@cf/meta/llama-3.3-70b-instruct-fp8-fast` via Cloudflare Workers AI
- **Interactive controls** — sliders to adjust experiment parameters and instantly see results
- **Live measurements** panel with calculated metrics for each experiment
- Fully serverless — runs as a **Cloudflare Python Worker** with static assets

---

## 🏗 Project Structure

```
quantalab/
├── wrangler.toml          # Cloudflare Workers configuration
├── src/
│   ├── index.py           # Python Worker — HTTP router
│   ├── experiments.py     # Experiment catalogue (data + helpers)
│   └── ai_mentor.py       # Cloudflare AI integration
├── static/
│   ├── index.html         # Single-page application shell
│   ├── style.css          # Dark-theme responsive styles
│   └── app.js             # Simulation engine + chat client
├── tests/
│   └── test_experiments.py # Pytest unit tests
└── requirements.txt       # Local dev dependencies
```

---

## 🚀 Getting Started

### Prerequisites

- [Node.js](https://nodejs.org/) ≥ 18 (for Wrangler CLI)
- [Wrangler](https://developers.cloudflare.com/workers/wrangler/) ≥ 3.x
- A Cloudflare account with **Workers AI** enabled

```bash
npm install -g wrangler
```

### Local Development

```bash
# Clone the repo
git clone https://github.com/alphaonelabs/website.git
cd website/quantalab

# Install local test dependencies
pip install -r requirements.txt

# Run tests
pytest tests/ -v

# Start the local dev server (Wrangler)
wrangler dev
```

Open `http://localhost:8787` in your browser.

> **Note:** The AI Mentor requires a Cloudflare Workers AI binding which is automatically available in both `wrangler dev` and production deployments.

### Deploy to Cloudflare Workers

```bash
wrangler deploy
```

Wrangler will output a `*.workers.dev` URL for your deployment.

---

## 🔌 API Reference

| Method | Path | Description |
|---|---|---|
| `GET` | `/` | Serve the SPA (index.html) |
| `GET` | `/api/health` | Health-check — returns `{"status":"ok"}` |
| `GET` | `/api/experiments` | List all experiments across all domains |
| `GET` | `/api/experiments/{domain}` | List experiments for a specific domain |
| `GET` | `/api/experiments/{domain}/{id}` | Get details for a single experiment |
| `POST` | `/api/mentor` | Ask the AI mentor a question |

### POST `/api/mentor`

**Request body:**
```json
{
  "message": "Why does a longer pendulum have a longer period?",
  "history": [{"role": "user", "content": "..."}, {"role": "assistant", "content": "..."}],
  "domain": "physics",
  "experiment": "pendulum"
}
```

**Response:**
```json
{
  "response": "Great question! The period of a pendulum depends on..."
}
```

---

## 🧪 Running Tests

```bash
pip install -r requirements.txt
pytest tests/ -v
```

---

## 🛠 Technology Stack

| Layer | Technology |
|---|---|
| Runtime | Cloudflare Python Workers (Pyodide) |
| AI | Cloudflare Workers AI (`@cf/meta/llama-3.3-70b-instruct-fp8-fast`) |
| Frontend | Vanilla HTML5/CSS3/JavaScript + Canvas API |
| Fonts | Inter + JetBrains Mono (Google Fonts) |
| Testing | pytest + pytest-asyncio |
| Deployment | Cloudflare Workers (via Wrangler) |

---

## 📄 License

[MIT](LICENSE)
