#!/usr/bin/env bash
set -euo pipefail

TAG="${1:-}"
if [[ -z "$TAG" ]]; then
  echo "Usage: $0 v1.0.0" >&2
  exit 2
fi

if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  echo "ERROR: Not inside a Git repository." >&2
  exit 1
fi

if ! git rev-parse "$TAG" >/dev/null 2>&1; then
  echo "ERROR: Git ref not found: $TAG" >&2
  exit 5
fi

cat <<MSG
Rollback target verified: $TAG

This script intentionally does NOT force-checkout, reset, or rewrite your
working tree. For a deployed environment, use your Git provider's deploy
history to redeploy this tag/commit, then restore the database separately
if required.
MSG
