# PULSE Safety Scripts

These scripts are intentionally standalone and do not change application runtime behavior.

## Backup

```bash
DATABASE_URL="$DATABASE_URL" ./scripts/backup.sh
```

Creates a timestamped SQL dump under `backups/` (or `$BACKUP_DIR`). The temporary file is removed on failure and completed backups are mode `600`.

## Restore

Restore is deliberately blocked unless explicitly confirmed:

```bash
PULSE_CONFIRM_RESTORE=YES DATABASE_URL="$DATABASE_URL" ./scripts/restore.sh backups/pulse_db_YYYYMMDD_HHMMSS.sql
```

## Tag a release

Run from a clean Git working tree:

```bash
./scripts/tag.sh v1.0.0
```

## Rollback

```bash
./scripts/rollback.sh v1.0.0
```

The rollback helper only verifies the target and prints the safe deployment procedure. It does **not** force-checkout or reset files. This is intentional: a destructive Git reset inside a deployment environment could make recovery harder.

For Render/Git-based deployment, redeploy the selected tag/commit from the deployment provider, then restore the database only if needed.

## Version

```bash
./scripts/version.sh
```
