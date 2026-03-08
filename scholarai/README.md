# ScholarAI

AI-powered research assistant designed to help students and scientists navigate large volumes of academic literature. Supports paper discovery, summarization, citation exploration, and question answering across research papers. Helps organise knowledge, identify trends, and accelerate literature review workflows.

Built as a **Cloudflare Python Worker** powered by **Cloudflare Workers AI** (`@cf/meta/llama-3.1-8b-instruct`).

---

## Features

| Feature | Endpoint | Description |
|---------|----------|-------------|
| Paper discovery | `POST /api/discover` | Find relevant papers for a query |
| Summarisation | `POST /api/summarize` | Structured summary of a paper |
| Citation exploration | `POST /api/citations` | Explore a paper's citation network |
| Question answering | `POST /api/qa` | Answer research questions from literature |
| Knowledge organisation | `POST /api/organize` | Cluster and map a reading list |
| Trend identification | `POST /api/trends` | Spot emerging and declining research trends |
| Literature review | `POST /api/review` | Generate a full literature review section |

---

## Quick Start (local development)

### Prerequisites

- [Node.js](https://nodejs.org/) ≥ 18
- [uv](https://github.com/astral-sh/uv) (Python package manager)

```bash
# Install Node dependencies (Wrangler CLI)
npm install

# Start the local development server (requires a free Cloudflare account)
npm run dev
```

The local server starts at `http://localhost:8787`.

> **Note:** A Cloudflare account is required for the Workers AI binding.
> Run `npx wrangler login` before `npm run dev` to authenticate.

---

## API Reference

### `GET /`

Returns API metadata and a usage guide for all endpoints.

---

### `POST /api/discover`

Discover relevant academic papers for a research query.

**Request body:**
```json
{
  "query": "transformer models in NLP",
  "fields": ["machine learning", "NLP"],
  "limit": 10
}
```

**Response:**
```json
{
  "query": "transformer models in NLP",
  "results": {
    "papers": [...],
    "research_directions": [...],
    "key_concepts": [...],
    "related_queries": [...]
  }
}
```

---

### `POST /api/summarize`

Generate a structured summary of a research paper.

**Request body** (at least one field required):
```json
{
  "title": "Attention Is All You Need",
  "abstract": "We propose a new simple network architecture...",
  "content": "Full paper text (optional, truncated to 4 000 chars)"
}
```

---

### `POST /api/citations`

Explore a paper's citation network.

**Request body:**
```json
{
  "paper": "Attention Is All You Need",
  "type": "related"
}
```

`type` options: `forward`, `backward`, `related` (default: `related`).

---

### `POST /api/qa`

Answer a research question using the AI's knowledge and optional context.

**Request body:**
```json
{
  "question": "What are the main advantages of self-attention over RNNs?",
  "context": "Optional background text",
  "papers": [{"title": "...", "year": 2017}]
}
```

---

### `POST /api/organize`

Organise a reading list into thematic clusters and a knowledge map.

**Request body:**
```json
{
  "papers": [
    {"title": "Paper A", "year": 2021},
    {"title": "Paper B", "year": 2022}
  ],
  "organize_by": "topic"
}
```

`organize_by` options: `topic`, `year`, `author`, `methodology` (default: `topic`).

---

### `POST /api/trends`

Identify research trends in a field or from a set of papers.

**Request body** (at least one of `field` or `papers` required):
```json
{
  "field": "computer vision",
  "time_range": "2018-2024",
  "papers": [...]
}
```

---

### `POST /api/review`

Generate a structured literature review.

**Request body:**
```json
{
  "topic": "graph neural networks",
  "papers": [...],
  "style": "comprehensive",
  "audience": "graduate students"
}
```

`style` options: `comprehensive`, `brief`, `systematic` (default: `comprehensive`).

---

## Deployment

```bash
# Deploy to Cloudflare Workers
npm run deploy
```

---

## Development

### Running tests

```bash
# Install dev dependencies
uv sync --group dev

# Run tests
uv run pytest tests/ -v
```

### Project structure

```
scholarai/
├── src/
│   └── entry.py          # FastAPI app + WorkerEntrypoint
├── tests/
│   └── test_entry.py     # Pytest tests with mocked AI binding
├── wrangler.jsonc         # Cloudflare Workers configuration
├── pyproject.toml         # Python project + dependencies
├── package.json           # npm scripts for Wrangler CLI
└── README.md
```

---

## Architecture

```
HTTP Request
     │
     ▼
WorkerEntrypoint.fetch()   ← Cloudflare Workers runtime
     │  (via asgi bridge)
     ▼
FastAPI app                ← routing, validation, error handling
     │
     ▼
Depends(get_env)           ← injects Cloudflare env into each handler
     │
     ▼
env.AI.run(model, params)  ← Cloudflare Workers AI (@cf/meta/llama-3.1-8b-instruct)
     │
     ▼
JSON Response
```

