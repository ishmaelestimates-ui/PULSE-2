# Authentication Regression Finding

## Confirmed cause

The backend password-login and session-token path remains functional: the existing auth tests pass, including password verification, JWT validation, bootstrap repair, and malformed-token rejection. The deployment regression is at the frontend/API boundary.

`render.yaml` deploys a Render static frontend, but its build command does not provide `VITE_API_BASE_URL`. The frontend client therefore compiles with its relative `/` fallback and sends `/api/v1/auth/login` to the static frontend host instead of the Render backend. The backend's `CORS_ORIGINS` is dashboard-configured (`sync: false`), so a missing or incomplete production value can also prevent the deployed frontend from calling the API.

The corrective change is limited to deployment configuration and regression coverage. No credentials, password hashing, JWT format, or authentication architecture are changed.

## Discriminating checks

- `PYTHONPATH=. pytest -q` passes the current backend suite.
- A frontend production build without `VITE_API_BASE_URL` contains the relative API fallback; a build with the configured backend URL contains the backend origin.
- Authenticated API and media-upload tests exercise repeated login, token persistence, logout/login, and the protected upload path.

Production still requires `CORS_ORIGINS` to include the actual deployed frontend origin, and the frontend build requires `VITE_API_BASE_URL=https://pulse-2-i2yf.onrender.com`.