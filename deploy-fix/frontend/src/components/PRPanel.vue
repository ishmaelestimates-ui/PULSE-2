<template>
  <div class="pr-panel">
    <div class="sub-tabs">
      <button v-for="t in subTabs" :key="t" class="sub-tab" :class="{ 'sub-tab--active': subTab === t }" @click="subTab = t">
        {{ t }}
      </button>
    </div>

    <p v-if="error" class="hint hint--error">{{ error }}</p>

    <!-- PRESS KIT -->
    <div v-if="subTab === 'Press kit'" class="pane">
      <div class="header-row">
        <button class="btn btn--primary" :disabled="generatingKit" @click="generateKit">
          {{ generatingKit ? "Generating…" : pressKit ? "Regenerate press kit" : "Generate press kit" }}
        </button>
        <button v-if="pressKit" class="btn-link" @click="printKit">Print / Save as PDF</button>
      </div>

      <div v-if="pressKit" ref="kitContent" class="kit-content">
        <p class="note">{{ pressKit.note }}</p>

        <h4>Press release</h4>
        <p class="body-text">{{ pressKit.press_release }}</p>

        <h4>Synopsis</h4>
        <div class="synopsis-tabs">
          <button v-for="len in ['100', '250', '500']" :key="len" class="platform-tab" :class="{ 'platform-tab--active': synopsisLen === len }" @click="synopsisLen = len">
            {{ len }} words
          </button>
        </div>
        <p class="body-text">{{ pressKit.synopsis[synopsisLen] }}</p>

        <h4>Bios <span class="hint">(drafts — edit before use)</span></h4>
        <div v-for="(bio, i) in pressKit.bios" :key="i" class="bio-card">
          <strong>{{ bio.name }}</strong>
          <p class="body-text">{{ bio.bio }}</p>
        </div>

        <h4>Quotes <span class="hint">(pulled from your own transcript)</span></h4>
        <div v-for="(q, i) in pressKit.quotes" :key="i" class="quote-card">
          <span class="mono quote-time">{{ formatTime(q.timestamp) }}</span>
          <p class="quote-text">"{{ q.text }}"</p>
        </div>

        <h4>FAQ</h4>
        <div v-for="(item, i) in pressKit.faq" :key="i" class="faq-item">
          <p class="faq-q">{{ item.question }}</p>
          <p class="body-text">{{ item.answer }}</p>
        </div>
      </div>
    </div>

    <!-- JOURNALISTS -->
    <div v-else-if="subTab === 'Journalists'" class="pane">
      <button class="btn btn--primary" :disabled="loadingMatches" @click="loadMatches">
        {{ loadingMatches ? "Researching…" : "Find journalist leads" }}
      </button>

      <div v-if="matches.length" class="suggestions">
        <p class="note">{{ matchesNote }}</p>
        <div v-for="(s, i) in matches" :key="i" class="suggestion-card">
          <strong>{{ s.outlet_type }}</strong> — {{ s.beat }}
          <p class="body-text">{{ s.why_relevant }}</p>
          <p class="hint">Search tip: {{ s.search_tip }}</p>
        </div>
      </div>

      <h4 class="leads-header">Tracked leads</h4>
      <p class="hint">Add real contacts you've found yourself — this isn't AI-generated.</p>

      <form class="add-form" @submit.prevent="addLead">
        <input v-model="newLead.name" placeholder="Name" />
        <input v-model="newLead.outlet" placeholder="Outlet" />
        <input v-model="newLead.email" placeholder="Email" />
        <button class="btn btn--ghost" type="submit">+ Add lead</button>
      </form>

      <div v-for="lead in leads" :key="lead.id" class="lead-card">
        <div class="lead-top">
          <strong>{{ lead.name || "(unnamed)" }}</strong>
          <span class="status-badge" :class="`status-badge--${lead.status}`">{{ lead.status }}</span>
        </div>
        <p class="hint">{{ lead.outlet || "—" }} · {{ lead.email || "no email" }}</p>
        <button v-if="lead.status === 'new'" class="btn-link" :disabled="!pressKit" @click="pitchLead(lead.id)">
          {{ pressKit ? "Draft pitch" : "Generate press kit first" }}
        </button>
        <div v-if="lead.pitch_text" class="pitch-text">
          <p class="body-text">{{ lead.pitch_text }}</p>
          <p class="hint">Not sent automatically — copy and send from your own email.</p>
        </div>
      </div>
    </div>

    <!-- EMBARGOES -->
    <div v-else-if="subTab === 'Embargoes'" class="pane">
      <form class="add-form add-form--wrap" @submit.prevent="addEmbargo">
        <input v-model="newEmbargo.embargo_date" type="date" required />
        <input v-model="newEmbargo.follow_up_date" type="date" placeholder="Follow-up" />
        <input v-model="newEmbargo.notes" placeholder="Notes" />
        <button class="btn btn--ghost" type="submit">+ Add embargo</button>
      </form>
      <div v-for="e in embargoes" :key="e.id" class="embargo-row">
        <span class="mono">{{ e.embargo_date }}</span>
        <span class="status-badge" :class="`status-badge--${e.status}`">{{ e.status }}</span>
        <span class="hint">{{ e.notes }}</span>
      </div>
    </div>

    <!-- COVERAGE -->
    <div v-else-if="subTab === 'Coverage'" class="pane">
      <p class="hint">Manual entry only — no automated web scraping.</p>
      <form class="add-form add-form--wrap" @submit.prevent="addCoverageItem">
        <input v-model="newCoverage.outlet_name" placeholder="Outlet" required />
        <input v-model="newCoverage.title" placeholder="Article title" required />
        <input v-model="newCoverage.article_url" placeholder="URL" required />
        <button class="btn btn--ghost" type="submit">+ Add coverage</button>
      </form>
      <div v-for="c in coverage" :key="c.id" class="coverage-row">
        <a :href="c.article_url" target="_blank" rel="noopener" class="coverage-link">{{ c.title }}</a>
        <span class="hint">{{ c.outlet_name }}</span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from "vue";
import api from "../api/client";

const props = defineProps({
  episodeId: { type: Number, required: true },
});

const subTabs = ["Press kit", "Journalists", "Embargoes", "Coverage"];
const subTab = ref("Press kit");
const error = ref("");

const pressKit = ref(null);
const generatingKit = ref(false);
const synopsisLen = ref("250");
const kitContent = ref(null);

const matches = ref([]);
const matchesNote = ref("");
const loadingMatches = ref(false);
const leads = ref([]);
const newLead = reactive({ name: "", outlet: "", email: "" });

const embargoes = ref([]);
const newEmbargo = reactive({ embargo_date: "", follow_up_date: "", notes: "" });

const coverage = ref([]);
const newCoverage = reactive({ outlet_name: "", title: "", article_url: "" });

async function generateKit() {
  generatingKit.value = true;
  error.value = "";
  try {
    pressKit.value = await api.generatePressKit(props.episodeId);
  } catch (err) {
    error.value = err?.response?.data?.detail || "Failed to generate press kit.";
  } finally {
    generatingKit.value = false;
  }
}

function printKit() {
  window.print();
}

async function loadMatches() {
  loadingMatches.value = true;
  error.value = "";
  try {
    const data = await api.getJournalistMatches(props.episodeId);
    matches.value = data.suggestions;
    matchesNote.value = data.note;
  } catch (err) {
    error.value = err?.response?.data?.detail || "Failed to load journalist suggestions.";
  } finally {
    loadingMatches.value = false;
  }
}

async function loadLeads() {
  try {
    leads.value = await api.listJournalistLeads(props.episodeId);
  } catch (err) {
    // non-fatal
  }
}

async function addLead() {
  if (!newLead.name && !newLead.outlet && !newLead.email) return;
  try {
    const lead = await api.createJournalistLead(props.episodeId, { ...newLead });
    leads.value.unshift(lead);
    newLead.name = "";
    newLead.outlet = "";
    newLead.email = "";
  } catch (err) {
    error.value = err?.response?.data?.detail || "Failed to add lead.";
  }
}

async function pitchLead(leadId) {
  try {
    const result = await api.sendPitches(props.episodeId, [leadId]);
    const updated = result.results[0];
    const idx = leads.value.findIndex((l) => l.id === leadId);
    if (idx !== -1) leads.value[idx] = updated;
  } catch (err) {
    error.value = err?.response?.data?.detail || "Failed to draft pitch.";
  }
}

async function loadEmbargoes() {
  try {
    embargoes.value = await api.listEmbargoes(props.episodeId);
  } catch (err) {
    // non-fatal
  }
}

async function addEmbargo() {
  if (!newEmbargo.embargo_date) return;
  try {
    const payload = { ...newEmbargo };
    if (!payload.follow_up_date) delete payload.follow_up_date;
    const e = await api.createEmbargo(props.episodeId, payload);
    embargoes.value.push(e);
    newEmbargo.embargo_date = "";
    newEmbargo.follow_up_date = "";
    newEmbargo.notes = "";
  } catch (err) {
    error.value = err?.response?.data?.detail || "Failed to add embargo.";
  }
}

async function loadCoverage() {
  try {
    coverage.value = await api.listCoverage(props.episodeId);
  } catch (err) {
    // non-fatal
  }
}

async function addCoverageItem() {
  if (!newCoverage.outlet_name || !newCoverage.title || !newCoverage.article_url) return;
  try {
    const c = await api.addCoverage(props.episodeId, { ...newCoverage });
    coverage.value.unshift(c);
    newCoverage.outlet_name = "";
    newCoverage.title = "";
    newCoverage.article_url = "";
  } catch (err) {
    error.value = err?.response?.data?.detail || "Failed to add coverage.";
  }
}

function formatTime(seconds) {
  const total = Math.floor(seconds || 0);
  const m = Math.floor(total / 60);
  const s = total % 60;
  return `${m}:${String(s).padStart(2, "0")}`;
}

onMounted(() => {
  loadLeads();
  loadEmbargoes();
  loadCoverage();
});
</script>

<style scoped>
.pr-panel {
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
  gap: 12px;
}
.header-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.hint {
  font-size: 11.5px;
  color: var(--text-faint);
}
.hint--error {
  color: var(--weak);
}
.note {
  font-size: 11px;
  color: var(--text-faint);
  background: var(--surface-inset);
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  padding: 8px 10px;
}
.kit-content h4 {
  font-size: 12px;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  color: var(--text-faint);
  margin: 14px 0 6px;
}
.body-text {
  font-size: 12.5px;
  color: var(--text-dim);
  line-height: 1.6;
  white-space: pre-wrap;
}
.synopsis-tabs {
  display: flex;
  gap: 4px;
  margin-bottom: 6px;
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
.bio-card, .quote-card, .faq-item {
  background: var(--surface-inset);
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  padding: 10px 12px;
  margin-bottom: 6px;
}
.quote-time {
  font-size: 10px;
  color: var(--text-faint);
}
.quote-text {
  font-style: italic;
  font-size: 12.5px;
  color: var(--text);
  margin-top: 4px;
}
.faq-q {
  font-size: 12.5px;
  font-weight: 600;
  color: var(--text);
}

.leads-header {
  margin-top: 10px;
  font-size: 12px;
  text-transform: uppercase;
  color: var(--text-faint);
}
.add-form {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}
.add-form input {
  flex: 1;
  min-width: 100px;
  background: var(--surface-inset);
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  color: var(--text);
  padding: 7px 9px;
  font-size: 12px;
}
.lead-card, .suggestion-card {
  background: var(--surface-inset);
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  padding: 10px 12px;
  margin-bottom: 6px;
}
.lead-top {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.status-badge {
  font-size: 10px;
  padding: 2px 7px;
  border-radius: 999px;
  border: 1px solid var(--border-bright);
  color: var(--text-faint);
  text-transform: capitalize;
}
.status-badge--pitched, .status-badge--scheduled {
  color: var(--clip);
}
.status-badge--replied, .status-badge--lifted, .status-badge--posted {
  color: var(--secondary);
}
.status-badge--declined, .status-badge--broken {
  color: var(--weak);
}
.pitch-text {
  margin-top: 8px;
  padding-top: 8px;
  border-top: 1px solid var(--border);
}

.embargo-row, .coverage-row {
  display: flex;
  gap: 10px;
  align-items: center;
  padding: 6px 0;
  border-bottom: 1px solid var(--border);
  font-size: 12px;
}
.coverage-link {
  color: var(--primary);
  text-decoration: none;
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
