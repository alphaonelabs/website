#!/bin/bash
set -e
echo "Applying D1 migrations to education_db..."
npx wrangler d1 migrations apply education_db --remote
echo "Done."