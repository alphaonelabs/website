# Python base image
FROM python:3.12-slim-bookworm

# Set working directory
WORKDIR /app

# Install dependencies
RUN apt-get update && apt-get upgrade -y && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy only dependency manifests first (better layer caching)
COPY pyproject.toml poetry.lock* ./

# Install Poetry and project dependencies (system deps minimal here; app build image)
RUN python -m pip install --upgrade pip wheel setuptools && \
    pip install poetry==1.8.3 && \
    poetry config virtualenvs.create false --local || true && \
    poetry install --only main --no-interaction --no-ansi

# Copy project files
COPY . .

# Create necessary directories for static files
RUN mkdir -p /app/static /app/staticfiles

# Create and configure environment variables
COPY .env.sample .env

# Collect static files
RUN python manage.py collectstatic --noinput

# Run migrations and create test data
RUN python manage.py migrate && \
    python manage.py create_test_data

# Create superuser
ENV DJANGO_SUPERUSER_USERNAME=admin
ENV DJANGO_SUPERUSER_EMAIL=admin@example.com
ENV DJANGO_SUPERUSER_PASSWORD=adminpassword
RUN python manage.py createsuperuser --noinput

# Echo message during build
RUN echo "Your Project is now live on http://localhost:8000"

# Expose port
EXPOSE 8000

# Healthcheck for ASGI liveness
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD curl -fsS http://127.0.0.1:8000/ || exit 1

# Start the ASGI server (uvicorn) for WebSocket support
CMD ["uvicorn", "web.asgi:application", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
