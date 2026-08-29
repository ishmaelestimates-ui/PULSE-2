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

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
