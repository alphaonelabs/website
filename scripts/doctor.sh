#!/usr/bin/env bash
# =============================================================================
# doctor.sh — Diagnose common development environment problems
#
# Usage:  npm run doctor   OR   bash scripts/doctor.sh
#
# Checks for common issues and prints human-readable fixes, not stack traces.
# =============================================================================
set -uo pipefail

# -- Colours & helpers --------------------------------------------------------
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; BLUE='\033[0;34m'
BOLD='\033[1m'; NC='\033[0m'

ok()    { echo -e "  ${GREEN}✔${NC} $1"; PASS=$((PASS + 1)); }
warn()  { echo -e "  ${YELLOW}⚠${NC} $1"; WARN=$((WARN + 1)); }
fail()  { echo -e "  ${RED}✖${NC} $1"; FAIL=$((FAIL + 1)); }
fix()   { echo -e "    ${BLUE}→ Fix:${NC} $1"; }

PASS=0; WARN=0; FAIL=0

# -- Resolve project root -----------------------------------------------------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "${PROJECT_ROOT}"

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
    if [ "${PY_MAJOR}" -ge 3 ] && [ "${PY_MINOR}" -ge 10 ]; then
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
        fix "Run: npm run setup"
    fi
else
    warn "No .venv directory — dependencies may not be installed"
    fix "Run: npm run setup"
fi

# macOS Gatekeeper quarantine check
if [[ "$OSTYPE" == "darwin"* ]] && [ -d "${PROJECT_ROOT}/.venv" ]; then
    QUARANTINED=$(find "${PROJECT_ROOT}/.venv" -name '*.so' -exec /usr/bin/xattr -l {} \; 2>/dev/null | grep -c 'com.apple.quarantine' || true)
    if [ "${QUARANTINED}" -gt 0 ]; then
        fail "${QUARANTINED} .so file(s) in .venv are quarantined by macOS Gatekeeper"
        fix "Run: npm run setup  (it clears quarantine automatically)"
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
        fix "Run: npm run setup  (it generates secrets automatically)"
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
    fix "Run: npm run setup  OR  cp .env.sample .env"
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
        fix "Run: npm run setup  (it runs migrations automatically)"
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
    echo -e "  ${RED}${BOLD}Some checks failed.${NC} Fix the issues above and run ${BOLD}npm run doctor${NC} again."
    exit 1
elif [ "${WARN}" -gt 0 ]; then
    echo -e "  ${YELLOW}${BOLD}Looks mostly good!${NC} Warnings are optional but recommended to fix."
    exit 0
else
    echo -e "  ${GREEN}${BOLD}Everything looks great! 🎉${NC}"
    exit 0
fi
