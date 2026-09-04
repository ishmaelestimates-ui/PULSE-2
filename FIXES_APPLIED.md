# PULSE Deployment Hardening Applied

This ZIP is a hardened revision of the supplied `pulse-deploy-ready.zip`.

## Changes in this revision

- Protected the private application API routers with the existing `get_current_user` dependency at router registration time. The auth router remains public for login, invite acceptance, and magic-link flows.
- Added explicit `CORS_ORIGINS` configuration and removed wildcard CORS from the application.
- Added production startup validation for critical configuration: secret key strength, database placeholder detection, wildcard CORS, and bootstrap admin password length.
- Added baseline browser security headers, including HSTS when `ENVIRONMENT=production`.
- Added a Vue router guard so unauthenticated users are sent to the login view before entering the application UI.
- Updated stale authentication/security documentation and added `SECURITY.md`.

## Important remaining work

The current frontend depends on same-origin `/media/...` URLs, so the static media mount was not removed in this compatibility pass. For confidential unreleased media on the public internet, implement authenticated/signed media delivery as a coordinated frontend/API change.

Server-side JWT revocation, rate limiting, background FFmpeg workers, and comprehensive integration tests are also still recommended before a high-security public launch.

## Validation performed

- Python bytecode compilation of backend source: passed.
- Production configuration fail-closed checks: passed.
- AST audit confirms 14 private routers use router-level authentication; auth remains intentionally public.
- Frontend JavaScript syntax checks: passed.

A full live API integration test was not run because the provided execution environment did not have every runtime dependency installed (for example the Gemini package/psycopg2), and no external dependency installation was assumed.

## Reddit Intelligence Upgrade — September 2, 2026

Added a deeper Reddit intelligence layer without turning PULSE into an astroturfing or undisclosed-engagement tool.

- **Community DNA**: live subreddit size/activity, topic overlap, conversation density, promotion-risk signals, rules, and a transparent fit score.
- **Live contribution opportunities**: identifies questions, resource requests, and active discussions where the creator can add real value. It deliberately avoids recommending fake organic posting.
- **Cross-community conversation signal**: observes whether an episode's themes are appearing across multiple Reddit communities.
- **Persistent learning**: stores community snapshots and opportunity observations for later comparison.
- **Reddit UI Intel tab**: scan several communities at once and inspect fit, rules, conversation signals, and live opportunities.
- **New API**: `GET /api/v1/episodes/{id}/reddit/intelligence`, `GET /api/v1/episodes/{id}/reddit/opportunities`, `POST /api/v1/reddit/movement-signal`.
- **Database migration**: `0009_reddit_intelligence.py`.
- **Frontend repair**: fixed the accidental nested `try` in `RedditPanel.vue`.

The intelligence score is an observation/ranking aid, not a prediction of viral success or proof of grassroots support.

## Guardrail Sprint 2 — Isolated Auto-Save & Crash Recovery — September 2, 2026

Added an isolated persistence layer for editor draft snapshots without modifying the existing episode, analysis, campaign, PR, Postiz, Reddit, film, dashboard, fame, or authentication implementations.

### Backend
- Added `app/models/autosave.py` with per-user/per-episode snapshots.
- Added `app/services/autosave_service.py` with latest/history retrieval and a 20-snapshot retention cap.
- Added `app/schemas/autosave.py`.
- Added `app/api/autosave.py` for save/status/history endpoints.
- Added `app/api/recovery.py` for latest-snapshot recovery.
- Added Alembic migration `0010_autosaves.py`.
- Registered the new routers behind the existing authenticated router boundary.

### Frontend
- Added standalone `AutoSaveIndicator.vue`.
- Added standalone `CrashRecovery.vue`.
- Added API client methods for autosave/recovery.

### Verification
- Python compile/AST validation passed.
- Isolated autosave service test passed against SQLite.
- Existing application core modules were not rewritten.
- Frontend components are intentionally standalone; existing editor screens were not modified in this chunk.

## Guardrail Sprint 3 — Isolated Security Audit Logging — September 2, 2026
- Added dedicated `AuditLog` persistence separate from historical user activity entries.
- Added explicit `audit_service.record_event()` with defensive metadata sanitization.
- Sensitive credential/token fields are excluded from audit metadata rather than stored.
- Added admin-only read endpoint: `GET /api/v1/admin/audit` with bounded limit and optional action/user filters.
- Added Alembic migration `0011_audit_logs` with indexes for user, action, and timestamp.
- Registered the new model and router without modifying protected application modules.
- Added focused tests for secret filtering and event persistence.
