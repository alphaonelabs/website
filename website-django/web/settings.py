import logging
import os
import sys
from pathlib import Path

import environ
import sentry_sdk
from cryptography.fernet import Fernet
from django.core.exceptions import DisallowedHost
from sentry_sdk.integrations.django import DjangoIntegration
from sentry_sdk.integrations.logging import LoggingIntegration

BASE_DIR = Path(__file__).resolve().parent.parent

env = environ.Env()

env_file = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")


# Set encryption key for secure messaging; in production, this must come from the environment
MESSAGE_ENCRYPTION_KEY = env.str("MESSAGE_ENCRYPTION_KEY", default=Fernet.generate_key()).strip()
SECURE_MESSAGE_KEY = MESSAGE_ENCRYPTION_KEY

if os.path.exists(env_file):
    environ.Env.read_env(env_file)
else:
    print("No .env file found.")

# Re-initialize / initialize Sentry AFTER environment variables are loaded so DSN is present here.
SENTRY_DSN = env.str("SENTRY_DSN", default="")
if SENTRY_DSN:
    # Capture WARNING+ as breadcrumbs and ERROR+ as events
    sentry_logging = LoggingIntegration(
        level=getattr(logging, os.getenv("SENTRY_LOG_LEVEL", "INFO").upper(), logging.INFO),
        event_level=logging.ERROR,
    )
    sentry_sdk.init(
        dsn=SENTRY_DSN,
        integrations=[DjangoIntegration(), sentry_logging],
        environment=env.str("ENVIRONMENT", default="development"),
        send_default_pii=True,
        traces_sample_rate=float(os.getenv("SENTRY_TRACES_SAMPLE_RATE", 0.0)),  # set >0 to enable performance
        # Do not send Invalid Host (DisallowedHost) errors to Sentry
        ignore_errors=(DisallowedHost,),
    )
else:
    # Helpful notice for ops without breaking startup
    print("Sentry DSN not configured; error events will not be sent.")

SECRET_KEY = env.str("SECRET_KEY", default="django-insecure-5kyff0s@l_##j3jawec5@b%!^^e(j7v)ouj4b7q6kru#o#a)o3")
# Debug settings
ENVIRONMENT = env.str("ENVIRONMENT", default="development")

# Default DEBUG to False for security
DEBUG = False

# Only enable DEBUG in local environment and only if DJANGO_DEBUG is True
if ENVIRONMENT == "development":
    DEBUG = True

# Detect test environment and set DEBUG=True to use local media path
if "test" in sys.argv:
    TESTING = True
    DEBUG = True
else:
    TESTING = False

PA_USER = "alphaonelabs99282llkb"
PA_HOST = PA_USER + ".pythonanywhere.com"
PA_WSGI = "/var/www/" + PA_USER + "_pythonanywhere_com_wsgi.py"
PA_SOURCE_DIR = "/home/" + PA_USER + "/web"

# Social Media Settings
TWITTER_USERNAME = "alphaonelabs"
TWITTER_API_KEY = os.getenv("TWITTER_API_KEY")
TWITTER_API_SECRET_KEY = os.getenv("TWITTER_API_SECRET_KEY")
TWITTER_ACCESS_TOKEN = os.getenv("TWITTER_ACCESS_TOKEN")
TWITTER_ACCESS_TOKEN_SECRET = os.getenv("TWITTER_ACCESS_TOKEN_SECRET")

# Production settings
if not DEBUG:
    # SECURE_SSL_REDIRECT = True
    # adding this to prevent redirect loop
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = 31536000  # 1 year
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SECURE_BROWSER_XSS_FILTER = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    SECURE_REDIRECT_EXEMPT = []
    SECURE_SSL_HOST = "alphaonelabs.com"
    SECURE_REFERRER_POLICY = "strict-origin-when-cross-origin"

# Allow hosts list can be overridden via .env (comma-separated) while providing a strong default.
ALLOWED_HOSTS = env.list(
    "ALLOWED_HOSTS",
    default=[
        "alphaonelabs99282llkb.pythonanywhere.com",
        "0.0.0.0",
        "127.0.0.1",
        "localhost",
        "alphaonelabs.com",
        ".alphaonelabs.com",
    ],
)

# CSRF trusted origins can also be overridden through .env (comma-separated).
CSRF_TRUSTED_ORIGINS = env.list(
    "CSRF_TRUSTED_ORIGINS",
    default=[
        "https://alphaonelabs.com",
        "https://www.alphaonelabs.com",
        "http://127.0.0.1:8000",
        "http://localhost:8000",
    ],
)

# Timezone settings
TIME_ZONE = "America/New_York"
USE_TZ = True

# Error handling
handler404 = "web.views.custom_404"
# Custom handler for 429 (too many requests)
handler429 = "web.views.custom_429"

# Admin notification settings
ADMINS = [("Admin", os.getenv("EMAIL_FROM"))]
SERVER_EMAIL = os.getenv("EMAIL_FROM")  # Email address error messages come from

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.sites",
    "django.contrib.humanize",
    "channels",
    "allauth",
    "allauth.account",
    "captcha",
    "markdownx",
    "web",
    "web.virtual_lab.apps.VirtualLabConfig",
]

if DEBUG and not TESTING:
    INSTALLED_APPS.append("django_browser_reload")

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    # Compress responses to reduce payload size
    "django.middleware.gzip.GZipMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "web.middleware.HostnameRewriteMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "allauth.account.middleware.AccountMiddleware",
    "web.middleware.WebRequestMiddleware",
    # "web.middleware.GlobalExceptionMiddleware",
]

if DEBUG and not TESTING:
    MIDDLEWARE.insert(-2, "django_browser_reload.middleware.BrowserReloadMiddleware")

ROOT_URLCONF = "web.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "web/templates"],
        # Use cached loaders in production to avoid repeated template parsing
        "APP_DIRS": DEBUG,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "web.context_processors.last_modified",
            ],
            **(
                {}
                if DEBUG
                else {
                    "loaders": [
                        (
                            "django.template.loaders.cached.Loader",
                            [
                                "django.template.loaders.filesystem.Loader",
                                "django.template.loaders.app_directories.Loader",
                            ],
                        )
                    ]
                }
            ),
        },
    },
]

CAPTCHA_FONT_SIZE = 28
CAPTCHA_IMAGE_SIZE = (150, 40)
CAPTCHA_LETTER_ROTATION = (-20, 20)
CAPTCHA_BACKGROUND_COLOR = "#f0f8ff"
CAPTCHA_FOREGROUND_COLOR = "#2f4f4f"
CAPTCHA_NOISE_FUNCTIONS = ("captcha.helpers.noise_arcs", "captcha.helpers.noise_dots")
CAPTCHA_FILTER_FUNCTIONS = ("captcha.helpers.post_smooth",)
CAPTCHA_2X_IMAGE = True
CAPTCHA_TEST_MODE = False

WSGI_APPLICATION = "web.wsgi.application"

# Add ASGI application configuration
ASGI_APPLICATION = "web.asgi.application"

# Channels / Redis channel layer configuration (assumes a local Redis unless overridden)
REDIS_URL = env.str("REDIS_URL", default="redis://127.0.0.1:6379/0")
CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {"hosts": [REDIS_URL]},
    }
}

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
        # Persist DB connections to avoid reconnect overhead in production
        "CONN_MAX_AGE": 300 if not DEBUG else 0,
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]

SITE_ID = 1
SITE_NAME = "AlphaOne Labs"
SITE_DOMAIN = "alphaonelabs.com"

# Allauth settings
ACCOUNT_EMAIL_REQUIRED = True
ACCOUNT_USERNAME_REQUIRED = False  # Since we're using email authentication
ACCOUNT_EMAIL_VERIFICATION = "mandatory"  # Require email verification
ACCOUNT_LOGIN_METHODS = {"email"}
ACCOUNT_UNIQUE_EMAIL = True
ACCOUNT_PREVENT_ENUMERATION = True  # Prevent user enumeration
ACCOUNT_USERNAME_MIN_LENGTH = 3
ACCOUNT_LOGIN_ON_EMAIL_CONFIRMATION = True
ACCOUNT_SESSION_REMEMBER = None  # Let user decide via checkbox
ACCOUNT_REMEMBER_ME_FIELD = "remember"  # Match test field name
ACCOUNT_LOGIN_ON_PASSWORD_RESET = True
ACCOUNT_SIGNUP_PASSWORD_ENTER_TWICE = False
ACCOUNT_LOGOUT_ON_GET = True
ACCOUNT_SIGNUP_EMAIL_ENTER_TWICE = False
ACCOUNT_LOGOUT_ON_PASSWORD_CHANGE = False
ACCOUNT_OLD_PASSWORD_FIELD_ENABLED = True
ACCOUNT_EMAIL_AUTHENTICATION = True  # Enable email authentication
ACCOUNT_EMAIL_CONFIRMATION_AUTHENTICATED_REDIRECT_URL = "index"
ACCOUNT_EMAIL_CONFIRMATION_ANONYMOUS_REDIRECT_URL = "account_login"

# Authentication backends
AUTHENTICATION_BACKENDS = [
    "django.contrib.auth.backends.ModelBackend",
    "allauth.account.auth_backends.AuthenticationBackend",
]

# Authentication URLs
LOGIN_URL = "account_login"
LOGIN_REDIRECT_URL = "index"
LOGOUT_REDIRECT_URL = "index"

ACCOUNT_RATE_LIMITS = {
    "login_attempt": "5/5m",  # 5 attempts per 5 minutes
    "login_failed": "3/5m",  # 3 failed attempts per 5 minutes
    "signup": "5/h",  # 5 signups per hour
    "send_email": "5/5m",  # 5 emails per 5 minutes
    "change_email": "3/h",  # 3 email changes per hour
}

# Override allauth forms
ACCOUNT_FORMS = {
    "signup": "web.forms.UserRegistrationForm",
    "login": "web.forms.CustomLoginForm",
}

LANGUAGE_CODE = "en"

TIME_ZONE = "UTC"

USE_I18N = True

USE_TZ = True


STATIC_URL = "/static/"


DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

"""
Media files configuration

Previously MEDIA_ROOT for production was hard-coded to the legacy PythonAnywhere
path (/home/alphaonelabs99282llkb/web/media). That prevented the live server
from locating media we now place under the project directory on the new VPS.

We switch to an environment-variable override with a sane default pointing to
<project>/media for both dev and prod (unless a cloud storage backend is
configured later). This keeps URLs stable (/media/...) while aligning file
paths with the Nginx alias in ansible/nginx-http.conf.j2:
    location /media/ { alias /home/django/education-website/media/; }

If GS_BUCKET_NAME is set above, DEFAULT_FILE_STORAGE will override this with
Google Cloud Storage; in that case MEDIA_ROOT is less relevant.
"""
MEDIA_ROOT = env.str("MEDIA_ROOT", default=str(BASE_DIR / "media"))
MEDIA_URL = "/media/"

STATIC_ROOT = os.path.join(BASE_DIR, "staticfiles")
STATICFILES_DIRS = [BASE_DIR / "static"]
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

# Caching configuration: shared Redis backend for multi-worker consistency.
# Falls back to LocMemCache during tests or when Redis is unavailable.
if TESTING:
    # Always use LocMemCache during tests
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": "unique-snowflake",
        }
    }
else:
    try:
        import redis

        redis_client = redis.from_url(REDIS_URL, socket_connect_timeout=1)
        redis_client.ping()
        CACHES = {
            "default": {
                "BACKEND": "django_redis.cache.RedisCache",
                "LOCATION": REDIS_URL,
                "TIMEOUT": 300,
                "OPTIONS": {"CLIENT_CLASS": "django_redis.client.DefaultClient"},
            }
        }
    except (redis.ConnectionError, redis.TimeoutError, Exception):
        # Fallback to in-memory cache when Redis unavailable (e.g., Docker build)
        CACHES = {
            "default": {
                "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
                "LOCATION": "unique-snowflake",
            }
        }

# Cache middleware settings (usable when wrapping views or enabling site-wide cache)
CACHE_MIDDLEWARE_ALIAS = "default"
CACHE_MIDDLEWARE_SECONDS = int(os.getenv("CACHE_MIDDLEWARE_SECONDS", "300"))
CACHE_MIDDLEWARE_KEY_PREFIX = os.getenv("CACHE_MIDDLEWARE_KEY_PREFIX", "aol")

# Use cached sessions in normal runtime to reduce DB hits; keep default during tests
if not TESTING:
    SESSION_ENGINE = "django.contrib.sessions.backends.cached_db"

# Drop noisy Invalid Host messages from logs entirely
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "null": {"class": "logging.NullHandler"},
        # Ensure any accidental use of 'mail_admins' will be a no-op
        "mail_admins": {"class": "logging.NullHandler"},
    },
    "loggers": {
        # Django emits DisallowedHost on invalid/missing Host header; silence it
        "django.security.DisallowedHost": {
            "handlers": ["null"],
            "level": "ERROR",
            "propagate": False,
        },
        # Do not email admins on request/server errors
        "django.request": {
            "handlers": ["null"],
            "level": "ERROR",
            "propagate": False,
        },
        "django.server": {
            "handlers": ["null"],
            "level": "ERROR",
            "propagate": False,
        },
    },
}

# Email settings
if DEBUG:
    EMAIL_BACKEND = "web.email_backend.SlackNotificationEmailBackend"
    print("Using console email backend with Slack notifications for development")
    DEFAULT_FROM_EMAIL = "noreply@example.com"  # Default for development
    MAILGUN_SENDING_KEY = None  # Not needed in development
else:
    # Production email settings
    EMAIL_BACKEND = "web.email_backend.SlackNotificationEmailBackend"
    MAILGUN_SENDING_KEY = env.str("MAILGUN_SENDING_KEY", default="")
    # Optional: set MAILGUN_DOMAIN explicitly; otherwise inferred from DEFAULT_FROM_EMAIL
    MAILGUN_DOMAIN = env.str("MAILGUN_DOMAIN", default="") or None
    DEFAULT_FROM_EMAIL = env.str("EMAIL_FROM", default="noreply@alphaonelabs.com")
    EMAIL_FROM = os.getenv("EMAIL_FROM")

# Stripe settings
STRIPE_PUBLISHABLE_KEY = env("STRIPE_PUBLISHABLE_KEY", default="")
STRIPE_SECRET_KEY = env("STRIPE_SECRET_KEY", default="")
STRIPE_WEBHOOK_SECRET = env("STRIPE_WEBHOOK_SECRET", default="")

# Social Media and Content API Settings
MAILCHIMP_API_KEY = env.str("MAILCHIMP_API_KEY", default="")
MAILCHIMP_LIST_ID = env.str("MAILCHIMP_LIST_ID", default="")

INSTAGRAM_ACCESS_TOKEN = env.str("INSTAGRAM_ACCESS_TOKEN", default="")
FACEBOOK_ACCESS_TOKEN = env.str("FACEBOOK_ACCESS_TOKEN", default="")

GITHUB_ACCESS_TOKEN = env.str("GITHUB_ACCESS_TOKEN", default="")
GITHUB_REPO = env.str("GITHUB_REPO", default="AlphaOneLabs/education-website")

YOUTUBE_API_KEY = env.str("YOUTUBE_API_KEY", default="")
YOUTUBE_CHANNEL_ID = env.str("YOUTUBE_CHANNEL_ID", default="")

TWITTER_USERNAME = env.str("TWITTER_USERNAME", default="alphaonelabs")

# Slack Integration
SLACK_WEBHOOK_URL = env.str("SLACK_WEBHOOK_URL", default="")

# Slack webhook for email notifications
EMAIL_SLACK_WEBHOOK = env.str("EMAIL_SLACK_WEBHOOK", default=SLACK_WEBHOOK_URL)

LANGUAGES = [
    ("en", "English"),
    ("es", "Spanish"),
    ("fr", "French"),
    ("de", "German"),
    ("zh-hans", "Simplified Chinese"),
]

LOCALE_PATHS = [
    BASE_DIR / "locale",
]

USE_L10N = True

if os.environ.get("DATABASE_URL"):
    DATABASES = {"default": env.db()}

    # Only add MySQL-specific options if using MySQL
    if DATABASES["default"]["ENGINE"] == "django.db.backends.mysql":
        DATABASES["default"]["OPTIONS"] = {
            "charset": "utf8mb4",
            "sql_mode": (
                "STRICT_TRANS_TABLES,"
                "NO_ZERO_IN_DATE,"
                "NO_ZERO_DATE,"
                "ERROR_FOR_DIVISION_BY_ZERO,"
                "NO_ENGINE_SUBSTITUTION"
            ),
            "init_command": "SET NAMES 'utf8mb4' COLLATE 'utf8mb4_unicode_ci'",
        }

    # Google Cloud Storage settings for media files in production
    if os.environ.get("GS_BUCKET_NAME"):
        DEFAULT_FILE_STORAGE = "storages.backends.gcloud.GoogleCloudStorage"
        GS_BUCKET_NAME = os.environ.get("GS_BUCKET_NAME")
        GS_PROJECT_ID = os.environ.get("GS_PROJECT_ID")

        # Get service account file path from .env
        service_account_filename = env.str("SERVICE_ACCOUNT_FILE")
        SERVICE_ACCOUNT_FILE = os.path.join(BASE_DIR, service_account_filename)
        if os.path.exists(SERVICE_ACCOUNT_FILE):
            from google.oauth2 import service_account

            GS_CREDENTIALS = service_account.Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE)
        else:
            print(f"Warning: Service account file not found at {SERVICE_ACCOUNT_FILE}")
            GS_CREDENTIALS = None

        GS_DEFAULT_ACL = "publicRead"
        GS_QUERYSTRING_AUTH = False
        GS_LOCATION = "media"  # Store files in a media directory in the bucket


# Admin URL Configuration
ADMIN_URL = env.str("ADMIN_URL", default="a-dmin-url123")

# Markdownx configuration
MARKDOWNX_MARKDOWN_EXTENSIONS = [
    "markdown.extensions.extra",
    "markdown.extensions.codehilite",
    "markdown.extensions.tables",
    "markdown.extensions.toc",
]

MARKDOWNX_URLS_PATH = "/markdownx/markdownify/"
MARKDOWNX_UPLOAD_URLS_PATH = "/markdownx/upload/"
MARKDOWNX_MEDIA_PATH = "markdownx/"  # Path within MEDIA_ROOT

USE_X_FORWARDED_HOST = True

# GitHub API Token for fetching contributor data
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")


# Allow per-environment override of secure cookie behavior (useful for staging without HTTPS).
CSRF_COOKIE_SECURE = env.bool("CSRF_COOKIE_SECURE", default=not DEBUG)
SESSION_COOKIE_SECURE = env.bool("SESSION_COOKIE_SECURE", default=not DEBUG)
GITHUB_WEBHOOK_SECRET = os.environ.get("GITHUB_WEBHOOK_SECRET", "")
