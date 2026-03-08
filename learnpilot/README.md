# learnpilot
AI-powered personalized learning lab that adapts to each learner in real time. Combines natural language processing, adaptive curricula, intelligent tutoring, and progress tracking to create a dynamic educational experience with interactive explanations, guided practice, and continuous feedback. Uses Cloudflare AI Python workers

## Features

- 🧠 **Adaptive Curricula** – Cloudflare Workers AI generates a personalised learning path based on each learner's skill level, learning style, and goals.
- 💬 **Intelligent Tutoring** – Real-time AI tutor chat powered by `@cf/meta/llama-3.1-8b-instruct` explains concepts, answers questions, and adapts to the learner.
- 📈 **Progress Tracking** – XP system, day streaks, per-lesson scores, and AI-generated progress insights.
- ✏️ **Guided Practice** – AI-generated practice questions with instant evaluation and constructive feedback.
- 🗺️ **Personalised Paths** – Each learner gets a unique ordered learning path tailored to their knowledge gaps and goals.

## Architecture

```
LearnPilot Django app  (web UI + REST API)
        │
        │  HTTP (when CLOUDFLARE_WORKER_URL is configured)
        ▼
Cloudflare Python Worker  (workers/src/worker.py)
        │
        │  Workers AI binding (env.AI)
        ▼
Cloudflare Workers AI  (@cf/meta/llama-3.1-8b-instruct)
```

When `CLOUDFLARE_WORKER_URL` is **not** set, the Django app calls the
[Cloudflare Workers AI REST API](https://developers.cloudflare.com/workers-ai/get-started/rest-api/)
directly using your `CLOUDFLARE_ACCOUNT_ID` and `CLOUDFLARE_API_TOKEN`.

## Quick Start

### 1. Clone & install dependencies

```bash
git clone https://github.com/alphaonelabs/learnpilot.git
cd learnpilot
pip install -r requirements.txt
```

### 2. Configure environment

```bash
cp .env.example .env
# Edit .env and set:
#   SECRET_KEY, CLOUDFLARE_ACCOUNT_ID, CLOUDFLARE_API_TOKEN
```

### 3. Initialise the database

```bash
python manage.py migrate
python manage.py seed_data      # Loads sample topics, courses, and lessons
python manage.py createsuperuser
```

### 4. Run the development server

```bash
python manage.py runserver
```

Open [http://127.0.0.1:8000/](http://127.0.0.1:8000/) in your browser.

## Deploy Cloudflare Python Worker (optional)

See [`workers/README.md`](workers/README.md) for step-by-step deployment instructions.

Once deployed, set `CLOUDFLARE_WORKER_URL` in your `.env` to route AI
requests through the edge worker for lower latency.

## Running Tests

```bash
python manage.py test tests
```

## Project Structure

```
learnpilot/
├── manage.py
├── requirements.txt
├── .env.example
├── learnpilot/            # Django project settings & root URLs
├── learning/              # Main Django app
│   ├── models.py          # Topic, Course, Lesson, LearnerProfile, Progress, …
│   ├── views.py           # Dashboard, course list, tutoring session, progress
│   ├── urls.py
│   ├── admin.py
│   ├── ai/
│   │   ├── cloudflare_ai.py   # Cloudflare Workers AI HTTP client
│   │   ├── tutor.py           # IntelligentTutor – explain, practice, evaluate
│   │   └── adaptive.py        # AdaptiveCurriculum – path generation, difficulty
│   └── management/commands/
│       └── seed_data.py       # Sample topics, courses, and lessons
├── templates/             # Django HTML templates (Tailwind CSS via CDN)
├── static/
│   ├── css/main.css
│   └── js/tutor.js        # Real-time tutor chat UI
├── tests/                 # Unit & integration tests
└── workers/               # Cloudflare Python Worker
    ├── wrangler.toml
    ├── src/worker.py      # Edge worker with Cloudflare AI bindings
    └── README.md
```

