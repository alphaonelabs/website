#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "$REPO_ROOT"

usage() {
  cat <<'EOF'
Usage:
  ./scripts/upload-vars.sh [ENV_FILE]
  ./scripts/upload-vars.sh [ENV_FILE] --account-id <CLOUDFLARE_ACCOUNT_ID>
  ./scripts/upload-vars.sh [ENV_FILE] --account-name <CLOUDFLARE_ACCOUNT_NAME>

Examples:
  ./scripts/upload-vars.sh
  ./scripts/upload-vars.sh .env.production --account-id 0123456789abcdef0123456789abcdef
  ./scripts/upload-vars.sh .env.production --account-name "AlphaOneLabs"

Account resolution order:
  1) --account-id / --account-name flags
  2) EXPECTED_CF_ACCOUNT_ID / EXPECTED_CF_ACCOUNT_NAME env vars
  3) CLOUDFLARE_ACCOUNT_ID / CLOUDFLARE_ACCOUNT_NAME in ENV_FILE

Authentication resolution order:
  1) CLOUDFLARE_API_TOKEN env var
  2) CLOUDFLARE_API_TOKEN in ENV_FILE
  3) Wrangler OAuth session (wrangler login)

You can still provide expected account via env vars:
  EXPECTED_CF_ACCOUNT_ID
  EXPECTED_CF_ACCOUNT_NAME
EOF
}

ENV_FILE=".env.production"
EXPECTED_ACCOUNT_ID="${EXPECTED_CF_ACCOUNT_ID:-}"
EXPECTED_ACCOUNT_NAME="${EXPECTED_CF_ACCOUNT_NAME:-}"
AUTH_MODE="oauth"
CF_API_TOKEN="${CLOUDFLARE_API_TOKEN:-}"

if [[ $# -gt 0 && "$1" != --* ]]; then
  ENV_FILE="$1"
  shift
fi

while [[ $# -gt 0 ]]; do
  case "$1" in
    --account-id)
      EXPECTED_ACCOUNT_ID="${2:-}"
      shift 2
      ;;
    --account-name)
      EXPECTED_ACCOUNT_NAME="${2:-}"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Error: unknown argument: $1" >&2
      usage
      exit 1
      ;;
  esac
done

if ! command -v wrangler >/dev/null 2>&1; then
  echo "Error: wrangler is not installed or not in PATH." >&2
  exit 1
fi

if ! command -v python3 >/dev/null 2>&1; then
  echo "Error: python3 is required for JSON parsing in account verification." >&2
  exit 1
fi

if [[ ! -f "$ENV_FILE" ]]; then
  echo "Error: env file not found: $ENV_FILE" >&2
  exit 1
fi

get_optional_var() {
  local key="$1"
  local line
  line="$(grep -E "^${key}=" "$ENV_FILE" | tail -n 1 || true)"
  if [[ -z "$line" ]]; then
    return 1
  fi

  local value="${line#*=}"
  if [[ "$value" == \"*\" ]]; then
    value="${value#\"}"
    value="${value%\"}"
  fi

  printf '%s' "$value"
}

if [[ -z "$EXPECTED_ACCOUNT_ID" ]]; then
  EXPECTED_ACCOUNT_ID="$(get_optional_var "CLOUDFLARE_ACCOUNT_ID" || true)"
fi

if [[ -z "$EXPECTED_ACCOUNT_NAME" ]]; then
  EXPECTED_ACCOUNT_NAME="$(get_optional_var "CLOUDFLARE_ACCOUNT_NAME" || true)"
fi

if [[ -z "$EXPECTED_ACCOUNT_ID" && -z "$EXPECTED_ACCOUNT_NAME" ]]; then
  echo "Error: no expected Cloudflare account found." >&2
  echo "Set one of: --account-id, --account-name, EXPECTED_CF_ACCOUNT_ID, EXPECTED_CF_ACCOUNT_NAME, CLOUDFLARE_ACCOUNT_ID, CLOUDFLARE_ACCOUNT_NAME." >&2
  usage
  exit 1
fi

if [[ -z "$CF_API_TOKEN" ]]; then
  CF_API_TOKEN="$(get_optional_var "CLOUDFLARE_API_TOKEN" || true)"
fi

if [[ -n "$CF_API_TOKEN" ]]; then
  export CLOUDFLARE_API_TOKEN="$CF_API_TOKEN"
  AUTH_MODE="api_token"
  echo "Using Cloudflare API token authentication."
fi

verify_account() {
  local attempt="${1:-0}"
  local whoami_json
  local py_out
  local rc

  set +e
  whoami_json="$(wrangler whoami --json 2>&1)"
  rc=$?
  set -e

  if [[ $rc -ne 0 ]]; then
    echo "Error: failed to run 'wrangler whoami --json'." >&2
    echo "$whoami_json" >&2
    echo "Hint: run 'wrangler login' first." >&2
    exit 1
  fi

  set +e
  py_out="$(WHOAMI_JSON="$whoami_json" EXPECTED_ID="$EXPECTED_ACCOUNT_ID" EXPECTED_NAME="$EXPECTED_ACCOUNT_NAME" python3 - <<'PY'
import json
import os
import sys

raw = os.environ.get("WHOAMI_JSON", "")
exp_id = os.environ.get("EXPECTED_ID", "").strip()
exp_name = os.environ.get("EXPECTED_NAME", "").strip().lower()

try:
    data = json.loads(raw)
except Exception:
    print("PARSE_ERROR")
    sys.exit(2)

if data.get("loggedIn") is False:
  print("NOT_LOGGED_IN")
  print(data.get("email") or "unknown")
  sys.exit(4)

accounts = data.get("accounts") or []
email = data.get("email") or "unknown"

match = None
for account in accounts:
    aid = str(account.get("id", ""))
    aname = str(account.get("name", ""))
    if exp_id and aid == exp_id:
        match = account
        break
    if exp_name and aname.lower() == exp_name:
        match = account
        break

if match is None:
    print("NO_MATCH")
    print(email)
    for account in accounts:
        print(f"{account.get('id', '')}|{account.get('name', '')}")
    sys.exit(3)

print("MATCH")
print(email)
print(f"{match.get('id', '')}|{match.get('name', '')}")
PY
)"
  rc=$?
  set -e

  if [[ $rc -eq 2 || "$py_out" == PARSE_ERROR* ]]; then
    echo "Error: unable to parse Cloudflare account details from wrangler output." >&2
    echo "Raw output:" >&2
    echo "$whoami_json" >&2
    exit 1
  fi

  if [[ $rc -eq 4 || "$py_out" == NOT_LOGGED_IN* ]]; then
    if [[ "$AUTH_MODE" == "api_token" ]]; then
      echo "Error: API token authentication failed (wrangler reports not logged in)." >&2
      echo "Check CLOUDFLARE_API_TOKEN value and required scopes (Workers Scripts:Edit, Account:Read)." >&2
      exit 1
    fi

    if [[ "$attempt" -eq 0 ]]; then
      echo "No active Wrangler login. Running 'wrangler login'..." >&2
      if ! wrangler login; then
        echo "Error: wrangler login failed." >&2
        exit 1
      fi
      verify_account 1
      return
    fi

    echo "Error: Wrangler login still unavailable after re-authentication." >&2
    exit 1
  fi

  if [[ $rc -eq 3 || "$py_out" == NO_MATCH* ]]; then
    if [[ "$AUTH_MODE" == "api_token" ]]; then
      echo "Error: API token authenticated against a different account than expected." >&2
      echo "$py_out" | awk 'NR==2 {print "Authenticated email: " $0}' >&2
      echo "Available accounts from 'wrangler whoami':" >&2
      echo "$py_out" | awk 'NR>2 {split($0,a,"|"); print "  - id=" a[1] ", name=" a[2]}' >&2
      echo "Expected account id: ${EXPECTED_ACCOUNT_ID:-<not set>}" >&2
      echo "Expected account name: ${EXPECTED_ACCOUNT_NAME:-<not set>}" >&2
      exit 1
    fi

    if [[ "$attempt" -eq 0 ]]; then
      echo "Account mismatch detected. Re-authenticating with Cloudflare..." >&2
      echo "$py_out" | awk 'NR==2 {print "Authenticated email: " $0}' >&2
      echo "$py_out" | awk 'NR>2 {split($0,a,"|"); print "  - available id=" a[1] ", name=" a[2]}' >&2
      echo "Expected account id: ${EXPECTED_ACCOUNT_ID:-<not set>}" >&2
      echo "Expected account name: ${EXPECTED_ACCOUNT_NAME:-<not set>}" >&2

      set +e
      wrangler logout >/dev/null 2>&1
      set -e

      echo "Running 'wrangler login'..." >&2
      if ! wrangler login; then
        echo "Error: wrangler login failed." >&2
        exit 1
      fi

      verify_account 1
      return
    fi

    echo "Error: logged-in Cloudflare account still does not match expected account after re-authentication." >&2
    echo "$py_out" | awk 'NR==2 {print "Authenticated email: " $0}' >&2
    echo "Available accounts from 'wrangler whoami':" >&2
    echo "$py_out" | awk 'NR>2 {split($0,a,"|"); print "  - id=" a[1] ", name=" a[2]}' >&2
    echo "Expected account id: ${EXPECTED_ACCOUNT_ID:-<not set>}" >&2
    echo "Expected account name: ${EXPECTED_ACCOUNT_NAME:-<not set>}" >&2
    exit 1
  fi

  echo "$py_out" | awk 'NR==2 {print "Authenticated Cloudflare email: " $0}'
  echo "$py_out" | awk 'NR==3 {split($0,a,"|"); print "Verified account: id=" a[1] ", name=" a[2]}'
}

get_var() {
  local key="$1"
  local line
  line="$(grep -E "^${key}=" "$ENV_FILE" | tail -n 1 || true)"
  if [[ -z "$line" ]]; then
    echo "Error: missing ${key} in ${ENV_FILE}" >&2
    return 1
  fi

  local value="${line#*=}"
  if [[ "$value" == \"*\" ]]; then
    value="${value#\"}"
    value="${value%\"}"
  fi

  printf '%s' "$value"
}

put_secret() {
  local key="$1"
  local value
  local out
  local rc

  value="$(get_var "$key")" || return 1
  if [[ -z "$value" ]]; then
    echo "Error: ${key} is empty in ${ENV_FILE}" >&2
    return 1
  fi

  set +e
  out="$(printf '%s' "$value" | wrangler secret put "$key" 2>&1)"
  rc=$?
  set -e

  if [[ $rc -eq 0 ]]; then
    echo "Uploaded secret: $key"
    return 0
  fi

  echo "$out" >&2
  if echo "$out" | grep -q "Binding name '.*' already in use"; then
    echo "Conflict for ${key}: remove or rename the existing non-secret binding in Cloudflare Worker settings, then rerun." >&2
  else
    echo "Failed to upload secret: ${key}" >&2
  fi
  return 1
}

upload_all_from_env() {
  local line
  local key
  local uploaded=0
  local failed=0

  while IFS= read -r line || [[ -n "$line" ]]; do
    [[ "$line" =~ ^[[:space:]]*$ ]] && continue
    [[ "$line" =~ ^[[:space:]]*# ]] && continue

    line="${line#export }"

    if [[ "$line" =~ ^([A-Za-z_][A-Za-z0-9_]*)= ]]; then
      key="${BASH_REMATCH[1]}"
      if [[ "$key" == "CLOUDFLARE_ACCOUNT_ID" || "$key" == "CLOUDFLARE_ACCOUNT_NAME" || "$key" == "CLOUDFLARE_API_TOKEN" ]]; then
        echo "Skipping metadata key: $key"
        continue
      fi
      if put_secret "$key"; then
        uploaded=$((uploaded + 1))
      else
        failed=$((failed + 1))
      fi
    fi
  done < "$ENV_FILE"

  if [[ "$uploaded" -eq 0 && "$failed" -eq 0 ]]; then
    echo "Error: no valid KEY=VALUE entries found in ${ENV_FILE}" >&2
    exit 1
  fi

  echo "Done. Uploaded ${uploaded} secrets from ${ENV_FILE}; failed: ${failed}."
  if [[ "$failed" -gt 0 ]]; then
    exit 1
  fi
}

verify_account
upload_all_from_env
