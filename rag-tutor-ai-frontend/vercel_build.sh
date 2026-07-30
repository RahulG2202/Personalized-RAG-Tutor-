#!/usr/bin/env bash

# Use this from Vercel Settings > Git > Ignored Build Step:
# bash vercel_build.sh
#
# Vercel semantics for Ignored Build Step:
# exit 0 = skip this deployment
# exit 1 = continue with build/deploy

set -euo pipefail

BRANCH_NAME="${VERCEL_GIT_COMMIT_REF:-}"

if [[ -z "$BRANCH_NAME" ]]; then
  BRANCH_NAME="$(git rev-parse --abbrev-ref HEAD 2>/dev/null || true)"
fi

echo "Vercel branch: ${BRANCH_NAME:-unknown}"

if [[ "$BRANCH_NAME" == "main" ]]; then
  echo "Main branch detected. Continuing Vercel build."
  exit 1
fi

echo "Skipping Vercel build. Only the main branch deploys."
exit 0
