# Deploying PULSE to Render (Docker)

## 1. Push to GitHub
Render deploys from a Git repo — push this codebase to GitHub (or GitLab) first.

## 2. Create the PostgreSQL database
In the Render dashboard: **New → PostgreSQL**
- Pick a name, region, and plan.
- Once created, copy the **Internal Database URL** — you'll need it below.
- Render's own Postgres URLs already start with `postgresql://`, which is what this app expects.

## 3. Create the web service
**New → Web Service** → connect your repo.
- **Runtime:** Docker (Render will detect the `Dockerfile` automatically).
- **Build Command:** leave blank — Docker handles the build via the `Dockerfile`.
- **Start Command:** leave blank — the `Dockerfile`'s `CMD` already runs
  `alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port $PORT`.
- Render injects `$PORT` automatically; the Dockerfile is already wired to use it.

Using Docker (not Render's native Python runtime) matters here specifically because
the app shells out to the real `ffmpeg`/`ffprobe` binaries for media processing —
the `Dockerfile` installs those via `apt-get`. Render's native Python buildpack does
not include ffmpeg, so native runtime deployment would fail on any upload/color/
transcription-adjacent endpoint.

## 4. Environment variables
Set these in the Render service's **Environment** tab:

| Variable | Value |
| --- | --- |
| `DATABASE_URL` | The Internal Database URL from step 2 |
| `SECRET_KEY` | A long random string (signs session tokens) |
| `ENVIRONMENT` | `production` |
| `GEMINI_API_KEY` | Your Gemini key |
| `OPENAI_API_KEY` | Only if using `TRANSCRIPTION_PROVIDER=whisper` |
| `POSTIZ_URL`, `POSTIZ_API_KEY` | Only if using Postiz distribution |
| `BOOTSTRAP_ADMIN_EMAIL`, `BOOTSTRAP_ADMIN_PASSWORD` | Sets the first admin login on first boot |
| `MEDIA_STORAGE_PATH` | `/app/media` (matches the Dockerfile) |

See `.env.example` for the complete list with defaults — anything not listed above
can usually be left at its default.

**Persistent media:** Render's filesystem is ephemeral across deploys/restarts.
Add a Render **Disk**, mount it at `/app/media`, so uploaded media survives redeploys.

## 5. Migrations
Nothing to do manually — the container's start command runs `alembic upgrade head`
every time it boots, before starting the server. This is safe to run repeatedly;
Alembic tracks which migrations are already applied.

If you ever need to run a migration manually against the Render database from your
own machine: `DATABASE_URL=<internal-or-external-url> alembic upgrade head`
(use the **External** Database URL if running from outside Render's network).

## 6. Deploy
Click **Create Web Service**. Render builds the Docker image, starts the container,
runs migrations, and boots the app. Watch the deploy logs for the bootstrap-admin
line (it prints a generated password once if `BOOTSTRAP_ADMIN_PASSWORD` wasn't set —
copy it immediately, it's not recoverable after that).
