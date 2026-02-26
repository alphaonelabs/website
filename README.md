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

## Acknowledgments

- Thanks to all contributors who have helped shape this project
- Built with ❤️ by the Alpha One Labs team
