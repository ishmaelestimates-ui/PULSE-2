<template>
  <div class="fame-panel">
    <div class="sub-tabs">
      <button v-for="t in subTabs" :key="t" class="sub-tab" :class="{ 'sub-tab--active': subTab === t }" @click="subTab = t">
        {{ t }}
      </button>
    </div>

    <p v-if="error" class="hint hint--error">{{ error }}</p>

    <!-- SCORE -->
    <div v-if="subTab === 'Score'" class="pane">
      <button class="btn btn--primary" :disabled="loadingScore" @click="loadScore">
        {{ loadingScore ? "Computing…" : "Compute fame score" }}
      </button>

      <div v-if="score" class="score-block">
        <span class="score-value">{{ score.score }}</span>
        <span class="score-label">/ 100</span>
        <p class="hint">{{ score.note }}</p>
        <div class="components">
          <div v-for="(v, k) in score.components" :key="k" class="component-row">
            <span class="component-label">{{ k }}</span>
            <div class="component-track"><div class="component-fill" :style="{ width: v + '%' }"></div></div>
            <span class="mono">{{ v }}</span>
          </div>
        </div>
      </div>

      <div v-if="score" class="projection-row">
        <button v-for="h in [30, 90, 365]" :key="h" class="btn-link" @click="loadProjection(h)">
          Project {{ h }}d
        </button>
      </div>
      <div v-if="projection" class="hint">
        {{ projection.horizon_days }}-day projection: {{ projection.projected_score }}
        ({{ projection.confidence }}) — {{ projection.note }}
      </div>
    </div>

    <!-- MENTIONS -->
    <div v-else-if="subTab === 'Mentions'" class="pane">
      <div class="search-row">
        <input v-model="mentionQuery" placeholder="Search Reddit for mentions…" @keyup.enter="searchReddit" />
        <button class="btn btn--ghost" @click="searchReddit">Search</button>
      </div>
      <p class="hint">Real Reddit search only — other platforms need manual entry below.</p>

      <form class="add-form" @submit.prevent="addManualMention">
        <input v-model="manualMention.platform" placeholder="Platform" required />
        <input v-model="manualMention.excerpt" placeholder="Excerpt / quote" required />
        <button class="btn btn--ghost" type="submit">+ Add manually</button>
      </form>

      <div v-for="m in mentions" :key="m.id" class="mention-card">
        <div class="mention-top">
          <span class="mono hint">{{ m.platform }}</span>
          <span class="sentiment-badge" :class="`sentiment-badge--${m.sentiment}`">{{ m.sentiment }}</span>
        </div>
        <p class="body-text">{{ m.excerpt }}</p>
        <button v-if="m.sentiment === 'unanalyzed'" class="btn-link" @click="analyzeSentiment(m.id)">
          Analyze sentiment
        </button>
      </div>
    </div>

    <!-- COMPETITORS -->
    <div v-else-if="subTab === 'Competitors'" class="pane">
      <p class="hint">Enter real numbers you've looked up yourself — nothing here is AI-generated.</p>
      <form class="add-form add-form--wrap" @submit.prevent="addCompetitorRow">
        <input v-model="competitorForm.competitor_name" placeholder="Competitor" required />
        <input v-model="competitorForm.metric_name" placeholder="Metric (e.g. Subscribers)" required />
        <input v-model.number="competitorForm.competitor_value" type="number" placeholder="Their value" required />
        <input v-model.number="competitorForm.our_value" type="number" placeholder="Our value" />
        <button class="btn btn--ghost" type="submit">+ Add</button>
      </form>
      <div v-for="c in competitors" :key="c.id" class="competitor-row">
        <span>{{ c.competitor_name }}</span>
        <span class="hint">{{ c.metric_name }}</span>
        <span class="mono">{{ c.competitor_value }}</span>
        <span v-if="c.our_value != null" class="mono">us: {{ c.our_value }}</span>
      </div>
    </div>

    <!-- CULTURAL FOOTPRINT -->
    <div v-else-if="subTab === 'Cultural footprint'" class="pane">
      <p class="hint">A manual log of memes/references/citations you've found — not auto-detected.</p>
      <form class="add-form add-form--wrap" @submit.prevent="addFootprintItem">
        <select v-model="footprintForm.item_type">
          <option value="meme">Meme</option>
          <option value="reference">Reference</option>
          <option value="citation">Citation</option>
          <option value="other">Other</option>
        </select>
        <input v-model="footprintForm.description" placeholder="Description" required />
        <input v-model="footprintForm.url" placeholder="URL (optional)" />
        <button class="btn btn--ghost" type="submit">+ Add</button>
      </form>
      <div v-for="item in footprint" :key="item.id" class="footprint-row">
        <span class="type-badge">{{ item.item_type }}</span>
        <span>{{ item.description }}</span>
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

const subTabs = ["Score", "Mentions", "Competitors", "Cultural footprint"];
const subTab = ref("Score");
const error = ref("");

const score = ref(null);
const loadingScore = ref(false);
const projection = ref(null);

const mentions = ref([]);
const mentionQuery = ref("");
const manualMention = reactive({ platform: "", excerpt: "" });

const competitors = ref([]);
const competitorForm = reactive({ competitor_name: "", metric_name: "", competitor_value: null, our_value: null });

const footprint = ref([]);
const footprintForm = reactive({ item_type: "meme", description: "", url: "" });

async function loadScore() {
  loadingScore.value = true;
  error.value = "";
  try {
    score.value = await api.getFameScore(props.episodeId);
  } catch (err) {
    error.value = err?.response?.data?.detail || "Failed to compute fame score.";
  } finally {
    loadingScore.value = false;
  }
}

async function loadProjection(horizon) {
  try {
    projection.value = await api.getFameProjection(props.episodeId, horizon);
  } catch (err) {
    error.value = err?.response?.data?.detail || "Failed to project score.";
  }
}

async function loadMentions() {
  try {
    mentions.value = await api.listMentions(props.episodeId);
  } catch (err) {
    // non-fatal
  }
}

async function searchReddit() {
  if (!mentionQuery.value.trim()) return;
  try {
    await api.searchRedditMentions(props.episodeId, mentionQuery.value.trim());
    await loadMentions();
  } catch (err) {
    error.value = err?.response?.data?.detail || "Reddit search failed.";
  }
}

async function addManualMention() {
  try {
    await api.addMention(props.episodeId, { ...manualMention });
    manualMention.platform = "";
    manualMention.excerpt = "";
    await loadMentions();
  } catch (err) {
    error.value = err?.response?.data?.detail || "Failed to add mention.";
  }
}

async function analyzeSentiment(mentionId) {
  try {
    const updated = await api.analyzeMentionSentiment(props.episodeId, mentionId);
    const idx = mentions.value.findIndex((m) => m.id === mentionId);
    if (idx !== -1) mentions.value[idx] = updated;
  } catch (err) {
    error.value = err?.response?.data?.detail || "Sentiment analysis failed.";
  }
}

async function loadCompetitors() {
  try {
    competitors.value = await api.listCompetitors(props.episodeId);
  } catch (err) {
    // non-fatal
  }
}

async function addCompetitorRow() {
  try {
    await api.addCompetitor(props.episodeId, { ...competitorForm });
    competitorForm.competitor_name = "";
    competitorForm.metric_name = "";
    competitorForm.competitor_value = null;
    competitorForm.our_value = null;
    await loadCompetitors();
  } catch (err) {
    error.value = err?.response?.data?.detail || "Failed to add competitor.";
  }
}

async function loadFootprint() {
  try {
    footprint.value = await api.listCulturalFootprint(props.episodeId);
  } catch (err) {
    // non-fatal
  }
}

async function addFootprintItem() {
  try {
    await api.addCulturalFootprintItem(props.episodeId, { ...footprintForm });
    footprintForm.description = "";
    footprintForm.url = "";
    await loadFootprint();
  } catch (err) {
    error.value = err?.response?.data?.detail || "Failed to add item.";
  }
}

onMounted(() => {
  loadMentions();
  loadCompetitors();
  loadFootprint();
});
</script>

<style scoped>
.fame-panel {
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
.body-text {
  font-size: 12.5px;
  color: var(--text-dim);
  line-height: 1.5;
}

.score-block {
  background: var(--surface-inset);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  padding: 20px;
  text-align: center;
}
.score-value {
  font-family: var(--font-display);
  font-size: 40px;
  font-weight: 700;
  color: var(--primary);
}
.score-label {
  font-size: 14px;
  color: var(--text-faint);
}
.components {
  margin-top: 14px;
  text-align: left;
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.component-row {
  display: grid;
  grid-template-columns: 90px 1fr 34px;
  align-items: center;
  gap: 8px;
}
.component-label {
  font-size: 11px;
  text-transform: capitalize;
  color: var(--text-dim);
}
.component-track {
  height: 6px;
  border-radius: 999px;
  background: var(--surface);
  overflow: hidden;
}
.component-fill {
  height: 100%;
  background: var(--primary);
}
.projection-row {
  display: flex;
  gap: 12px;
}

.search-row, .add-form {
  display: flex;
  gap: 6px;
}
.search-row input, .add-form input, .add-form select {
  flex: 1;
  background: var(--surface-inset);
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  color: var(--text);
  padding: 8px 10px;
  font-size: 12.5px;
}

.mention-card {
  background: var(--surface-inset);
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  padding: 10px 12px;
}
.mention-top {
  display: flex;
  justify-content: space-between;
}
.sentiment-badge {
  font-size: 10px;
  padding: 2px 7px;
  border-radius: 999px;
  border: 1px solid var(--border-bright);
  color: var(--text-faint);
  text-transform: capitalize;
}
.sentiment-badge--positive { color: var(--secondary); }
.sentiment-badge--negative { color: var(--weak); }
.sentiment-badge--neutral { color: var(--clip); }

.competitor-row, .footprint-row {
  display: flex;
  gap: 10px;
  align-items: center;
  padding: 6px 0;
  border-bottom: 1px solid var(--border);
  font-size: 12.5px;
  color: var(--text-dim);
}
.type-badge {
  font-size: 10px;
  padding: 2px 7px;
  border-radius: 999px;
  border: 1px solid var(--border-bright);
  text-transform: capitalize;
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
