<template>
  <div class="film-panel">
    <div class="sub-tabs">
      <button v-for="t in subTabs" :key="t" class="sub-tab" :class="{ 'sub-tab--active': subTab === t }" @click="subTab = t">
        {{ t }}
      </button>
    </div>

    <p v-if="error" class="hint hint--error">{{ error }}</p>

    <!-- ACTS -->
    <div v-if="subTab === 'Acts'" class="pane">
      <button class="btn btn--primary" :disabled="loadingActs" @click="loadActs">
        {{ loadingActs ? "Analyzing…" : "Detect 3-act structure" }}
      </button>
      <p v-if="actsNote" class="hint">{{ actsNote }}</p>
      <div v-for="act in acts" :key="act.id" class="act-card" @click="emit('seek', act.start_time)">
        <div class="act-top">
          <strong>Act {{ act.act_number }}: {{ act.title }}</strong>
          <span class="mono hint">{{ Math.round(act.confidence * 100) }}% confidence</span>
        </div>
        <p class="hint mono">{{ formatTime(act.start_time) }} – {{ formatTime(act.end_time) }}</p>
        <p class="body-text">{{ act.description }}</p>
      </div>
    </div>

    <!-- TRAILER -->
    <div v-else-if="subTab === 'Trailer'" class="pane">
      <button class="btn btn--primary" :disabled="loadingTrailer" @click="loadTrailer">
        {{ loadingTrailer ? "Building…" : "Generate 30/60/90s cut lists" }}
      </button>
      <p v-if="trailerNote" class="hint">{{ trailerNote }}</p>

      <div v-if="Object.keys(trailerCuts).length" class="version-tabs">
        <button v-for="v in ['30', '60', '90']" :key="v" class="platform-tab" :class="{ 'platform-tab--active': trailerVersion === v }" @click="trailerVersion = v">
          {{ v }}s
        </button>
        <button class="btn-link" @click="doExport">Export CSV for Resolve</button>
      </div>
      <div v-for="cut in trailerCuts[trailerVersion] || []" :key="cut.id" class="cut-row" @click="emit('seek', cut.start_time)">
        <span class="mono cut-time">{{ formatTime(cut.start_time) }}–{{ formatTime(cut.end_time) }}</span>
        <span class="scene-tag" :class="`scene-tag--${cut.scene_type}`">{{ cut.scene_type }}</span>
        <span class="cut-label">{{ cut.description }}</span>
      </div>
    </div>

    <!-- FESTIVALS -->
    <div v-else-if="subTab === 'Festivals'" class="pane">
      <button class="btn btn--primary" :disabled="loadingFestivals" @click="loadFestivals">
        {{ loadingFestivals ? "Researching…" : "Find festival matches" }}
      </button>
      <p v-if="festivalsNote" class="hint">{{ festivalsNote }}</p>

      <div v-for="m in festivalMatches" :key="m.id" class="festival-card">
        <div class="festival-top">
          <strong>{{ m.festival_name }}</strong>
          <span class="tier-badge">Tier {{ m.tier }}</span>
        </div>
        <p class="hint">{{ m.why_relevant }}</p>
        <p v-if="m.notes" class="hint">Deadline guess: {{ m.notes }} <span class="unverified">(unverified)</span></p>
        <p v-if="m.entry_fee" class="hint">Fee guess: {{ m.entry_fee }}</p>
        <label class="verify-row">
          <input type="checkbox" :checked="m.verified" @change="toggleVerified(m)" />
          Verified against the real festival site
        </label>
      </div>

      <button class="btn btn--ghost" :disabled="generatingSubmission" @click="generateSubmission">
        {{ generatingSubmission ? "Writing…" : "Generate submission package" }}
      </button>
      <div v-if="submission" class="submission-card">
        <p class="hint">{{ submission.note }}</p>
        <h4>Logline</h4>
        <p class="body-text">{{ submission.logline }}</p>
        <h4>Synopsis</h4>
        <p class="body-text">{{ submission.synopsis }}</p>
        <h4>Director's statement</h4>
        <p class="body-text">{{ submission.directors_statement }}</p>
        <h4>Key art brief</h4>
        <p class="body-text">{{ submission.key_art_brief }}</p>
      </div>
    </div>

    <!-- TERRITORY -->
    <div v-else-if="subTab === 'Territory'" class="pane">
      <button class="btn btn--ghost" :disabled="loadingTerritory" @click="loadTerritory">
        {{ loadingTerritory ? "Loading…" : "Load territory schedule" }}
      </button>
      <p v-if="territoryNote" class="hint">{{ territoryNote }}</p>
      <div v-for="r in territoryReleases" :key="r.id" class="territory-row">
        <span>{{ r.territory }}</span>
        <span class="mono">{{ r.release_date }}</span>
      </div>
    </div>

    <!-- SYNC -->
    <div v-else-if="subTab === 'Sync licensing'" class="pane">
      <button class="btn btn--primary" :disabled="loadingSync" @click="loadSync">
        {{ loadingSync ? "Scanning…" : "Scan transcript" }}
      </button>
      <p v-if="syncNote" class="hint hint--warn">{{ syncNote }}</p>
      <div v-if="syncFlags.length === 0 && syncChecked" class="hint">No mentions flagged.</div>
      <div v-for="(f, i) in syncFlags" :key="i" class="sync-card">
        <p class="body-text">"{{ f.excerpt }}"</p>
        <p class="hint">{{ f.concern_type }} — {{ f.recommended_action }}</p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from "vue";
import api from "../api/client";

const props = defineProps({
  episodeId: { type: Number, required: true },
});
const emit = defineEmits(["seek"]);

const subTabs = ["Acts", "Trailer", "Festivals", "Territory", "Sync licensing"];
const subTab = ref("Acts");
const error = ref("");

const acts = ref([]);
const actsNote = ref("");
const loadingActs = ref(false);

const trailerCuts = ref({});
const trailerNote = ref("");
const trailerVersion = ref("30");
const loadingTrailer = ref(false);

const festivalMatches = ref([]);
const festivalsNote = ref("");
const loadingFestivals = ref(false);
const submission = ref(null);
const generatingSubmission = ref(false);

const territoryReleases = ref([]);
const territoryNote = ref("");
const loadingTerritory = ref(false);

const syncFlags = ref([]);
const syncNote = ref("");
const syncChecked = ref(false);
const loadingSync = ref(false);

async function loadActs() {
  loadingActs.value = true;
  error.value = "";
  try {
    const data = await api.getActs(props.episodeId);
    acts.value = data.acts;
    actsNote.value = data.note;
  } catch (err) {
    error.value = err?.response?.data?.detail || "Failed to detect acts.";
  } finally {
    loadingActs.value = false;
  }
}

async function loadTrailer() {
  loadingTrailer.value = true;
  error.value = "";
  try {
    const data = await api.getTrailerCutList(props.episodeId);
    trailerCuts.value = data.cuts;
    trailerNote.value = data.note;
  } catch (err) {
    error.value = err?.response?.data?.detail || "Failed to build trailer cut list.";
  } finally {
    loadingTrailer.value = false;
  }
}

async function doExport() {
  try {
    await api.exportTrailer(props.episodeId, Number(trailerVersion.value));
  } catch (err) {
    error.value = "Export failed.";
  }
}

async function loadFestivals() {
  loadingFestivals.value = true;
  error.value = "";
  try {
    const data = await api.getFestivalMatches(props.episodeId);
    festivalMatches.value = data.matches;
    festivalsNote.value = data.note;
  } catch (err) {
    error.value = err?.response?.data?.detail || "Failed to find festival matches.";
  } finally {
    loadingFestivals.value = false;
  }
}

async function toggleVerified(match) {
  try {
    const updated = await api.updateFestivalMatch(props.episodeId, match.id, { verified: !match.verified });
    const idx = festivalMatches.value.findIndex((m) => m.id === match.id);
    if (idx !== -1) festivalMatches.value[idx] = updated;
  } catch (err) {
    error.value = "Failed to update.";
  }
}

async function generateSubmission() {
  generatingSubmission.value = true;
  try {
    submission.value = await api.generateFestivalSubmission(props.episodeId);
  } catch (err) {
    error.value = err?.response?.data?.detail || "Failed to generate submission package.";
  } finally {
    generatingSubmission.value = false;
  }
}

async function loadTerritory() {
  loadingTerritory.value = true;
  error.value = "";
  try {
    const data = await api.getTerritorySchedule(props.episodeId);
    territoryReleases.value = data.releases;
    territoryNote.value = data.note;
  } catch (err) {
    error.value = err?.response?.data?.detail || "Failed to load territory schedule.";
  } finally {
    loadingTerritory.value = false;
  }
}

async function loadSync() {
  loadingSync.value = true;
  error.value = "";
  try {
    const data = await api.getSyncLicensingReport(props.episodeId);
    syncFlags.value = data.flags;
    syncNote.value = data.note;
    syncChecked.value = true;
  } catch (err) {
    error.value = err?.response?.data?.detail || "Failed to scan transcript.";
  } finally {
    loadingSync.value = false;
  }
}

function formatTime(seconds) {
  const total = Math.floor(seconds || 0);
  const m = Math.floor(total / 60);
  const s = total % 60;
  return `${m}:${String(s).padStart(2, "0")}`;
}
</script>

<style scoped>
.film-panel {
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 14px;
}
.sub-tabs {
  display: flex;
  gap: 4px;
  flex-wrap: wrap;
}
.sub-tab {
  background: var(--surface-inset);
  border: 1px solid var(--border);
  color: var(--text-faint);
  font-size: 11.5px;
  padding: 6px 11px;
  border-radius: 999px;
}
.sub-tab--active {
  background: var(--primary-dim);
  border-color: var(--primary);
  color: white;
}
.pane {
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.hint {
  font-size: 11.5px;
  color: var(--text-faint);
}
.hint--error {
  color: var(--weak);
}
.hint--warn {
  color: var(--bookend);
}
.body-text {
  font-size: 12.5px;
  color: var(--text-dim);
  line-height: 1.6;
}

.act-card, .festival-card, .submission-card, .sync-card {
  background: var(--surface-inset);
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  padding: 10px 12px;
  cursor: pointer;
}
.submission-card, .sync-card {
  cursor: default;
}
.act-top, .festival-top {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.submission-card h4 {
  font-size: 11px;
  text-transform: uppercase;
  color: var(--text-faint);
  margin: 10px 0 4px;
}

.version-tabs {
  display: flex;
  gap: 6px;
  align-items: center;
}
.platform-tab {
  background: var(--surface-inset);
  border: 1px solid var(--border);
  color: var(--text-faint);
  font-size: 11px;
  padding: 5px 10px;
  border-radius: 999px;
}
.platform-tab--active {
  background: var(--primary-dim);
  border-color: var(--primary);
  color: white;
}
.cut-row {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 0;
  border-bottom: 1px solid var(--border);
  cursor: pointer;
  font-size: 12px;
}
.cut-time {
  color: var(--text-faint);
  flex-shrink: 0;
}
.scene-tag {
  font-size: 10px;
  padding: 1px 6px;
  border-radius: 999px;
  border: 1px solid var(--border-bright);
  flex-shrink: 0;
}
.scene-tag--Action { color: var(--weak); }
.scene-tag--Dialogue { color: var(--clip); }
.scene-tag--Emotional { color: var(--strong); }
.scene-tag--Climax { color: var(--bookend); }

.tier-badge {
  font-size: 10px;
  padding: 2px 7px;
  border-radius: 999px;
  border: 1px solid var(--border-bright);
  color: var(--text-dim);
}
.unverified {
  color: var(--bookend);
}
.verify-row {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 11px;
  color: var(--text-dim);
  margin-top: 6px;
}

.territory-row {
  display: flex;
  justify-content: space-between;
  padding: 6px 0;
  border-bottom: 1px solid var(--border);
  font-size: 12.5px;
}

.btn {
  font-family: var(--font-body);
  font-weight: 600;
  font-size: 12.5px;
  border-radius: var(--radius-md);
  padding: 8px 14px;
  border: 1px solid var(--border-bright);
  background: var(--surface-raised);
  color: var(--text);
}
.btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
.btn--primary {
  background: var(--primary);
  border-color: var(--primary);
  color: white;
}
.btn-link {
  background: transparent;
  border: none;
  color: var(--primary);
  font-size: 11.5px;
  font-weight: 600;
}
</style>
