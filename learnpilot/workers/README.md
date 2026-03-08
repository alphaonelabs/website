# LearnPilot AI Worker

This directory contains the **Cloudflare Python Worker** that powers
LearnPilot's AI features at the edge.

## Architecture

```
LearnPilot Django app
        │
        │  HTTP (when CLOUDFLARE_WORKER_URL is set)
        ▼
Cloudflare Python Worker  (workers/src/worker.py)
        │
        │  Workers AI binding (env.AI)
        ▼
Cloudflare Workers AI  (@cf/meta/llama-3.1-8b-instruct)
```

The worker exposes these endpoints:

| Method | Path           | Description                              |
|--------|----------------|------------------------------------------|
| POST   | `/ai/chat`     | Continue a tutoring conversation         |
| POST   | `/ai/explain`  | Explain a concept at the learner's level |
| POST   | `/ai/practice` | Generate a practice question             |
| POST   | `/ai/evaluate` | Evaluate a learner's answer              |
| POST   | `/ai/path`     | Generate a personalised learning path    |
| GET    | `/health`      | Health check                             |

## Requirements

- [Node.js](https://nodejs.org/) ≥ 18 (for Wrangler CLI)
- A Cloudflare account with Workers AI enabled

## Deploy

```bash
# Install Wrangler CLI
npm install -g wrangler

# Authenticate
wrangler login

# Deploy the worker
cd workers
wrangler deploy
```

After deployment Wrangler will print the worker URL, e.g.
`https://learnpilot-ai.<your-subdomain>.workers.dev`.

Set this as `CLOUDFLARE_WORKER_URL` in the Django `.env` file to route
AI requests through the edge worker instead of calling the Cloudflare
AI REST API directly.

## Local Development

```bash
cd workers
wrangler dev
```

The worker will start on `http://localhost:8787`.
