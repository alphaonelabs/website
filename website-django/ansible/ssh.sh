#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
INV=inventory.yml
HOST=$(awk '/ansible_host:/ {print $2; exit}' "$INV")
USER=$(awk '/ansible_user:/ {print $2; exit}' "$INV")
PORT=$(awk '/ansible_port:/ {print $2; exit}' "$INV")
PASS=$(awk -F':' '/ansible_password:/ {sub(/^ +/,"",$2); gsub(/"/,"",$2); print $2; exit}' "$INV")
if [ -z "${HOST}" ] || [ -z "${USER}" ] || [ -z "${PASS}" ]; then
  echo "Missing host/user/password from inventory.yml" >&2
  exit 1
fi
if ! command -v sshpass >/dev/null 2>&1; then
  if command -v apt-get >/dev/null 2>&1; then
    sudo apt-get update -y && sudo apt-get install -y sshpass
  else
    echo "Install sshpass manually" >&2; exit 2
  fi
fi
exec sshpass -p "$PASS" ssh -o StrictHostKeyChecking=no -p "${PORT:-22}" "${USER}@${HOST}" "$@"
