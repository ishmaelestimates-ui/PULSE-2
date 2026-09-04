# PULSE

FastAPI backend + Vue 3 frontend for the PULSE podcast production/
distribution system: media upload, FFmpeg-powered metadata/waveform/
thumbnail extraction, transcription (Gemini or Whisper), Gemini-powered
editorial analysis, a media player with transcript sync and an accept/
reject review console, CSV marker export for DaVinci Resolve, LUT-based
color grading with Gemini-suggested grading parameters, delivery-spec
compliance checking, project brand settings, a Gemini-generated marketing
campaign pack, a PR module (press kit, journalist lead tracking,
embargoes, coverage), Postiz-backed distribution to social platforms and
Reddit, film features (3-act structure, trailer cut lists, festival
matching, territory planning, sync-licensing scan), an executive
dashboard (progress, health score, risks, budget, timeline), an internal
engagement index ("Fame" module) with real Reddit mention search and
sentiment analysis, and invite-only user accounts with role-based access.

This file covers the **backend**. See `frontend/README.md` for the Vue
app.

## Quick start (both halves)

```bash
# backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # fill in DATABASE_URL, GEMINI_API_KEY, SECRET_KEY
alembic upgrade head
uvicorn app.main:app --reload   # http://localhost:8000

# frontend (separate terminal)
cd frontend
npm install
npm run dev              # http://localhost:5173, proxies to :8000
```

## Backend setup

```bash
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env
# then edit .env: set DATABASE_URL, GEMINI_API_KEY, SECRET_KEY
# (and OPENAI_API_KEY if you'll use TRANSCRIPTION_PROVIDER=whisper)
```

### FFmpeg (required for media upload)

The media endpoints shell out to `ffmpeg`/`ffprobe`, so they must be on
`PATH`. The provided Dockerfile installs them automatically; for local
development install them yourself:

```bash
# macOS
brew install ffmpeg
# Debian/Ubuntu
sudo apt-get install ffmpeg
```

If FFmpeg isn't found, upload/transcribe endpoints return a clean 503
rather than crashing.

## Database

Requires PostgreSQL. Create the database, then run migrations:

```bash
alembic upgrade head
```

Migration `0002` adds the `media_files` table and makes
`episodes.transcript` nullable (episodes can now be created "media-first"
— upload audio/video, then transcribe — instead of only "transcript-first").
Migration `0003` adds `episodes.transcript_segments` (timestamped segments,
populated by `/transcribe`), which the frontend needs for transcript sync.

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

| Method | Path                                      | Description                                        |
|--------|-------------------------------------------|-----------------------------------------------------|
| GET    | `/api/v1/episodes`                        | List episodes with a derived status + review counts  |
| POST   | `/api/v1/episodes`                        | Create an episode (transcript optional as of Night 2)|
| GET    | `/api/v1/episodes/{id}`                   | Get an episode + its review statuses                |
| POST   | `/api/v1/episodes/{id}/media`             | Upload audio/video; runs FFmpeg extraction           |
| GET    | `/api/v1/episodes/{id}/media-status`      | Uploaded files, transcription status, duration       |
| POST   | `/api/v1/episodes/{id}/transcribe`        | Transcribe via Gemini or Whisper                     |
| POST   | `/api/v1/episodes/{id}/analyze`           | Run Gemini analysis, generate recommendations        |
| POST   | `/api/v1/episodes/{id}/reviews`           | Accept/reject/update a recommendation                |
| GET    | `/api/v1/episodes/{id}/export/markers`    | CSV export of accepted markers for Resolve            |
| GET    | `/media/uploads/{episode_id}/{filename}`  | Static: original uploaded file                       |
| GET    | `/media/derived/{episode_id}/{filename}`  | Static: extracted audio / thumbnail / grade previews  |
| GET    | `/api/v1/luts`                            | List built-in + uploaded .cube 3D LUTs                |
| POST   | `/api/v1/luts?name=...`                   | Upload a custom .cube LUT                             |
| POST   | `/api/v1/episodes/{id}/apply-lut`         | Apply a LUT via ffmpeg lut3d (preview or full render) |
| POST   | `/api/v1/episodes/{id}/style-transfer`    | Gemini-suggested grading params, applied via ffmpeg   |
| GET    | `/api/v1/episodes/{id}/color-specs`       | Netflix/Amazon/Apple compliance check (real metadata) |
| GET    | `/api/v1/delivery-specs`                  | Static reference delivery specs per platform          |
| GET    | `/api/v1/brand-settings`                  | Get project brand settings                            |
| PUT    | `/api/v1/brand-settings`                  | Update colors/font                                    |
| POST   | `/api/v1/brand-settings/logo`             | Upload logo image                                     |
| POST   | `/api/v1/brand-settings/intro-music`      | Upload intro music                                    |
| POST   | `/api/v1/brand-settings/outro-music`      | Upload outro music                                    |
| POST   | `/api/v1/episodes/{id}/generate-campaign` | Generate/regenerate the full campaign pack             |
| GET    | `/api/v1/episodes/{id}/campaign`          | Fetch the most recently generated campaign pack        |
| GET    | `/api/v1/episodes/{id}/hype-score`        | AI-estimated hype scores (from the stored campaign)    |
| GET    | `/api/v1/episodes/{id}/viral-prediction`  | AI-estimated viral predictions (from the stored campaign) |
| POST   | `/api/v1/episodes/{id}/generate-press-kit`| Generate press release/synopsis/bios/quotes/FAQ        |
| GET    | `/api/v1/episodes/{id}/journalist-matches`| AI-suggested outlet types/beats (not named contacts)   |
| GET/POST | `/api/v1/episodes/{id}/journalist-leads`| Track real contacts you've found yourself              |
| POST   | `/api/v1/episodes/{id}/send-pitches`      | Draft pitch text (does not send email)                 |
| GET/POST | `/api/v1/episodes/{id}/embargoes`       | Embargo tracking                                        |
| GET/POST | `/api/v1/episodes/{id}/coverage`        | Manually-tracked press coverage (no scraping)           |
| GET    | `/api/v1/reddit/subreddits/search`        | Real subreddit search via Reddit's public API           |
| GET    | `/api/v1/reddit/subreddits/analyze/{name}`| Real subscriber/rules/top-posts data                    |
| POST   | `/api/v1/episodes/{id}/reddit/generate`   | Disclosed post titles/body/subreddit suggestions        |
| GET/POST | `/api/v1/episodes/{id}/reddit/posts`    | Reddit post drafts                                       |
| POST   | `/api/v1/episodes/{id}/reddit/schedule`   | Schedule a Reddit post via Postiz                       |
| GET    | `/api/v1/episodes/{id}/reddit/performance`| Upvotes/comments (best-effort via Postiz)                |
| POST   | `/api/v1/reddit/comment/suggest`          | Draft a reply for your own disclosed account             |
| GET/POST | `/api/v1/reddit/karma`                  | Manual karma log                                         |
| GET    | `/api/v1/platforms/integrations`          | Connected Postiz channels                                |
| GET    | `/api/v1/platforms/reddit/status`         | Whether Reddit is connected in Postiz                    |
| POST   | `/api/v1/episodes/{id}/schedule-posts`    | Schedule the campaign pack's social posts via Postiz     |
| GET    | `/api/v1/episodes/{id}/post-status`       | Scheduled-post status/engagement                          |
| GET    | `/api/v1/episodes/{id}/acts`              | Gemini's 3-act structure read, with confidence scores      |
| GET    | `/api/v1/episodes/{id}/trailer-cut-list`  | Deterministic 30/60/90s cut lists                          |
| POST   | `/api/v1/episodes/{id}/export-trailer`    | CSV export of a trailer cut for Resolve                     |
| GET    | `/api/v1/episodes/{id}/festival-matches`  | Festival suggestions — deadlines/fees unverified            |
| PATCH  | `/api/v1/episodes/{id}/festival-matches/{match_id}` | Correct/verify a festival match                  |
| POST   | `/api/v1/episodes/{id}/festival-submission` | Logline/synopsis/director's statement/key-art brief        |
| GET/POST | `/api/v1/episodes/{id}/territory-schedule` | Planning-target release dates (not real deals)          |
| GET    | `/api/v1/episodes/{id}/delivery-specs`    | Alias of `/color-specs` — see note below                    |
| GET    | `/api/v1/episodes/{id}/sync-licensing-report` | Heuristic transcript scan — NOT legal advice            |
| GET    | `/api/v1/episodes/{id}/dashboard`         | Progress, health score, critical path, upcoming deadlines   |
| GET    | `/api/v1/episodes/{id}/risks`             | Legal/Schedule/Financial/Creative risks (rule-based)         |
| GET/POST | `/api/v1/episodes/{id}/finances`        | Budget tracking + reallocation suggestions                  |
| GET/POST | `/api/v1/episodes/{id}/timeline`        | Milestones with overdue highlighting                         |
| POST   | `/api/v1/auth/invites`                    | (admin) Create an invite                                     |
| GET    | `/api/v1/auth/invites`                    | (admin) List invites                                          |
| DELETE | `/api/v1/auth/invites/{id}`               | (admin) Revoke an invite                                       |
| POST   | `/api/v1/auth/accept-invite`              | Create account from an invite token                            |
| POST   | `/api/v1/auth/login`                      | Password login                                                 |
| POST   | `/api/v1/auth/magic-link/request`         | Request a sign-in link (not actually emailed — see below)      |
| POST   | `/api/v1/auth/magic-link/verify`          | Exchange a magic-link token for a session                      |
| GET    | `/api/v1/auth/me`                         | Current user                                                    |
| GET/PATCH | `/api/v1/users`, `/api/v1/users/{id}`  | (admin) List/update users                                       |
| GET    | `/api/v1/users/{id}/activity`             | Activity log (self or admin)                                    |
| GET    | `/api/v1/episodes/{id}/fame/score`        | Internal engagement index (not a real fame measurement)         |
| GET    | `/api/v1/episodes/{id}/fame/history`      | Score history                                                    |
| GET    | `/api/v1/episodes/{id}/fame/projection`   | Naive linear trend extrapolation                                 |
| GET/POST | `/api/v1/episodes/{id}/fame/mentions`  | Real Reddit search + manual mention log                          |
| POST   | `/api/v1/episodes/{id}/fame/mentions/{id}/analyze-sentiment` | Real Gemini sentiment classification         |
| GET/POST | `/api/v1/episodes/{id}/fame/competitors` | User-entered competitor numbers                                |
| GET/POST | `/api/v1/episodes/{id}/fame/cultural-footprint` | Manual log of memes/references/citations                |

### Typical flow (media-first, new in Night 2)

1. `POST /api/v1/episodes` with `{title}` → get back an `id` (no
   transcript needed yet).
2. `POST /api/v1/episodes/{id}/media` (multipart `file=`) → uploads an
   MP4/MOV/AVI/MKV/WebM/MP3/WAV/M4A/FLAC/AAC file. FFmpeg runs
   automatically: probes duration/codec/resolution, extracts a
   standardized mono 16kHz WAV audio track, generates a simplified
   waveform (300-point amplitude array), and — for video — grabs a JPEG
   thumbnail of the first frame. Returns the `MediaFile` record with
   ready-to-use URLs.
3. `GET /api/v1/episodes/{id}/media-status` → check upload + transcription
   status at any point.
4. `POST /api/v1/episodes/{id}/transcribe` → sends the extracted audio to
   the configured provider (`TRANSCRIPTION_PROVIDER=gemini` or `whisper`)
   and stores the resulting transcript on the episode, with segment-level
   timestamps in the response.
5. From here it's the Night 1 flow: `POST .../analyze` →
   `POST .../reviews` → `GET .../export/markers`.

### Typical flow (transcript-first, Night 1, still supported)

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

### Transcription provider notes

- **`gemini`** (default): uploads the extracted audio to the Gemini
  Files API and asks Gemini 1.5 Flash/Pro for a timestamped transcript.
  Uses `GEMINI_API_KEY`.
- **`whisper`**: calls OpenAI's *hosted* Whisper API
  (`client.audio.transcriptions.create`), which returns segment
  timestamps natively. Uses `OPENAI_API_KEY`. Note: this is not the
  `openai-whisper` PyPI package (that's a local model requiring a GPU and
  multi-GB downloads) — the hosted API is a much better fit for a
  stateless backend. `openai-whisper` is left commented out in
  `requirements.txt` if you specifically want fully offline/local
  transcription instead.

### Color grading (Night 4)

Two grading paths, both **real FFmpeg operations**, not stubs:

- **LUT application** (`POST .../apply-lut`): runs ffmpeg's `lut3d`
  filter against a genuine 3D lookup table. Six built-in `.cube` LUTs
  ship under `app/assets/luts/` (Identity, Warm, Cool, Teal & Orange,
  High Contrast B&W, Flat/Log-ish) — see `scripts/generate_luts.py` if
  you want to regenerate or add more (needs `numpy`, dev-only, not a
  runtime dependency). You can also upload your own `.cube` file via
  `POST /api/v1/luts`. By default only a fast single-frame preview is
  generated; pass `render_full: true` to also render the complete graded
  video — that runs **synchronously and can be slow** for long episodes,
  since there's no background job queue yet.
- **"Style transfer"** (`POST .../style-transfer`): **not** literal
  neural style transfer — Gemini's vision model compares a reference
  image against a frame from the episode and returns suggested grading
  parameters (brightness/contrast/saturation/gamma/temperature/tint) as
  structured JSON, which are then applied mechanically via ffmpeg's `eq`
  and `colorbalance` filters. Honest framing: "AI-suggested settings,
  applied by a deterministic filter," not a black-box pixel transform.

**Delivery-spec compliance** (`GET .../color-specs`) compares the
episode's *actually measured* metadata — resolution, frame rate, codec
(via ffprobe), and integrated loudness / true peak (via a real ffmpeg
`loudnorm` analysis pass run at upload time) — against simplified
baseline targets for Netflix, Amazon Prime Video, and Apple TV+/Video
Partner Program. These targets are compiled from each platform's public
delivery guides but are **rough go/no-go checkpoints, not the full
official specification** (which covers IMF packaging, captions,
metadata schemas, and more) — confirm against current partner
documentation before actual delivery.

### Brand settings (Night 4)

Single global settings row — this build now has authenticated application
routes, but brand settings remain intentionally workspace-global rather than
per-user. Keep the singleton until the product introduces workspaces/tenants.

### Storage layout

```
media/
├── uploads/{episode_id}/{uuid}.{ext}        # original upload
├── derived/{episode_id}/{name}_audio.wav    # extracted/normalized audio
│             {name}_thumb.jpg                # video thumbnail
│             lut_{name}_preview.jpg          # color-grade previews
├── luts/{name}.cube                         # user-uploaded LUTs
└── brand/{logo,intro_music,outro_music}.*   # brand settings assets
```

In production, mount `MEDIA_STORAGE_PATH` as a persistent volume (or swap
`media_service.py`'s local-disk calls for S3/GCS) so uploads survive
redeploys.

### Campaign pack (Night 5)

`POST .../generate-campaign` requires at least one **accepted** strong
moment or clip candidate (analyze the episode and accept something in
the Review tab first). One Gemini call produces the text-generation
pieces — social posts for all 6 platforms, 10-15 hooks, a 3-sentence
press blurb, an email newsletter, and markdown show notes — plus two
things that are explicitly **AI estimates, not measurements**:

- **Hype scores (1-100)** and **viral predictions** (platform +
  viral/high/moderate/low) are Gemini's qualitative read of each clip's
  hook strength and shareability. There is no trained model and no real
  engagement data behind them — every API response and the frontend UI
  carry a disclaimer saying so. `GET .../hype-score` and
  `GET .../viral-prediction` just read these back from the last
  generated campaign rather than recomputing (they're produced together
  in the one Gemini call) — regenerate the campaign to refresh them.

Two pieces are **not** from Gemini at all, deliberately:
- The **release schedule** uses generic, commonly-cited "best time to
  post" windows per platform — not derived from this show's actual
  audience, since PULSE has no analytics/social integration.
- The **trailer cut list** is assembled in pure Python: the accepted
  strong moments/clips are greedily packed by confidence score into a
  ~60s budget, then re-sorted chronologically. Deterministic and
  reproducible — regenerating without changing accepted reviews gives
  the same cut list.

Regenerating overwrites the previous campaign pack (one row per episode,
no version history).

### Sprint 6: PR module, Postiz, Reddit distribution

**A deliberate deviation from spec, stated plainly:** the original brief
for the Reddit module asked for posts "framed as discussion, no self-
promotion" and a "Reddit Domination" module. That's a request to help
disguise marketing as organic community discussion — deceptive to the
people reading it, and against what most subreddits' actual rules exist
to prevent. This wasn't built. What exists instead:

- Every generated/saved Reddit post carries a **mandatory
  `disclosure_note`** ("Posted by the show's creator...") — not optional,
  not something the API lets you clear.
- Title/body generation optimizes for genuine curiosity, explicitly
  instructed (in the Gemini prompt itself) to disclose authorship rather
  than pose as a third party.
- Subreddit recommendations come from **real Reddit search results**
  (Gemini suggests topic keywords, the app searches Reddit's actual
  public API for each one), not hallucinated subreddit names — and
  `analyze_subreddit` surfaces each subreddit's real rules so you can
  follow them.
- Comment-reply suggestions are drafted for **you, the disclosed
  creator, to post yourself** — nothing posts to Reddit automatically.

**Journalist matching is also reframed.** Gemini has no real, current
database of journalists, so having it invent names/outlets/emails would
just be fabricating plausible-looking (and possibly wrong, or entirely
fictional) contact information for real people. `GET .../journalist-matches`
returns AI-suggested *outlet types and beats to research* — never named
individuals. `JournalistLead` is a plain CRM record you fill in yourself
once you've found a real contact.

**Postiz integration** is grounded in Postiz's actual public API
(`/public/v1`, `Authorization: {key}` header, `POST /posts` with
`type`/`date`/`posts`/`tags`) — see `app/services/postiz_service.py`'s
docstring for the two things that couldn't be fully verified without a
live instance: the exact per-platform post-settings schema (Reddit's
subreddit/flair fields etc. — Postiz's own creation wizard is the
authoritative source), and whether analytics are exposed identically on
self-hosted instances (degrades to "unknown" rather than failing if not).

**No web scraping is implemented** for the coverage-tracking endpoint —
building a reliable, ToS-compliant scraper per news outlet is its own
substantial project. Coverage is manual entry only.

### Sprint 7: Film features + executive dashboard

**`GET .../delivery-specs` duplicates Night 4's `GET .../color-specs`.**
Sprint 7 asked for a per-episode Netflix/Amazon/Apple compliance
checklist — that endpoint already existed. Rather than duplicate the
compliance logic under a second path, `/delivery-specs` is a thin alias
that calls the same implementation.

**What's deterministic vs. AI vs. AI-but-explicitly-unverified:**

- **Trailer cut selection is deterministic** — ranked by confidence +
  hype score (when a campaign's been generated), packed to fit 30/60/90s.
  Only `scene_type` (Action/Dialogue/Emotional/Climax, used for CSV
  marker coloring) comes from Gemini, and it's labeled as a qualitative
  tone read, not a factual category.
- **Acts** (3-act structure) are Gemini's narrative-arc read, complete
  with its own confidence score — a starting point for an editor, same
  spirit as strong/weak moment detection from Night 1.
- **Festival matches are the one place this sprint leans hardest on a
  disclaimer, deliberately.** Gemini can usually name real, relevant
  festivals correctly, but submission deadlines and entry fees are
  guesses from training data that goes stale every year (these dates
  move annually) and can simply be wrong. Every match starts
  `verified=false`; the fuzzy deadline text is stored as a note, not
  parsed into the real `deadline` date field, specifically so a wrong
  AI guess can't silently masquerade as a hard date somewhere else in
  the app (e.g. the dashboard's upcoming-deadlines list only shows a
  `deadline` if one exists AND flags it "unverified" until you check
  the festival's actual site and confirm it).
- **Territory schedule is a planning tool**, not real distribution deal
  data — PULSE has no distribution-partner integration.
- **Sync-licensing report is explicitly not legal advice.** It's a
  heuristic transcript scan for songs/artists/third-party content
  mentions worth a human (ideally a lawyer) reviewing. It can miss real
  issues and over-flag harmless ones; an empty result is not clearance.
- **Dashboard health score, progress, and risks are 100% deterministic**
  — computed from PULSE's own tracked data (uploads, review decisions,
  generated assets, overdue milestones, budget overruns, unverified
  festival deadlines). No external benchmark, no AI call, except that
  `/risks` triggers one sync-licensing scan for the Legal category
  (`/dashboard` itself doesn't, to keep the main load fast).
- **"Team status" is honestly empty.** PULSE has no multi-user/team
  accounts, so there's no real team data to show — the dashboard says so
  rather than inventing placeholder team members.

### Sprint 8: Fame module + user management

**Fame Score is not a real-world fame measurement.** PULSE has no
social-listening API, no citation database, and no way to verify
anything about the outside world. Rather than have Gemini invent a
precise-looking "reach: 47, authority: 62" style number (which would be
pure fabrication with no basis), the Fame Score is a **deterministic,
fully-inspectable formula** over PULSE's own real tracked data:

```
engagement    = log-scaled(Reddit upvotes+comments, accepted reviews)
reach_proxy   = coverage-item count + submitted/accepted festival matches
authority_proxy = accepted tier-1/tier-2 festivals + completed milestones
momentum      = change vs. the previous snapshot
score         = 0.40·engagement + 0.25·reach_proxy + 0.20·authority_proxy + 0.15·momentum
```

The formula is documented in `fame_service.py`, echoed in every API
response's `note` field, and never described as "fame," "reach," or
"authority" in the real-world sense in the UI — it's labeled an internal
engagement index. The 30/90/365-day "projection" is naive linear
regression over the score's own history — a mechanical trend line, not a
forecast about anyone's actual future fame.

**"Media monitoring" is real Reddit search, not web-wide surveillance.**
`fame/mentions/search-reddit` hits Reddit's actual public search API and
saves genuine results. There's no integration for Twitter/X, news sites,
or anywhere else — those need manual entry. Sentiment analysis on a given
mention's text, by contrast, is genuine Gemini NLP — a legitimate use of
the model, unlike a fabricated fame number.

**Competitor benchmarking and cultural footprint are entirely
user-entered.** PULSE does not generate statistics about named
third-party competitors (that would be fabricating claims about real
entities) or auto-detect memes/citations/references. Both are manual
logs — you tracking things you found yourself.

**User management is a real, from-scratch auth system** (PBKDF2-SHA256
password hashing via stdlib `hashlib`, no extra native dependency; HS256
JWT session tokens via PyJWT), but with two honest limits stated plainly
rather than glossed over:

1. **No email provider is integrated.** Invites and magic links are not
   actually emailed — in `ENVIRONMENT=development` the link is returned
   directly in the API response (and shown in the Users UI) so you can
   test the flow; in any other environment it's only written to the
   server log. Wire in a real provider (SendGrid, SES, Postmark, etc.)
   before relying on this for anyone but yourself.
2. **Application API routers are now authentication-gated.** The current
   build uses a router-level authenticated dependency for the private API
   surface, while admin-only operations keep their existing role checks.
   Fine-grained editor/admin permissions beyond those checks are still a
   future authorization pass.

The first admin account is created automatically on first startup if the
`users` table is empty (see `BOOTSTRAP_ADMIN_EMAIL`/`BOOTSTRAP_ADMIN_PASSWORD`
in `.env.example`) — an invite requires an existing admin, so something
has to seed the first one. If you don't set a password, a random one is
generated and printed to the server log exactly once.

## Tests

```bash
pytest
```


## Security hardening applied

This build makes the application routers authentication-protected at registration time, adds explicit CORS origin configuration, production startup validation for critical secrets, browser security headers, and a frontend route guard.

Set `CORS_ORIGINS` to a comma-separated list of the exact frontend origins, for example `https://studio.example.com`. Do not use `*` in production.

The `/media` static mount remains a same-origin convenience for the current frontend. For public internet deployments containing confidential unreleased media, replace it with authenticated/signed media delivery before treating the system as fully production-secure.
