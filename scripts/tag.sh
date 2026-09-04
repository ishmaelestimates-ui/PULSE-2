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

if [[ -n "$(git status --porcelain)" ]]; then
  echo "ERROR: Working tree is not clean. Commit changes before tagging." >&2
  git status --short
  exit 4
fi

if git rev-parse "$TAG" >/dev/null 2>&1; then
  echo "ERROR: Git ref already exists: $TAG" >&2
  exit 5
fi

git tag -a "$TAG" -m "PULSE STUDIO release $TAG"
echo "Created release tag: $TAG"
