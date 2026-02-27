#!/usr/bin/env bash
# =============================================================================
# dev.sh — Start the local development server
#
# Usage:  npm run dev   OR   bash scripts/dev.sh
#
# Starts Django's development server with hot-reload. Optionally checks Redis
# availability if Redis-backed channels are configured. Stops cleanly on Ctrl+C.
# =============================================================================
set -euo pipefail

# -- Colours & helpers --------------------------------------------------------
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; BLUE='\033[0;34m'
CYAN='\033[0;36m'; BOLD='\033[1m'; NC='\033[0m'

info()  { echo -e "${BLUE}${BOLD}$1${NC}"; }
ok()    { echo -e "${GREEN}  ✔ $1${NC}"; }
warn()  { echo -e "${YELLOW}  ⚠ $1${NC}"; }
fail()  { echo -e "${RED}  ✖ $1${NC}"; }

# -- Resolve project root -----------------------------------------------------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "${PROJECT_ROOT}"

# -- Pre-flight checks --------------------------------------------------------
info "Pre-flight checks..."

# Ensure .env exists
if [ ! -f "${PROJECT_ROOT}/.env" ]; then
    fail ".env file not found. Run 'npm run setup' first."
    exit 1
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
        warn "Run 'npm run doctor' for help, or kill the process on port 8000."
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
    exit 1
fi

# -- Trap Ctrl+C for clean shutdown -------------------------------------------
cleanup() {
    echo ""
    echo -e "${YELLOW}Shutting down...${NC}"
    # Kill all child processes in this process group
    kill -- -$$ 2>/dev/null || true
    exit 0
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
"${PYTHON}" manage.py runserver 0.0.0.0:8000 2>&1 \
    | grep --line-buffered -v -E "^(Watching for file changes|Performing system checks|System check identified|Django version|Starting development server|Quit the server with|$)"
