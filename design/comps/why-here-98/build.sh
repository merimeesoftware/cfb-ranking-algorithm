#!/usr/bin/env bash
# Rebuild the #98 package: fixtures → HTML states → PNG renders → manifest fragment → checks.
# Needs: python3, node 22, scripts/visual deps (npm ci --prefix scripts/visual), Chrome (CHROME_PATH).
set -euo pipefail
cd "$(dirname "$0")"
python3 data/build_fixtures.py
node render.mjs >/dev/null
node capture.mjs
python3 data/write_fragment.py
node check-comps.mjs --json check-report.json
node test-check-comps.mjs
