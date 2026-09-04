#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKUP_DIR="${BACKUP_DIR:-${ROOT_DIR}/backups}"
mkdir -p "$BACKUP_DIR"

: "${DATABASE_URL:?DATABASE_URL is required}"

TIMESTAMP="$(date -u +%Y%m%d_%H%M%S)"
OUTPUT="${BACKUP_DIR}/pulse_db_${TIMESTAMP}.sql"
TMP="${OUTPUT}.tmp"

cleanup() { rm -f "$TMP"; }
trap cleanup EXIT

if ! command -v pg_dump >/dev/null 2>&1; then
  echo "ERROR: pg_dump is not installed or not on PATH." >&2
  exit 1
fi

echo "Creating PostgreSQL backup..."
pg_dump --dbname="$DATABASE_URL" --no-owner --no-acl --format=plain --file="$TMP"

mv "$TMP" "$OUTPUT"
chmod 600 "$OUTPUT"
echo "Backup created: $OUTPUT"
