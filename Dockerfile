FROM python:3.11-slim

WORKDIR /app

# System deps: gcc/libpq-dev to build psycopg2, ffmpeg for media
# extraction (audio pull, thumbnails, waveform, metadata via ffprobe).
RUN apt-get update \
    && apt-get install -y --no-install-recommends gcc libpq-dev ffmpeg \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Media storage — mount a volume here in production so uploads survive
# container restarts/redeploys.
RUN mkdir -p /app/media/uploads /app/media/derived

# Render (and most PaaS) inject a dynamic $PORT — bind to that, falling
# back to 8000 for local `docker run` where it isn't set. Migrations run
# on every container start; safe to run repeatedly since Alembic tracks
# what's already applied.
EXPOSE 8000
CMD alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}
