#!/usr/bin/env bash
set -euo pipefail

: "${DATABASE_URL:?DATABASE_URL is required}"

BACKUP_FILE="${1:-}"
if [[ -z "$BACKUP_FILE" || ! -f "$BACKUP_FILE" ]]; then
  echo "Usage: $0 /path/to/backup.sql" >&2
  exit 2
fi

if ! command -v psql >/dev/null 2>&1; then
  echo "ERROR: psql is not installed or not on PATH." >&2
  exit 1
fi

echo "WARNING: This restores database contents from: $BACKUP_FILE"
echo "WARNING: Existing data may be overwritten."
if [[ "${PULSE_CONFIRM_RESTORE:-}" != "YES" ]]; then
  echo "Set PULSE_CONFIRM_RESTORE=YES to continue."
  exit 3
fi

psql --dbname="$DATABASE_URL" --set ON_ERROR_STOP=1 --file="$BACKUP_FILE"
echo "Database restore completed."
