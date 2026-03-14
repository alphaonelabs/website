# Alpha One Labs Education Platform

A modern, feature-rich education platform built with Django and Tailwind CSS that enables seamless learning experiences through course creation, peer connections, study groups, and interactive forums.

## Project Overview

Alpha One Labs is an education platform designed to facilitate both learning and teaching. The platform provides a comprehensive environment where educators can create and manage courses, while students can learn, collaborate, and engage with peers. With features like study groups, peer connections, and discussion forums, we aim to create a collaborative learning environment that goes beyond traditional online education.

## Features

### For Students

- 📚 Course enrollment and management
- 👥 Peer-to-peer connections and messaging
- 📝 Study group creation and participation
- 💬 Interactive discussion forums
- 📊 Progress tracking and analytics
- 🌟 Submit links and receive grades with feedback
- 🌙 Dark mode support
- 📱 Responsive design for all devices

### For Teachers

- 📝 Course creation and management
- 📊 Student progress monitoring
- 📈 Analytics dashboard
- 📣 Marketing tools for course promotion
- 💯 Grade submitted links and provide feedback
- 💰 Payment integration with Stripe
- 📧 Email marketing capabilities
- 🔔 Automated notifications

### Technical Features

- 🔒 Secure authentication system
- 🌐 Internationalization support
- 🚀 Performance optimized
- 📦 Modular architecture
- ⚡ Real-time updates
- 🔍 Search functionality
- 🎨 Customizable UI
- 🏆 "Get a Grade" system with academic grading scale

## Tech Stack

### Backend

- Python 3.10+
- Django 5.x
- Redis (channels + caching)
- MySQL (production) / SQLite (development optional)

### Frontend

- Tailwind CSS
- Alpine.js
- Font Awesome icons
- JavaScript (Vanilla)

### Infrastructure

- Docker support
- Nginx
- Uvicorn (ASGI)
- Django Channels (WebSockets)
- SendGrid for emails (graceful fallback)
- Stripe for payments

## Setup Instructions

### Prerequisites

- Python 3.10 or higher
- pip or poetry for package management
- Git

### Local Development Setup

1. Clone the repository:

   ```bash
   git clone https://github.com/alphaonelabs/alphaonelabs-education-website.git
   cd alphaonelabs-education-website
   ```

2. Set up virtual environment:

   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies (Poetry is the single source of truth):

   ```bash
   # Ensure Poetry installed (once)
   pip install --upgrade pip
   pip install poetry==1.8.3

   # Install project deps into local venv (recommended)
   poetry install

   # Activate virtualenv (Poetry 1.8 auto-detects)
   poetry shell  # or just use: poetry run <command>
   ```

4. Set up environment variables:

   ```bash
   cp .env.sample .env
   # Edit .env with your configuration
   ```

5. Run migrations:

   ```bash
   python manage.py migrate
   ```

6. Create a superuser:

   ```bash
   python manage.py createsuperuser
   ```

7. Create test data:

   ```bash
   python manage.py create_test_data
   ```

8. Run the development server with ASGI support (required for WebSockets):

   ```bash
   poetry run uvicorn web.asgi:application --host 127.0.0.1 --port 8000 --reload
   ```

   **Note:** WebSocket features (Live Avatars, Real-time Chat) require ASGI. Django's `runserver` command uses WSGI and will not support WebSockets.

9. Visit [http://localhost:8000](http://localhost:8000) in your browser.

### Docker Setup

1. Build the Docker image:

   ```bash
   docker build -t education-website .
   ```

2. Run the Docker container:

   ```bash
   docker run -d -p 8000:8000 education-website
   ```

3. Visit [http://localhost:8000](http://localhost:8000) in your browser.

### Admin Credentials:

- **Email:** `admin@example.com`
- **Password:** `adminpassword`

## Environment Variables Configuration

Copy `.env.sample` to `.env` and configure the variables.

## Development Guidelines

### Code Style

- Follow PEP 8 guidelines for Python code.
- Use **Black** for code formatting.
- Use **isort** for import sorting.
- Follow Django's coding style guide.
- Use **ESLint** for JavaScript code.

### Git Workflow

1. Create a new branch for each feature/bugfix.
2. Follow **conventional commits** for commit messages.
3. Submit **pull requests** for review.
4. Ensure all **tests pass** before merging.

### Testing

- Write unit tests for new features.
- Run tests before committing:

  ```bash
  python manage.py test
  ```

### Pre-commit Hooks (Important)

We use pre-commit to enforce formatting (black, isort), linting (flake8, djlint), etc.

```bash
poetry run pre-commit install
poetry run pre-commit run --hook-stage commit
poetry run pre-commit run --all-files
```

### Documentation

- Document all new features and API endpoints
- Update README.md when adding major features
- Use docstrings for Python functions and classes
- Comment complex logic

## Contributing

We welcome contributions! Please see our [Contributing Guidelines](CONTRIBUTING.md) for details on how to submit pull requests, report issues, and contribute to the project.

## Support

If you encounter any issues or need support, please:

1. Search existing [Issues](https://github.com/alphaonelabs/education-website/issues)
2. Create a new issue if your problem persists
3. Join us on [Slack](https://join.slack.com/t/alphaonelabs/shared_invite/zt-7dvtocfr-1dYWOL0XZwEEPUeWXxrB1A)
4. Join us on [Discord](https://discord.gg/HJtuzTJN3h)

## Homepage Design Philosophy

This section documents the principles guiding the homepage and overall platform design toward a **secure, focused, and trustworthy** online education experience.

### Core Goal

The homepage should answer three questions immediately:

1. **What can I learn here?**
2. **How do I start learning?**
3. **Why should I trust this platform?**

Everything else is secondary.

---

### ✅ Keep on Homepage (Vital Elements)

These are the **minimum essential elements** for an online education platform:

#### Primary Actions (Above the Fold)

```
Alpha One Labs
Secure Open Education Platform

[Start Learning]   [Start Teaching]

Browse Courses | Join Live Class
```

#### Learning Content

- Courses
- Live Classes
- Subjects
- Study Groups

#### Platform Features

- Virtual Classroom
- Collaborative Whiteboard
- Progress Tracking
- Secure Payments
- Encrypted Communication

#### For Teachers

- Create Courses
- Manage Students
- Earn from Teaching
- Analytics

#### Trust & Security Indicators

```
🔐 End-to-End Encrypted Classes
🛡️  Open Source Transparency
📚 Community Driven Learning
```

#### Progress & Achievements

Visible under the learner dashboard:

- Progress trackers
- Achievements
- Grade tracking

---

### 🔀 Move Off Homepage (Secondary Features)

These are valid features but should **not** appear on the main landing page:

| Feature | Move To |
|---|---|
| Blog | `Resources → Blog` |
| Forum | `Community → Forum` |
| Success Stories | Separate marketing page |
| Waiting Rooms | `Teach → Open Requests` |
| Contributions / Open Source | `About → Open Source` |

---

### ❌ Remove or Defer (Security & Clarity)

These items increase attack surface, payment complexity, or cognitive load:

| Item | Reason to Remove |
|---|---|
| Edu Memes | Removes professionalism |
| Storefronts / Merch Shop | Mixes payment systems; increases fraud surface |
| Referral Program | Major abuse vector: bot accounts, spam, fake referrals |
| Leaderboard | Gamification promotes cheating, botting, and API abuse |
| Challenges | Only relevant if the platform focuses on coding education (e.g., like LeetCode) |
| Duplicate navigation items | Simplify — avoid the same page appearing multiple times |

---

### 🧭 Navigation Simplification

The current navigation has **40+ menu items**. Good platforms use **5–7 items max** (counting Login/Signup as a single grouped action).

**Target navigation structure (6 items):**

```
Learn | Teach | Community | Resources | About | Login / Signup
```

Each top-level item may contain a focused dropdown:

- **Learn** → Courses, Live Classes, Subjects, Study Groups
- **Teach** → Create Course, Manage Students, Analytics, Open Requests
- **Community** → Forum, Study Groups, Learning Requests
- **Resources** → Blog, Documentation, API
- **About** → About Us, Open Source, Security, Privacy Policy

---

### 🔐 Security Considerations

The current feature set introduces several potential risk areas:

#### Payment Surface
Mixing courses, a store, donations, and referrals increases **payment fraud surface**. The platform should funnel all payments through **one system** (Stripe).

#### User-Generated Content
Allowing forum posts, blog posts, memes, requests, and arbitrary uploads increases:
- Spam risk
- XSS vulnerability surface
- Moderation burden

Limit UGC scope early and apply strict input sanitization.

#### Real-Time Rooms
Live classrooms and waiting rooms require:
- Strong authentication
- Rate limiting
- Session protection

Without these controls, real-time features are vulnerable to abuse.

---

### 🏠 Ideal Homepage Structure

```
Hero
├── Alpha One Labs — Secure Open Education Platform
├── [Start Learning]   [Start Teaching]
└── Browse Courses | Join Live Class

Browse Learning
├── Courses
├── Live Classes
├── Subjects
└── Study Groups

Platform Features
├── Virtual Classroom
├── Collaborative Whiteboard
├── Progress Tracking
├── Secure Payments
└── Encrypted Communication

For Teachers
├── Create Courses
├── Manage Students
├── Earn from Teaching
└── Analytics

Community
├── Forum
├── Study Groups
└── Learning Requests

Trust Section
├── Open Source
├── Privacy First
└── End-to-End Encryption
```

---

## Acknowledgments

- Thanks to all contributors who have helped shape this project
- Built with ❤️ by the Alpha One Labs team
