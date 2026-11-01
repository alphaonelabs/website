#!/usr/bin/env bash
set -euo pipefail

# Local Cloudflare Worker development entrypoint.
# Loads .env.production when present so the old-server env is preserved locally.
if [ -f .env.production ]; then
  set -a
  . ./.env.production
  set +a
fi

exec npx wrangler dev --local
