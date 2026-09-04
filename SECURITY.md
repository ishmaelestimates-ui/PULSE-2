# PULSE Security Notes

This deployment-ready build includes several security hardening changes:

- Private FastAPI routers are protected by a shared authentication dependency at router registration time.
- Admin-only endpoints retain their existing role checks.
- Production startup rejects placeholder/weak `SECRET_KEY`, placeholder database URLs, wildcard CORS, and weak bootstrap passwords.
- CORS is configured from `CORS_ORIGINS`.
- Standard browser security headers are added, including HSTS in production.
- The frontend has a navigation guard that redirects unauthenticated users to login.

## Still required before a high-security public launch

1. Replace the static `/media` mount with authenticated or signed media delivery. The current frontend relies on same-origin media URLs, so this requires a coordinated frontend/API change rather than a one-line setting.
2. Add server-side session revocation/rotation if immediate logout or forced session invalidation is required.
3. Add rate limiting and abuse protection at the reverse proxy/API gateway.
4. Add background workers for long-running FFmpeg jobs rather than keeping HTTP requests open.
5. Add full integration tests against the deployment database and real media-processing binaries.
6. Use a secrets manager or platform secret store; never commit `.env`.
