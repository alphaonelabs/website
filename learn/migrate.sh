#!/bin/bash
set -euo pipefail
echo "Applying D1 migrations to education_db..."
npx --yes wrangler d1 migrations apply education_db --remote
echo "Done."