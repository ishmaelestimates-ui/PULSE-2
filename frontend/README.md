# PULSE Frontend

Vue 3 + Vite editorial console for PULSE: media player with waveform
scrubbing, transcript sync, and the accept/reject review workflow.

## Setup

```bash
cd frontend
npm install
npm run dev
```

Runs at `http://localhost:5173`. The dev server proxies `/api` and
`/media` to `http://localhost:8000` (see `vite.config.js`), so make sure
the backend is running there first — see the root `README.md`.

## Build

```bash
npm run build   # outputs to frontend/dist
npm run preview # serve the production build locally
```

In production, serve `dist/` behind the same origin as the API (or update
`vite.config.js`'s proxy target / add a reverse-proxy rule) so relative
`/api` and `/media` calls keep working.

## Structure

```
src/
├── api/client.js              # thin axios wrapper over every backend endpoint
├── router/index.js            # 2 routes: episode list, episode detail
├── views/
│   ├── EpisodeListView.vue    # grid of episodes with derived status pills
│   ├── EpisodeDetailView.vue  # the workstation — owns all data fetching/mutation
│   ├── BrandSettingsView.vue  # colors/font/logo/intro-outro music (single global config)
│   ├── UserManagementView.vue # invite/list/deactivate users, view activity (admin only)
│   └── LoginView.vue          # password login, magic-link request/verify, invite acceptance
├── components/
│   ├── MediaPlayer.vue        # video/audio + waveform scrubber + color-coded markers
│   ├── TranscriptSync.vue     # timestamp-synced transcript, click-to-seek, auto-scroll
│   ├── ReviewPanel.vue        # tabs: Transcript / Strong / Weak / Clips / Summary / Coloring
│   ├── ReviewList.vue         # accept/reject cards, shared by the review tabs
│   ├── ColoringPanel.vue      # LUT selector, AI style-transfer modal, delivery-spec checklist
│   ├── CampaignPanel.vue      # campaign generation, social posts, hooks, schedule, downloads
│   ├── PRPanel.vue            # press kit, journalist leads, embargoes, coverage
│   ├── RedditPanel.vue        # subreddit search/analysis, disclosed post drafting, karma, comments
│   ├── FilmPanel.vue          # acts, trailer cut lists, festival matches, territory, sync licensing
│   ├── DashboardPanel.vue     # progress/health score, risks, finances, timeline
│   ├── FamePanel.vue          # internal engagement score, mentions/sentiment, competitors, footprint
│   ├── UploadDropzone.vue     # drag-and-drop + click-to-browse upload with progress
│   ├── ExportBar.vue          # Resolve CSV export (live) + Premiere/FCP/campaign stubs
│   └── StatusPill.vue         # draft/uploaded/transcribed/analyzed/reviewed badge
└── assets/styles.css          # design tokens (color/type/radius) — see below
```

No central store (Pinia/Vuex) — `EpisodeDetailView.vue` owns the episode's
state via Composition API refs and passes data down / handles events up.
That's enough for a two-route app; introduce Pinia if the view tree grows.

## Design system

Dark "mission control" console. Tokens live in `src/assets/styles.css`:

- **Brand:** `--primary` #6C5CE7 (purple), `--secondary` #00E676 (green)
- **Marker semantics:** `--strong` green, `--weak` red, `--clip` blue,
  `--primary` for opening, `--bookend` (amber) for closing
- **Type:** Space Grotesk (display), Inter (body), IBM Plex Mono
  (timecodes, stats, transcript timestamps)

## Known gaps (by design, not oversight)

- **Export to Premiere (XML) / FCP (FCPXML) / campaign pack** are
  disabled stub buttons. No backend endpoint produces these formats yet —
  the buttons are there so the layout doesn't need rework once they
  exist, but they don't fabricate a fake export.
- **Speaker labels** in the transcript are rendered *if* a segment has a
  `speaker` field, but neither the Gemini nor Whisper transcription path
  in the backend currently performs diarization, so this will typically
  be empty. Wiring is ready for whenever diarization is added.
- **Marker colors on the player differ slightly from the Resolve CSV
  export.** The player distinguishes opening (purple) from closing
  (amber) so an editor can tell them apart at a glance; the backend's CSV
  export uses amber for both. Cosmetic-only — doesn't affect what gets
  exported.
- **"AI style transfer" is not neural style transfer.** Gemini looks at
  a reference image and a frame from your footage and suggests
  conventional grading parameters (brightness/contrast/saturation/
  temperature/tint); FFmpeg applies them. The UI's copy says this
  explicitly rather than implying a black-box pixel transform.
- **The delivery-spec checklist is a rough baseline, not a compliance
  guarantee.** It compares real measured metadata (resolution, frame
  rate, codec, loudness, true peak) against simplified reference targets
  compiled from public platform docs — always confirm against the
  platform's current official delivery specification before shipping.
- **Brand settings are still global, not per-user**, even though an auth
  system now exists (Sprint 8) — `/settings` wasn't retrofitted to scope
  per account. One shared configuration for the whole project.
- **Hype scores and viral predictions are AI estimates, not analytics.**
  Gemini's qualitative read of a clip's hook strength, turned into a
  number and a label — there's no trained predictive model and no real
  engagement data feeding it. The disclaimer is shown inline in the
  Campaign tab, not buried in docs.
- **The release schedule's "best times" are generic industry defaults,**
  not personalized to this show's audience (PULSE has no
  analytics/social integration to draw real data from).
- **The trailer cut list is deterministic, not Gemini-written.** It's
  assembled in Python from the accepted moments/clips with the highest
  confidence scores, packed to fit ~60 seconds.
- **The Reddit panel does not do undisclosed self-promotion.** Every
  post carries a mandatory disclosure note, subreddit recommendations
  come from real Reddit search results (not hallucinated names), and
  comment replies are drafted for you to post yourself — nothing
  auto-posts. See the root README's Sprint 6 section for the full
  reasoning; this was a deliberate deviation from the original spec's
  "frame as discussion, no self-promotion" request.
- **Journalist leads are not AI-generated contacts.** The "Find
  journalist leads" button returns outlet-type/beat suggestions to
  research, never invented names or emails — those you enter yourself
  once verified.
- **Festival deadlines/fees are AI guesses, always shown as unverified
  until you check them yourself.** The Film tab's checkbox to mark a
  match "verified" exists because festival dates move every year and
  Gemini's training data goes stale — the dashboard's upcoming-deadlines
  list flags unverified ones explicitly rather than treating a guess as
  a hard date.
- **The sync-licensing scan is not legal advice.** It's a heuristic
  transcript scan for third-party content mentions worth a human
  reviewing — not exhaustive, not a clearance.
- **The dashboard's health score and progress are deterministic**,
  computed from PULSE's own tracked completion state — not an external
  benchmark. "Team status" is still reported as empty — Sprint 8 added
  user accounts, but the dashboard wasn't wired to show per-user activity
  there yet (see the Users page under Settings for that instead).
- **The Fame Score is not a real-world fame measurement.** It's a
  documented, deterministic formula over PULSE's own tracked data
  (Reddit engagement, coverage count, festival tier, milestones) —
  labeled an "internal engagement index" everywhere it appears, never
  "reach" or "authority" in the real-world sense. The 30/90/365-day
  projection is a naive linear trend line over that index's own history,
  not a forecast about anyone's actual fame.
- **"Media monitoring" is real Reddit search, nothing more.** No
  Twitter/X, news, or general web monitoring is integrated — those need
  manual entry in the Mentions tab. Sentiment analysis on a mention's
  text is genuine Gemini NLP, unlike the score itself.
- **Competitor benchmarking and cultural footprint are fully manual.**
  PULSE doesn't fabricate statistics about named competitors or
  auto-detect memes/citations — both are logs of things you found and
  entered yourself.
- **Magic links and invites are not actually emailed.** No email
  provider is integrated. In development the link is shown directly in
  the Users page and the login screen; elsewhere it's only logged
  server-side.
- **Sprint 1-7 endpoints are not access-controlled.** Logging in gates
  only the new Users/Fame endpoints — everything else in the app remains
  exactly as open as it was before Sprint 8.

## Sprint 9: UI/UX polish — two honest substitutions

- **`engine-roar.mp3` doesn't exist as a shipped file.** There's no
  audio-synthesis tool available to generate a real sound effect, and
  writing arbitrary bytes into a `.mp3` extension would just be a broken
  file. `LoadingScreen.vue` tries `/engine-roar.mp3` first (drop a real
  licensed file into `frontend/public/` to use one), and falls back to a
  short engine-like sweep synthesized client-side via the Web Audio API.
  Browsers also block autoplay-with-sound until a user gesture — that
  failure is silent by design; the visual animation still plays either way.
- **Multi-format upload badges only claim what the backend actually
  supports.** The brief asked for FLV/WMV/OGG/WMA and direct transcript-
  file upload (SRT/VTT/TXT/DOCX/PDF), none of which the media pipeline
  parses — and this sprint is explicitly scoped as "no new features."
  `UploadDropzone.vue` shows those formats as visibly disabled
  ("not yet supported") rather than badging them as if they work, and
  validates the file extension client-side before ever hitting the
  upload endpoint.
- The searchable feature list (`/features`) computes its count live from
  a real per-sprint feature array rather than asserting a fixed "150+"
  — whatever the true count is, is what's displayed.
- "Resume capability" under Persistent Progress is mostly free: nearly
  all state is already persisted to the backend on every action, so
  reloading or returning later already resumes exactly where you left
  off via the episode id in the URL. `useAutoSave.js` adds a debounced
  save + status indicator for the one place with local draft state before
  Sprint 9 (brand settings' color/font form) — it's a UX utility, not a
  new persistence layer.
- Toasts and keyboard shortcuts are wired into the highest-value spots
  (upload/transcribe/analyze/export/campaign/LUT-apply/invite), not
  retrofitted onto every single action across all nine sprints — that
  would be a much larger, lower-value pass.
