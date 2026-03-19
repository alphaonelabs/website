#!/usr/bin/env bash
set -euo pipefail

ENV_FILE="${1:-.env.production}"

if ! command -v wrangler >/dev/null 2>&1; then
  echo "Error: wrangler is not installed or not in PATH." >&2
  exit 1
fi

if [[ ! -f "$ENV_FILE" ]]; then
  echo "Error: env file not found: $ENV_FILE" >&2
  exit 1
fi

get_var() {
  local key="$1"
  local line
  line="$(grep -E "^${key}=" "$ENV_FILE" | tail -n 1 || true)"
  if [[ -z "$line" ]]; then
    echo "Error: missing ${key} in ${ENV_FILE}" >&2
    exit 1
  fi

  local value="${line#*=}"
  # Trim optional surrounding double quotes.
  if [[ "$value" == \"*\" ]]; then
    value="${value#\"}"
    value="${value%\"}"
  fi

  printf '%s' "$value"
}

put_secret() {
  local key="$1"
  local value
  value="$(get_var "$key")"
  if [[ -z "$value" ]]; then
    echo "Error: ${key} is empty in ${ENV_FILE}" >&2
    exit 1
  fi

  printf '%s' "$value" | wrangler secret put "$key"
  echo "Uploaded secret: $key"
}

upload_all_from_env() {
  local line
  local key
  local uploaded=0

  while IFS= read -r line || [[ -n "$line" ]]; do
    # Ignore blank lines and comment lines.
    [[ "$line" =~ ^[[:space:]]*$ ]] && continue
    [[ "$line" =~ ^[[:space:]]*# ]] && continue

    # Support lines starting with "export KEY=VALUE".
    line="${line#export }"

    if [[ "$line" =~ ^([A-Za-z_][A-Za-z0-9_]*)= ]]; then
      key="${BASH_REMATCH[1]}"
      put_secret "$key"
      uploaded=$((uploaded + 1))
    fi
  done < "$ENV_FILE"

  if [[ "$uploaded" -eq 0 ]]; then
    echo "Error: no valid KEY=VALUE entries found in ${ENV_FILE}" >&2
    exit 1
  fi

  echo "Done. Uploaded ${uploaded} secrets from ${ENV_FILE}."
}

upload_all_from_env
