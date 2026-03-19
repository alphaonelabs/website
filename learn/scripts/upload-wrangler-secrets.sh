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
  local out
  local rc
  value="$(get_var "$key")"
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
    # Ignore blank lines and comment lines.
    [[ "$line" =~ ^[[:space:]]*$ ]] && continue
    [[ "$line" =~ ^[[:space:]]*# ]] && continue

    # Support lines starting with "export KEY=VALUE".
    line="${line#export }"

    if [[ "$line" =~ ^([A-Za-z_][A-Za-z0-9_]*)= ]]; then
      key="${BASH_REMATCH[1]}"
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

upload_all_from_env
