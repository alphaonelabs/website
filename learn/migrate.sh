#!/bin/bash
set -euo pipefail

if [ "${SKIP_D1_MIGRATIONS:-}" = "1" ] || [ "${SKIP_D1_MIGRATIONS:-}" = "true" ]; then
  echo "Skipping D1 migrations because SKIP_D1_MIGRATIONS is set."
  exit 0
fi

if [ -z "${CLOUDFLARE_API_TOKEN:-}" ]; then
  echo "Skipping D1 migrations because CLOUDFLARE_API_TOKEN is not set."
  echo "Set CLOUDFLARE_API_TOKEN for real deploys, or run migrations explicitly with: npx wrangler d1 migrations apply education_db --remote"
  exit 0
fi

echo "Applying D1 migrations to education_db..."
npx --yes wrangler d1 migrations apply education_db --remote
echo "Done."
