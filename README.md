# PULSE Backend

FastAPI backend for the PULSE podcast production/distribution system:
transcript ingestion, Gemini-powered editorial analysis, human review of
recommendations, and CSV marker export for DaVinci Resolve.

## Setup

```bash
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env
# then edit .env: set DATABASE_URL, GEMINI_API_KEY, SECRET_KEY
```

## Database

Requires PostgreSQL. Create the database, then run migrations:

```bash
alembic upgrade head
```

## Run

```bash
uvicorn app.main:app --reload
```

API docs at `http://localhost:8000/docs`.

## Docker

```bash
docker build -t pulse-backend .
docker run --env-file .env -p 8000:8000 pulse-backend
```

## API Overview

| Method | Path                                      | Description                                  |
|--------|-------------------------------------------|-----------------------------------------------|
| POST   | `/api/v1/episodes`                        | Create an episode with a transcript           |
| GET    | `/api/v1/episodes/{id}`                   | Get an episode + its review statuses          |
| POST   | `/api/v1/episodes/{id}/analyze`           | Run Gemini analysis, generate recommendations |
| POST   | `/api/v1/episodes/{id}/reviews`           | Accept/reject/update a recommendation         |
| GET    | `/api/v1/episodes/{id}/export/markers`    | CSV export of accepted markers for Resolve    |

### Typical flow

1. `POST /api/v1/episodes` with `{title, transcript}` → get back an `id`.
2. `POST /api/v1/episodes/{id}/analyze` → Gemini identifies strong
   moments, weak sections, clip candidates, and an opening/closing
   candidate. Each becomes an `EditorialReview` row with
   `status=recommended`.
3. For each review you like, `POST /api/v1/episodes/{id}/reviews` with
   `{review_id, status: "accepted"}` (or `"rejected"`).
4. `GET /api/v1/episodes/{id}/export/markers` → CSV of every accepted
   decision as a Resolve-importable marker (`Start TC,End TC,Name,Note,Color`
   at the configured `RESOLVE_FRAME_RATE`, default 24fps).

## Tests

```bash
pytest
```
