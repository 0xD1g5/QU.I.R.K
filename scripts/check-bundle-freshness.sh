#!/usr/bin/env bash
# Fail when the committed dashboard bundle (quirk/dashboard/static) does not
# match a fresh build of src/dashboard. The bundle is build output committed
# to git; nothing else detects when source and bundle drift apart, and a stale
# bundle ships old UI against a new API.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${REPO_ROOT}/src/dashboard"

if [ ! -d node_modules ]; then
  npm ci --no-audit --no-fund
fi
npm run build

cd "${REPO_ROOT}"
DRIFT=$(git status --porcelain quirk/dashboard/static)
if [ -n "${DRIFT}" ]; then
  echo ""
  echo "ERROR: committed bundle is stale — rebuilding src/dashboard changed quirk/dashboard/static:"
  echo "${DRIFT}"
  echo ""
  echo "Fix: commit the rebuilt assets (git add quirk/dashboard/static) or revert the src/dashboard change."
  exit 1
fi
echo "Bundle is fresh: quirk/dashboard/static matches a clean build of src/dashboard."
