#!/usr/bin/env bash
# =============================================================================
# dev.sh - Unified development script for Alpha One Labs
#
# Usage:
#   ./scripts/dev.sh setup    - Install dependencies and setup environment
#   ./scripts/dev.sh run      - Start the local development server
#   ./scripts/dev.sh doctor   - Diagnose common environment problems
# =============================================================================
set -euo pipefail

COMMAND="${1:-run}"

# -- Colours & helpers --------------------------------------------------------
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; BLUE='\033[0;34m'
CYAN='\033[0;36m'; BOLD='\033[1m'; NC='\033[0m'

info()  { echo -e "${BLUE}${BOLD}$1${NC}"; }
ok()    { echo -e "${GREEN}  ✔ $1${NC}"; PASS=$((PASS + 1)); }
warn()  { echo -e "${YELLOW}  ⚠ $1${NC}"; WARN=$((WARN + 1)); }
fail()  { echo -e "${RED}  ✖ $1${NC}"; FAIL=$((FAIL + 1)); }
die()   { fail "$1"; echo -e "${RED}    → $2${NC}"; exit 1; }
fix()   { echo -e "    ${BLUE}→ Fix:${NC} $1"; }
step()  { echo -e "\n${BOLD}[$1/7] $2${NC}"; }

PASS=0; WARN=0; FAIL=0

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# If the script is in root (./scripts/dev.sh), SCRIPT_DIR is the project root.
# If the script is in scripts/ (./scripts/dev.sh), project root is ..
if [ -f "${SCRIPT_DIR}/manage.py" ]; then
    PROJECT_ROOT="${SCRIPT_DIR}"
else
    PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
fi
cd "${PROJECT_ROOT}"

# =============================================================================
# SETUP
# =============================================================================
function cmd_setup() {
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
echo -e "  Start the dev server:  ${BOLD}./scripts/dev.sh run${NC}"
echo -e "  Run diagnostics:       ${BOLD}./scripts/dev.sh doctor${NC}"
echo -e "  Run tests:             ${BOLD}./scripts/dev.sh test${NC}"
echo ""
echo -e "  Admin login:           admin@example.com / adminpassword"
echo -e "  Dev server URL:        http://localhost:8000"
echo ""
}

# =============================================================================
# RUN
# =============================================================================
function cmd_run() {
# -- Pre-flight checks --------------------------------------------------------
info "Pre-flight checks..."

# Ensure .env exists
if [ ! -f "${PROJECT_ROOT}/.env" ]; then
    fail ".env file not found. Run './scripts/dev.sh setup' first."
    return 1
fi
ok ".env file found"

# Detect Python from the Poetry venv or fall back to system python
if [ -f "${PROJECT_ROOT}/.venv/bin/python" ]; then
    PYTHON="${PROJECT_ROOT}/.venv/bin/python"
elif command -v poetry &>/dev/null; then
    PYTHON="$(poetry env info -e 2>/dev/null || echo python3)"
else
    PYTHON="python3"
fi
ok "Python: ${PYTHON}"

# Check if port 8000 is already in use
if command -v lsof &>/dev/null; then
    if lsof -Pi :8000 -sTCP:LISTEN -t &>/dev/null; then
        warn "Port 8000 is already in use — the server may fail to bind."
        warn "Run './scripts/dev.sh doctor' for help, or kill the process on port 8000."
    fi
fi

# Optional: Check Redis connectivity (non-blocking)
REDIS_URL=$(grep '^REDIS_URL=' "${PROJECT_ROOT}/.env" 2>/dev/null | cut -d= -f2- || echo "")
if [ -n "${REDIS_URL}" ] && [ "${REDIS_URL}" != "redis://127.0.0.1:6379/0" ]; then
    # Custom Redis URL configured — warn if it's unreachable
    if command -v redis-cli &>/dev/null; then
        if ! redis-cli -u "${REDIS_URL}" ping &>/dev/null 2>&1; then
            REDACTED_URL=$(echo "${REDIS_URL}" | sed -E 's|://[^@]+@|://REDACTED@|')
            warn "Redis at ${REDACTED_URL} is not reachable."
            warn "WebSocket features (chat, whiteboard) won't work without Redis."
        else
            ok "Redis is reachable"
        fi
    fi
elif command -v redis-cli &>/dev/null; then
    if redis-cli ping &>/dev/null 2>&1; then
        ok "Redis is reachable (localhost)"
    else
        warn "Redis is not running locally. WebSocket features won't work."
        warn "Start Redis with: redis-server  OR  docker run -d -p 6379:6379 redis:7-alpine"
    fi
else
    warn "Redis CLI not found — skipping Redis check."
    warn "WebSocket features (chat, whiteboard) require Redis at runtime."
fi

# -- Collect static files (quick, idempotent) ---------------------------------
info "Collecting static files..."
if "${PYTHON}" manage.py collectstatic --noinput --verbosity=0 2>&1; then
    ok "Static files ready"
else
    fail "collectstatic failed. See output above."
    return 1
fi

# -- Trap Ctrl+C for clean shutdown -------------------------------------------
cleanup() {
    echo ""
    echo -e "${YELLOW}Shutting down...${NC}"
    # Kill all child processes in this process group
    kill -- -$$ 2>/dev/null || true
    return 0
}
trap cleanup INT TERM

# -- Start the development server ---------------------------------------------
echo ""
echo -e "${GREEN}${BOLD}══════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}${BOLD}  Alpha One Labs — Development Server${NC}"
echo -e "${GREEN}${BOLD}══════════════════════════════════════════════════════════${NC}"
echo ""
echo -e "  ${CYAN}Local:${NC}   http://localhost:8000"
echo -e "  ${CYAN}Network:${NC} http://0.0.0.0:8000"
echo -e "  ${CYAN}Admin:${NC}   http://localhost:8000/a-dmin-url123/"
echo ""

# Start Django dev server — filter out startup noise so the banner above
# stays as the last visible output. Request logs still pass through.
"${PYTHON}" manage.py runserver 0.0.0.0:8000 2> >(cat >&2) \
    | grep --line-buffered -v -E "^(Watching for file changes with StatReloader|Performing system checks\.\.\.|System check identified no issues|Django version [0-9]|Starting development server at|Quit the server with CONTROL-C\.|$)"
}

# =============================================================================
# DOCTOR
# =============================================================================
function cmd_doctor() {
    PASS=0; WARN=0; FAIL=0

echo ""
echo -e "${BOLD}╔══════════════════════════════════════════════════════╗${NC}"
echo -e "${BOLD}║        Alpha One Labs — Environment Doctor          ║${NC}"
echo -e "${BOLD}╚══════════════════════════════════════════════════════╝${NC}"
echo ""

# =============================================================================
# 1. Python version
# =============================================================================
echo -e "${BOLD}Python${NC}"

if command -v python3 &>/dev/null; then
    PY_VER=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}")')
    PY_MAJOR=$(python3 -c 'import sys; print(sys.version_info.major)')
    PY_MINOR=$(python3 -c 'import sys; print(sys.version_info.minor)')
    if [ "${PY_MAJOR}" -gt 3 ] || { [ "${PY_MAJOR}" -eq 3 ] && [ "${PY_MINOR}" -ge 10 ]; }; then
        ok "Python ${PY_VER} (≥ 3.10 required)"
    else
        fail "Python ${PY_VER} found — 3.10+ is required"
        fix "Install Python 3.10+ from https://www.python.org/downloads/"
    fi
else
    fail "Python 3 is not installed"
    fix "Install Python 3.10+ from https://www.python.org/downloads/"
fi

# =============================================================================
# 2. Poetry
# =============================================================================
echo ""
echo -e "${BOLD}Package Manager${NC}"

if command -v poetry &>/dev/null; then
    POETRY_VER=$(poetry --version 2>/dev/null | grep -oE '[0-9]+\.[0-9]+\.[0-9]+')
    ok "Poetry ${POETRY_VER}"
else
    fail "Poetry is not installed"
    fix "pip install poetry==1.8.3"
fi

# =============================================================================
# 3. Virtual environment
# =============================================================================
echo ""
echo -e "${BOLD}Virtual Environment${NC}"

if [ -d "${PROJECT_ROOT}/.venv" ]; then
    ok ".venv directory exists"
    if [ -f "${PROJECT_ROOT}/.venv/bin/python" ]; then
        VENV_PY=$("${PROJECT_ROOT}/.venv/bin/python" --version 2>&1)
        ok "venv Python: ${VENV_PY}"
    else
        warn ".venv exists but python binary not found"
        fix "Run: ./scripts/dev.sh setup"
    fi
else
    warn "No .venv directory — dependencies may not be installed"
    fix "Run: ./scripts/dev.sh setup"
fi

# macOS Gatekeeper quarantine check
if [[ "$OSTYPE" == "darwin"* ]] && [ -d "${PROJECT_ROOT}/.venv" ]; then
    QUARANTINED=$(find "${PROJECT_ROOT}/.venv" -name '*.so' -exec /usr/bin/xattr -l {} \; 2>/dev/null | grep -c 'com.apple.quarantine' || true)
    if [ "${QUARANTINED}" -gt 0 ]; then
        fail "${QUARANTINED} .so file(s) in .venv are quarantined by macOS Gatekeeper"
        fix "Run: ./scripts/dev.sh setup  (it clears quarantine automatically)"
    else
        ok "No quarantined files in .venv"
    fi
fi

# =============================================================================
# 4. Environment file
# =============================================================================
echo ""
echo -e "${BOLD}Environment Configuration${NC}"

if [ -f "${PROJECT_ROOT}/.env" ]; then
    ok ".env file exists"

    # Check critical keys
    SECRET_KEY=$(grep '^SECRET_KEY=' "${PROJECT_ROOT}/.env" | cut -d= -f2-)
    if [ "${SECRET_KEY}" = "your-secret-key-here" ] || [ -z "${SECRET_KEY}" ]; then
        fail "SECRET_KEY is not configured"
        fix "Run: ./scripts/dev.sh setup  (it generates secrets automatically)"
    else
        ok "SECRET_KEY is set"
    fi

    ENV_MODE=$(grep '^ENVIRONMENT=' "${PROJECT_ROOT}/.env" | cut -d= -f2-)
    if [ "${ENV_MODE}" = "development" ]; then
        ok "ENVIRONMENT=development"
    else
        warn "ENVIRONMENT=${ENV_MODE} (expected 'development' for local dev)"
        fix "Set ENVIRONMENT=development in .env"
    fi
else
    fail ".env file is missing"
    fix "Run: ./scripts/dev.sh setup  OR  cp .env.sample .env"
fi

# =============================================================================
# 5. Database
# =============================================================================
echo ""
echo -e "${BOLD}Database${NC}"

DB_URL=$(grep '^DATABASE_URL=' "${PROJECT_ROOT}/.env" 2>/dev/null | cut -d= -f2- || echo "")
if [ -z "${DB_URL}" ] || [[ "${DB_URL}" == *"sqlite"* ]]; then
    if [ -f "${PROJECT_ROOT}/db.sqlite3" ]; then
        DB_SIZE=$(du -h "${PROJECT_ROOT}/db.sqlite3" | cut -f1)
        ok "SQLite database exists (${DB_SIZE})"
    else
        warn "SQLite database does not exist yet"
        fix "Run: ./scripts/dev.sh setup  (it runs migrations automatically)"
    fi
else
    ok "DATABASE_URL is configured (non-SQLite)"
fi

# =============================================================================
# 6. Port 8000
# =============================================================================
echo ""
echo -e "${BOLD}Network${NC}"

if command -v lsof &>/dev/null; then
    PORT_PID=$(lsof -Pi :8000 -sTCP:LISTEN -t 2>/dev/null || echo "")
    if [ -n "${PORT_PID}" ]; then
        PORT_CMD=$(ps -p "${PORT_PID}" -o comm= 2>/dev/null || echo "unknown")
        fail "Port 8000 is in use by PID ${PORT_PID} (${PORT_CMD})"
        fix "Kill it with: kill ${PORT_PID}"
    else
        ok "Port 8000 is available"
    fi
elif command -v ss &>/dev/null; then
    if ss -tlnp 2>/dev/null | grep -q ':8000 '; then
        fail "Port 8000 is in use"
        fix "Find the process: ss -tlnp | grep :8000  then kill it"
    else
        ok "Port 8000 is available"
    fi
else
    warn "Cannot check port 8000 (lsof/ss not available)"
fi

# =============================================================================
# 7. Docker (optional)
# =============================================================================
echo ""
echo -e "${BOLD}Docker (optional)${NC}"

if command -v docker &>/dev/null; then
    if docker info &>/dev/null 2>&1; then
        ok "Docker is running"
    else
        warn "Docker is installed but not running"
        fix "Start Docker Desktop or run: sudo systemctl start docker"
    fi
else
    warn "Docker is not installed (optional — needed for docker-compose.dev.yml)"
    fix "Install from https://docs.docker.com/get-docker/"
fi

# =============================================================================
# 8. Redis (optional)
# =============================================================================
echo ""
echo -e "${BOLD}Redis (optional — for WebSocket features)${NC}"

if command -v redis-cli &>/dev/null; then
    if redis-cli ping &>/dev/null 2>&1; then
        REDIS_VER=$(redis-cli info server 2>/dev/null | grep redis_version | cut -d: -f2 | tr -d '\r')
        ok "Redis is running (${REDIS_VER})"
    else
        warn "Redis CLI found but server is not reachable"
        fix "Start Redis: redis-server  OR  docker run -d -p 6379:6379 redis:7-alpine"
    fi
else
    warn "Redis is not installed"
    fix "brew install redis  OR  docker run -d -p 6379:6379 redis:7-alpine"
fi

# =============================================================================
# Summary
# =============================================================================
echo ""
echo -e "${BOLD}─────────────────────────────────────────────────${NC}"
TOTAL=$((PASS + WARN + FAIL))
echo -e "  Results: ${GREEN}${PASS} passed${NC}, ${YELLOW}${WARN} warnings${NC}, ${RED}${FAIL} failed${NC} (${TOTAL} checks)"
echo ""

if [ "${FAIL}" -gt 0 ]; then
    echo -e "  ${RED}${BOLD}Some checks failed.${NC} Fix the issues above and run ${BOLD}./scripts/dev.sh doctor${NC} again."
    return 1
elif [ "${WARN}" -gt 0 ]; then
    echo -e "  ${YELLOW}${BOLD}Looks mostly good!${NC} Warnings are optional but recommended to fix."
    return 0
else
    echo -e "  ${GREEN}${BOLD}Everything looks great! 🎉${NC}"
    return 0
fi
}

case "$COMMAND" in
    setup)  cmd_setup ;;
    run)    cmd_run ;;
    doctor) cmd_doctor ;;
    *)      echo "Usage: $0 {setup|run|doctor}"; exit 1 ;;
esac
