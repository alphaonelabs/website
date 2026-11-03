#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REPORT_DIR="${A11Y_REPORT_DIR:-$ROOT_DIR/a11y-report}"
PORT="${A11Y_PORT:-8787}"
BASE_URL="${A11Y_BASE_URL:-http://127.0.0.1:$PORT}"
WRANGLER="${WRANGLER_VERSION:-4.40.0}"
SERVER_LOG="${REPORT_DIR}/wrangler.log"
SERVER_PID=""

mkdir -p "$REPORT_DIR"
cd "$ROOT_DIR"

cleanup() {
  if [ -n "$SERVER_PID" ] && kill -0 "$SERVER_PID" 2>/dev/null; then
    kill "$SERVER_PID" 2>/dev/null || true
    wait "$SERVER_PID" 2>/dev/null || true
  fi
}
trap cleanup EXIT INT TERM

echo "Applying learn/schema.sql to the local D1 database..."
npx --yes "wrangler@$WRANGLER" d1 execute education_db --local --file=schema.sql

echo "Starting Wrangler locally..."
npx --yes "wrangler@$WRANGLER" dev --local --port "$PORT" --ip 127.0.0.1 >"$SERVER_LOG" 2>&1 &
SERVER_PID=$!

ready=false
for _ in {1..60}; do
  if curl --fail --silent --show-error "$BASE_URL/status" >/dev/null 2>&1; then
    ready=true
    break
  fi
  if ! kill -0 "$SERVER_PID" 2>/dev/null; then
    echo "Wrangler exited before the local site became ready."
    cat "$SERVER_LOG"
    exit 1
  fi
  sleep 1
done

if [ "$ready" != true ]; then
  echo "Timed out waiting for Wrangler at $BASE_URL."
  cat "$SERVER_LOG"
  exit 1
fi

paths=("/" "/about" "/activity" "/login" "/teach" "/gsoc" "/status" "/privacy" "/terms" "/404")

for path in "${paths[@]}"; do
  slug="${path#/}"
  [ -n "$slug" ] || slug="home"
  report="$REPORT_DIR/$slug.json"
  echo "Scanning $path..."
  if ! npx --yes @axe-core/cli "$BASE_URL$path" \
    --tags wcag2a,wcag2aa,wcag21aa,wcag22aa \
    --chrome-options="--headless --no-sandbox --disable-dev-shm-usage" \
    --save "$report"; then
    echo "Axe scan failed for $path; continuing report-only."
  fi
done

python3 - "$REPORT_DIR" <<'PY'
import json
import sys
from pathlib import Path

report_dir = Path(sys.argv[1])
pages = []

for path in sorted(report_dir.glob("*.json")):
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        print(f"{path.stem}: report could not be parsed ({exc})")
        pages.append({"page": "/" if path.stem == "home" else f"/{path.stem}", "violations": 0, "parse_error": True})
        continue

    violations = []
    if isinstance(data, dict):
        violations = data.get("violations", [])
        if not isinstance(violations, list):
            violations = []
        entries = [data]
    elif isinstance(data, list):
        entries = [entry for entry in data if isinstance(entry, dict)]
        violations = [
            violation
            for entry in entries
            for violation in entry.get("violations", [])
            if isinstance(violation, dict)
        ]
        if not violations:
            violations = [
                violation
                for entry in entries
                for violation in entry.get("violations", [])
            ]
    else:
        entries = []

    page = "/" if path.stem == "home" else f"/{path.stem}"
    pages.append({"page": page, "violations": len(violations)})

summary_lines = ["Accessibility report summary (WCAG 2.2 AA tags; report-only):"]
for page in pages:
    summary_lines.append(f"{page['page']}: {page['violations']} violation(s)")

summary_lines.append("")
# TODO(#1131): Make the accessibility audit blocking after the baseline violations are fixed.
summary_lines.append("TODO(#1131): Make this check blocking after the baseline is clean.")

summary = "\n".join(summary_lines) + "\n"
(report_dir / "summary.txt").write_text(summary, encoding="utf-8")
(report_dir / "combined.json").write_text(json.dumps({"pages": pages}, indent=2) + "\n", encoding="utf-8")
print(summary, end="")
PY

echo "Accessibility report written to $REPORT_DIR"
