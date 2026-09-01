<template>
  <div class="feature-view">
    <div class="header">
      <router-link to="/" class="back-link">← Episodes</router-link>
      <h1>What PULSE can do</h1>
      <p class="subtitle">{{ totalCount }} capabilities across {{ categories.length }} areas, built across Sprints 1-9.</p>
    </div>

    <input v-model="query" class="search-input" placeholder="Search features…" autofocus />

    <div v-for="cat in filteredCategories" :key="cat.name" class="category">
      <h3>{{ cat.name }}</h3>
      <div v-for="f in cat.items" :key="f" class="feature-row">{{ f }}</div>
    </div>

    <p v-if="filteredCategories.length === 0" class="no-results">No matching features.</p>
  </div>
</template>

<script setup>
import { computed, ref } from "vue";

const query = ref("");

// A real, sprint-by-sprint accounting of what was actually built —
// not a marketing round number. Kept here as plain data so it's easy to
// keep honest as features change.
const categories = [
  {
    name: "Core editorial (Sprint 1)",
    items: [
      "Gemini-powered transcript analysis (strong moments, weak sections, clip candidates, opening/closing)",
      "Accept/reject review workflow with status tracking",
      "CSV marker export for DaVinci Resolve (timecode + color-coded)",
    ],
  },
  {
    name: "Media & transcription (Sprint 2)",
    items: [
      "Drag-and-drop media upload (MP4/MOV/AVI/MKV/WebM, MP3/WAV/M4A/FLAC/AAC)",
      "FFmpeg metadata probing (duration, codec, resolution, frame rate)",
      "Waveform generation",
      "Video thumbnail extraction",
      "Transcription via Gemini or OpenAI Whisper",
      "Real loudness measurement (integrated LUFS, true peak)",
    ],
  },
  {
    name: "Frontend workstation (Sprint 3)",
    items: [
      "Waveform-based media player with color-coded markers",
      "Transcript sync with playback highlighting and auto-scroll",
      "Click-to-seek from transcript, markers, or review cards",
      "Tabbed review console",
    ],
  },
  {
    name: "Color grading (Sprint 4)",
    items: [
      "Real 3D LUT application via ffmpeg (6 built-in LUTs + custom upload)",
      "Gemini-suggested grading parameters from a reference image",
      "Delivery-spec compliance checks (Netflix/Amazon/Apple, from real measured metadata)",
      "Project brand settings (colors, font, logo, intro/outro music)",
    ],
  },
  {
    name: "Marketing campaign (Sprint 5)",
    items: [
      "Gemini-generated social posts for 6 platforms",
      "10-15 ranked hooks with curiosity-gap scores",
      "Press blurb, email newsletter, show notes",
      "Deterministic 60s trailer cut list",
      "AI-estimated hype scores and viral predictions (clearly labeled as estimates)",
      "Generic release-time scheduling",
      "Download campaign as JSON or Markdown",
    ],
  },
  {
    name: "PR & distribution (Sprint 6)",
    items: [
      "Press kit generation (release, synopsis at 3 lengths, bios, real transcript quotes, FAQ)",
      "Journalist outlet/beat research suggestions (not fabricated contacts)",
      "Pitch drafting + journalist lead tracking, embargoes, coverage log",
      "Postiz integration for multi-platform scheduling",
      "Reddit: real subreddit search/analysis, disclosed post drafting, scheduling, performance, karma log",
    ],
  },
  {
    name: "Film features & dashboard (Sprint 7)",
    items: [
      "3-act structure detection with confidence scores",
      "30/60/90s trailer cut lists with Resolve CSV export",
      "Festival matching (unverified deadlines flagged explicitly)",
      "Festival submission package generator",
      "Territory release planning",
      "Sync-licensing transcript scan (not legal advice)",
      "Executive dashboard: progress, health score, critical path",
      "Rule-based risk detection (Legal/Schedule/Financial/Creative)",
      "Budget tracking with reallocation suggestions",
      "Milestone timeline with overdue highlighting",
    ],
  },
  {
    name: "Fame & user management (Sprint 8)",
    items: [
      "Internal engagement index (deterministic formula, not a real fame measurement)",
      "Naive trend projection over the index's own history",
      "Real Reddit mention search + manual mention log",
      "Gemini sentiment classification on mentions",
      "User-entered competitor benchmarking",
      "Manual cultural-footprint log",
      "Invite-only accounts, admin/editor roles, password + magic-link login",
      "Per-user activity log",
    ],
  },
  {
    name: "Polish (Sprint 9)",
    items: [
      "Branded animated loading screen",
      "Workflow step indicator (Upload → Transcribe → Analyze → Review → Export → Campaign)",
      "Context-aware primary action button",
      "Toast notifications",
      "Card/button micro-interactions",
      "Smart empty states",
      "Keyboard shortcuts (A/R/E, Ctrl+S, Shift+arrows)",
      "This searchable feature list",
      "Auto-save with status indicator on brand settings",
      "Honest format badges on upload (supported vs. not-yet-supported)",
    ],
  },
];

const totalCount = computed(() => categories.reduce((sum, c) => sum + c.items.length, 0));

const filteredCategories = computed(() => {
  const q = query.value.trim().toLowerCase();
  if (!q) return categories;
  return categories
    .map((cat) => ({ ...cat, items: cat.items.filter((i) => i.toLowerCase().includes(q)) }))
    .filter((cat) => cat.items.length > 0);
});
</script>

<style scoped>
.feature-view {
  max-width: 720px;
  width: 100%;
  margin: 0 auto;
  padding: 32px 24px 64px;
}
.header {
  margin-bottom: 20px;
}
.back-link {
  font-size: 12px;
  color: var(--text-faint);
  text-decoration: none;
}
.header h1 {
  font-size: 22px;
  margin: 8px 0 4px;
}
.subtitle {
  font-size: 12.5px;
  color: var(--text-faint);
}

.search-input {
  width: 100%;
  background: var(--surface-inset);
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  color: var(--text);
  padding: 12px 14px;
  font-size: 14px;
  margin-bottom: 24px;
}
.search-input:focus {
  outline: none;
  border-color: var(--primary);
}

.category {
  margin-bottom: 20px;
}
.category h3 {
  font-size: 12px;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  color: var(--primary);
  margin-bottom: 8px;
}
.feature-row {
  font-size: 13px;
  color: var(--text-dim);
  padding: 7px 0;
  border-bottom: 1px solid var(--border);
  line-height: 1.5;
}
.feature-row:last-child {
  border-bottom: none;
}

.no-results {
  text-align: center;
  color: var(--text-faint);
  padding: 40px 0;
}
</style>
