# Alpha One Labs Education Platform

Alpha One Labs is a Django-based learning platform for running courses, managing enrollments, supporting peer collaboration, and powering interactive community features such as forums, study groups, progress tracking, and virtual labs.

## Tech Stack

- Python 3.10+
- Django 5.x
- Django Channels + Uvicorn for ASGI/WebSockets
- Redis for channels and shared cache
- SQLite for local development, MySQL for production-like environments
- Poetry for dependency management

## Quick Start

### Prerequisites

- Python 3.10 or newer
- Git
- Poetry 1.8.3
- Redis (optional for local real-time features)
- MySQL (optional; SQLite works out of the box for local development)

### 1. Clone the repository

```bash
git clone https://github.com/alphaonelabs/alphaonelabs-education-website.git
cd alphaonelabs-education-website
```

### 2. Create and activate a virtual environment

macOS/Linux:

```bash
python -m venv .venv
source .venv/bin/activate
```

Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### 3. Install dependencies

```bash
python -m pip install --upgrade pip
pip install poetry==1.8.3
poetry install
```

You can run project commands either from your activated virtual environment or with `poetry run`.

### 4. Create your local environment file

macOS/Linux:

```bash
cp .env.sample .env
```

Windows PowerShell:

```powershell
Copy-Item .env.sample .env
```

Then review `.env` before starting the app. For most local work, the sample values are enough to boot with SQLite.

If you want a fresh secure messaging key, generate one with:

```bash
python web/master_key.py
```

### 5. Run migrations

```bash
poetry run python manage.py migrate
```

### 6. Optional bootstrap commands

Create an admin account:

```bash
poetry run python manage.py createsuperuser
```

Load sample data:

```bash
poetry run python manage.py create_test_data
```

### 7. Start the development server

Recommended for full local development, including WebSockets:

```bash
poetry run uvicorn web.asgi:application --host 127.0.0.1 --port 8000 --reload
```

If you only need standard Django pages and do not need WebSockets, this also works:

```bash
poetry run python manage.py runserver
```

Open the app at [http://127.0.0.1:8000/en/](http://127.0.0.1:8000/en/).

The admin lives behind the `ADMIN_URL` value from your `.env` file. With the default sample config, that is:

`http://127.0.0.1:8000/en/a-dmin-url123/`

## Environment Variables

`.env.sample` is the source of truth for local configuration. It includes comments for each variable and groups them by purpose.

The most important variables for local development are:

- `ENVIRONMENT`: use `development` locally
- `SECRET_KEY`: Django secret key
- `MESSAGE_ENCRYPTION_KEY`: required for secure messaging features
- `DATABASE_URL`: leave on SQLite for the easiest local setup
- `ALLOWED_HOSTS`: comma-separated hostnames the app will serve
- `CSRF_TRUSTED_ORIGINS`: comma-separated origins for local forms/admin access
- `ADMIN_URL`: custom admin path segment
- `REDIS_URL`: Redis endpoint for channels and shared cache

Most other values are optional unless you are actively working on integrations such as Stripe, Mailgun, GitHub webhooks, Google Cloud Storage, or social publishing.

## Testing and Linting

Run the Django test suite:

```bash
poetry run python manage.py test
```

Install and run pre-commit hooks:

```bash
poetry run pre-commit install
poetry run pre-commit run --all-files
```

## Common Errors

- WebSockets or live updates are not working: run the app with `uvicorn web.asgi:application`, not only `manage.py runserver`.
- You see `DisallowedHost` or CSRF failures on a custom host/port: update `ALLOWED_HOSTS` and `CSRF_TRUSTED_ORIGINS` in `.env`.
- Redis connection warnings appear locally: most pages can still work, but real-time features need a reachable `REDIS_URL`.
- MySQL client build errors occur during setup: keep `DATABASE_URL` on SQLite for local work, or install the MySQL client libraries required by `mysqlclient`.
- Google Cloud Storage errors appear in local development: leave `GS_BUCKET_NAME`, `GS_PROJECT_ID`, and `SERVICE_ACCOUNT_FILE` blank unless you are testing GCS integration.

## Contributing

Please read [CONTRIBUTING.md](CONTRIBUTING.md) before opening a pull request.

## Support

- Search existing [GitHub issues](https://github.com/alphaonelabs/education-website/issues)
- Join the community on [Slack](https://join.slack.com/t/alphaonelabs/shared_invite/zt-7dvtocfr-1dYWOL0XZwEEPUeWXxrB1A)
- Join the community on [Discord](https://discord.gg/HJtuzTJN3h)
