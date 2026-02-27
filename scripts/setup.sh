#!/usr/bin/env bash
# =============================================================================
# setup.sh — Idempotent local development setup for Alpha One Labs
#
# Usage:  npm run setup   OR   bash scripts/setup.sh
#
# This script is safe to run repeatedly. It will never overwrite user files
# (.env, db.sqlite3) and will skip steps that are already completed.
#
# Requirements: Python 3.10+, pip (Poetry is installed automatically if missing)
# Optional:     Docker (for Redis/MySQL), Redis CLI
# =============================================================================
set -euo pipefail

# -- Colours & helpers --------------------------------------------------------
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; BLUE='\033[0;34m'
BOLD='\033[1m'; NC='\033[0m'

info()  { echo -e "${BLUE}${BOLD}$1${NC}"; }
ok()    { echo -e "${GREEN}  ✔ $1${NC}"; }
warn()  { echo -e "${YELLOW}  ⚠ $1${NC}"; }
fail()  { echo -e "${RED}  ✖ $1${NC}"; }
die()   { fail "$1"; echo -e "${RED}    → $2${NC}"; exit 1; }

TOTAL_STEPS=7
step()  { echo -e "\n${BOLD}[$1/${TOTAL_STEPS}] $2${NC}"; }

# -- Resolve project root (script lives in <root>/scripts/) -------------------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "${PROJECT_ROOT}"

# =============================================================================
# Step 1 — Check required software versions
# =============================================================================
step 1 "Checking dependencies..."

# Python ≥ 3.10
if ! command -v python3 &>/dev/null; then
    die "Python 3 is not installed." \
        "Install Python 3.10+ from https://www.python.org/downloads/"
fi

PYTHON_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
PYTHON_MAJOR=$(echo "${PYTHON_VERSION}" | cut -d. -f1)
PYTHON_MINOR=$(echo "${PYTHON_VERSION}" | cut -d. -f2)

if [ "${PYTHON_MAJOR}" -lt 3 ] || { [ "${PYTHON_MAJOR}" -eq 3 ] && [ "${PYTHON_MINOR}" -lt 10 ]; }; then
    die "Python ${PYTHON_VERSION} found, but 3.10+ is required." \
        "Install Python 3.10+ from https://www.python.org/downloads/"
fi
ok "Python ${PYTHON_VERSION}"

# pip
if ! python3 -m pip --version &>/dev/null; then
    die "pip is not available." \
        "Run: python3 -m ensurepip --upgrade"
fi
ok "pip available"

# Poetry (install automatically if missing, and handle PATH issues)
POETRY_CMD=""
if command -v poetry &>/dev/null; then
    POETRY_CMD="poetry"
else
    warn "Poetry not found — installing Poetry 2.3.2..."
    python3 -m pip install --quiet poetry==2.3.2 2>&1 || true

    # pip may install the binary to a user-local scripts dir not on PATH.
    # Common locations: ~/.local/bin (Linux), ~/Library/Python/X.Y/bin (macOS)
    if command -v poetry &>/dev/null; then
        POETRY_CMD="poetry"
    else
        # Search common pip script directories
        for candidate in \
            "$HOME/.local/bin/poetry" \
            "$HOME/Library/Python/${PYTHON_VERSION}/bin/poetry" \
            "$(python3 -c 'import sysconfig; print(sysconfig.get_path("scripts", "posix_user"))' 2>/dev/null)/poetry"
        do
            if [ -x "${candidate}" ]; then
                export PATH="$(dirname "${candidate}"):${PATH}"
                POETRY_CMD="poetry"
                ok "Added $(dirname "${candidate}") to PATH"
                break
            fi
        done

        # Last resort: run poetry as a Python module
        if [ -z "${POETRY_CMD}" ] && python3 -c "import poetry" &>/dev/null; then
            POETRY_CMD="python3 -m poetry"
            ok "Using poetry via: python3 -m poetry"
        fi
    fi
fi

if [ -z "${POETRY_CMD}" ]; then
    die "Could not find or install Poetry." \
        "Install manually: pip install poetry==2.3.2  and ensure it's on your PATH"
fi

POETRY_VERSION=$(${POETRY_CMD} --version 2>/dev/null | grep -oE '[0-9]+\.[0-9]+\.[0-9]+')
ok "Poetry ${POETRY_VERSION}"

if [ "$(echo "${POETRY_VERSION}" | cut -d. -f1)" -ge 2 ]; then
    "${POETRY_CMD}" self add poetry-plugin-export 2>/dev/null || true
fi

# Optional: Docker
if command -v docker &>/dev/null; then
    ok "Docker available (optional)"
else
    warn "Docker not found — optional, needed only for docker-compose.dev.yml"
fi

# Optional: Redis CLI
if command -v redis-cli &>/dev/null; then
    ok "Redis CLI available (optional)"
else
    warn "Redis CLI not found — optional, WebSocket features need Redis at runtime"
fi

# =============================================================================
# Step 2 — Install Python dependencies via Poetry
# =============================================================================
step 2 "Installing packages..."

# Ensure Poetry creates a virtualenv (override the repo's poetry.toml which
# sets create=false — that setting is intended for Docker/CI, not local dev).
"${POETRY_CMD}" config virtualenvs.in-project true --local 2>/dev/null || true

# mysqlclient requires MySQL C headers (mysql_config) to compile.
# On macOS, these come from `brew install mysql-client`.
# For SQLite-only local dev, mysqlclient is not needed at all.
if ! command -v mysql_config &>/dev/null; then
    if [[ "$OSTYPE" == "darwin"* ]] && command -v brew &>/dev/null; then
        warn "mysql_config not found — trying: brew install mysql-client"
        if brew install mysql-client 2>/dev/null; then
            MYSQL_PREFIX="$(brew --prefix mysql-client 2>/dev/null)"
            export PKG_CONFIG_PATH="${MYSQL_PREFIX}/lib/pkgconfig:${PKG_CONFIG_PATH:-}"
            export PATH="${MYSQL_PREFIX}/bin:${PATH}"
            ok "mysql-client installed via Homebrew"
        else
            warn "brew install mysql-client failed — will skip mysqlclient package"
        fi
    else
        warn "mysql_config not found — mysqlclient will be skipped (not needed for SQLite)"
    fi
fi

# Try poetry install; if it fails (usually due to mysqlclient), fall back to
# installing everything except mysqlclient via pip.
if "${POETRY_CMD}" install --no-interaction --no-ansi 2>&1 | tail -5; then
    ok "Python dependencies installed"
else
    warn "poetry install failed (likely mysqlclient). Falling back to pip install..."

    # Create the venv manually if poetry didn't
    if [ ! -d "${PROJECT_ROOT}/.venv" ]; then
        python3 -m venv "${PROJECT_ROOT}/.venv"
    fi
    PIP="${PROJECT_ROOT}/.venv/bin/pip"

    # Export requirements from poetry, remove mysqlclient, install the rest
    "${POETRY_CMD}" export --without-hashes --no-interaction 2>/dev/null \
        | grep -v '^mysqlclient' \
        > "${PROJECT_ROOT}/.tmp-requirements.txt"
    "${PIP}" install --quiet -r "${PROJECT_ROOT}/.tmp-requirements.txt"
    rm -f "${PROJECT_ROOT}/.tmp-requirements.txt"

    # Also install dev dependencies
    "${POETRY_CMD}" export --with dev --without-hashes --no-interaction 2>/dev/null \
        | grep -v '^mysqlclient' \
        > "${PROJECT_ROOT}/.tmp-dev-requirements.txt"
    "${PIP}" install --quiet -r "${PROJECT_ROOT}/.tmp-dev-requirements.txt"
    rm -f "${PROJECT_ROOT}/.tmp-dev-requirements.txt"

    ok "Python dependencies installed (mysqlclient skipped — not needed for SQLite)"
fi

# Detect the poetry venv python for subsequent commands
if [ -d "${PROJECT_ROOT}/.venv" ]; then
    PYTHON="${PROJECT_ROOT}/.venv/bin/python"
else
    # Fallback: let poetry figure it out
    PYTHON="$("${POETRY_CMD}" env info -e 2>/dev/null || echo python3)"
fi
ok "Using Python: ${PYTHON}"

# macOS Gatekeeper: Remove quarantine attributes from compiled binaries (.so files)
# like _rust.abi3.so (from cryptography). Without this, macOS may block execution
# with a "Not Opened" security popup.
if [[ "$OSTYPE" == "darwin"* ]] && [ -d "${PROJECT_ROOT}/.venv" ]; then
    find "${PROJECT_ROOT}/.venv" -type f \( -name '*.so' -o -name '*.dylib' \) \
        -exec /usr/bin/xattr -d com.apple.quarantine {} \; 2>/dev/null || true
    ok "Cleared macOS quarantine flags on .venv binaries"
fi

# =============================================================================
# Step 3 — Create .env from .env.sample safely
# =============================================================================
step 3 "Configuring environment..."

if [ -f "${PROJECT_ROOT}/.env" ]; then
    ok ".env already exists — not overwriting"
else
    if [ ! -f "${PROJECT_ROOT}/.env.sample" ]; then
        die ".env.sample is missing from the repository." \
            "Ensure you have a clean checkout."
    fi
    cp "${PROJECT_ROOT}/.env.sample" "${PROJECT_ROOT}/.env"
    ok "Created .env from .env.sample"
fi

# =============================================================================
# Step 4 — Generate secure random secrets
# =============================================================================
step 4 "Generating secrets..."

# Generate a Django SECRET_KEY if it still has the placeholder value
CURRENT_SECRET=$(grep '^SECRET_KEY=' "${PROJECT_ROOT}/.env" | cut -d= -f2-)
if [ "${CURRENT_SECRET}" = "your-secret-key-here" ] || [ -z "${CURRENT_SECRET}" ]; then
    NEW_SECRET=$("${PYTHON}" -c "
import secrets, string
chars = string.ascii_letters + string.digits + '!@#\$%^&*(-_=+)'
print(''.join(secrets.choice(chars) for _ in range(50)))
")
    # Escape special characters (&, \, and |) for the sed replacement string
    ESCAPED_SECRET=$(printf '%s\n' "$NEW_SECRET" | sed -e 's/[\\&|]/\\&/g')
    
    # Use a delimiter that won't conflict with the secret value
    if [[ "$OSTYPE" == "darwin"* ]]; then
        sed -i '' "s|^SECRET_KEY=.*|SECRET_KEY=${ESCAPED_SECRET}|" "${PROJECT_ROOT}/.env"
    else
        sed -i "s|^SECRET_KEY=.*|SECRET_KEY=${ESCAPED_SECRET}|" "${PROJECT_ROOT}/.env"
    fi
    ok "Generated new SECRET_KEY"
else
    ok "SECRET_KEY already set"
fi

# Generate MESSAGE_ENCRYPTION_KEY if it still has the sample value
CURRENT_ENCRYPTION_KEY=$(grep '^MESSAGE_ENCRYPTION_KEY=' "${PROJECT_ROOT}/.env" | cut -d= -f2-)
SAMPLE_KEY="5ezrkqK2lhifqBRt9f8_dZhFQF_f5ipSQDV8Vzv9Dek="
if [ "${CURRENT_ENCRYPTION_KEY}" = "${SAMPLE_KEY}" ] || [ -z "${CURRENT_ENCRYPTION_KEY}" ]; then
    NEW_ENCRYPTION_KEY=$("${PYTHON}" -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")
    # Escape the encryption key in case it contains sed-special characters (though base64 usually doesn't, it's safer)
    ESCAPED_ENCRYPTION_KEY=$(printf '%s\n' "$NEW_ENCRYPTION_KEY" | sed -e 's/[\\&|]/\\&/g')
    
    if [[ "$OSTYPE" == "darwin"* ]]; then
        sed -i '' "s|^MESSAGE_ENCRYPTION_KEY=.*|MESSAGE_ENCRYPTION_KEY=${ESCAPED_ENCRYPTION_KEY}|" "${PROJECT_ROOT}/.env"
    else
        sed -i "s|^MESSAGE_ENCRYPTION_KEY=.*|MESSAGE_ENCRYPTION_KEY=${ESCAPED_ENCRYPTION_KEY}|" "${PROJECT_ROOT}/.env"
    fi
    ok "Generated new MESSAGE_ENCRYPTION_KEY"
else
    ok "MESSAGE_ENCRYPTION_KEY already set"
fi

# Ensure development mode
if [[ "$OSTYPE" == "darwin"* ]]; then
    sed -i '' "s|^ENVIRONMENT=.*|ENVIRONMENT=development|" "${PROJECT_ROOT}/.env"
    sed -i '' "s|^DEBUG=.*|DEBUG=True|" "${PROJECT_ROOT}/.env"
    sed -i '' "s|^DATABASE_URL=.*|DATABASE_URL=sqlite:///db.sqlite3|" "${PROJECT_ROOT}/.env"
else
    sed -i "s|^ENVIRONMENT=.*|ENVIRONMENT=development|" "${PROJECT_ROOT}/.env"
    sed -i "s|^DEBUG=.*|DEBUG=True|" "${PROJECT_ROOT}/.env"
    sed -i "s|^DATABASE_URL=.*|DATABASE_URL=sqlite:///db.sqlite3|" "${PROJECT_ROOT}/.env"
fi
ok "Environment set to development with SQLite"

# =============================================================================
# Step 5 — Run migrations safely
# =============================================================================
step 5 "Running database migrations..."

"${PYTHON}" manage.py migrate --no-input 2>&1 | tail -3
ok "Migrations complete"

# =============================================================================
# Step 6 — Seed minimal demo data
# =============================================================================
step 6 "Seeding demo data..."

# create_test_data is idempotent — it checks for existing data internally
"${PYTHON}" manage.py create_test_data 2>&1 | tail -5
ok "Demo data seeded"

# =============================================================================
# Step 7 — Verify app boots successfully
# =============================================================================
step 7 "Verifying application..."

"${PYTHON}" manage.py check --deploy 2>&1 | tail -3 || true
# The --deploy check may warn about HTTPS settings in dev; that's expected.
# The important thing is that the app loads without ImportError / config issues.
"${PYTHON}" manage.py check 2>&1
ok "Django system check passed"

# -- Done! --------------------------------------------------------------------
echo ""
echo -e "${GREEN}${BOLD}══════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}${BOLD}  ✔ Setup complete!${NC}"
echo -e "${GREEN}${BOLD}══════════════════════════════════════════════════════════${NC}"
echo ""
echo -e "  Start the dev server:  ${BOLD}npm run dev${NC}"
echo -e "  Run diagnostics:       ${BOLD}npm run doctor${NC}"
echo -e "  Run tests:             ${BOLD}npm run test${NC}"
echo ""
echo -e "  Admin login:           admin@example.com / adminpassword"
echo -e "  Dev server URL:        http://localhost:8000"
echo ""
