#!/bin/sh
# Commit derived rankings only. The private cache directory is gitignored;
# naming it on git add exits 1 under set -e, so this script never does.
set -eu
git add -- frontend/static/rankings
if git diff --cached --quiet; then
  echo "No ranking changes to publish"
  exit 0
fi
git commit -m "Publish precomputed rankings"
