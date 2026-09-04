<template>
  <div class="reddit-panel">
    <div class="sub-tabs">
      <button v-for="t in subTabs" :key="t" class="sub-tab" :class="{ 'sub-tab--active': subTab === t }" @click="subTab = t">
        {{ t }}
      </button>
    </div>

    <p v-if="error" class="hint hint--error">{{ error }}</p>

    <!-- GENERATE -->
    <div v-if="subTab === 'Generate'" class="pane">
      <button class="btn btn--primary" :disabled="generating" @click="generate">
        {{ generating ? "Generating…" : "Generate Reddit post" }}
      </button>
      <p class="hint">{{ genNote }}</p>

      <div v-if="generated">
        <p class="disclosure">Disclosure (always included): "{{ generated.disclosure_note }}"</p>

        <h4>Title options</h4>
        <label v-for="(t, i) in generated.title_options" :key="i" class="radio-row">
          <input type="radio" :value="t" v-model="draft.title" />
          {{ t }}
        </label>

        <h4>Body</h4>
        <textarea v-model="draft.body" rows="5" class="body-input"></textarea>

        <h4>Flair</h4>
        <select v-model="draft.flair">
          <option value="">(none)</option>
          <option v-for="f in generated.flair_suggestions" :key="f" :value="f">{{ f }}</option>
        </select>

        <h4>Recommended subreddits <span class="hint">(real, verified via Reddit search)</span></h4>
        <div v-for="s in generated.recommended_subreddits" :key="s.name" class="sub-row" @click="draft.subreddit = s.name.replace(/^r\//, '')">
          <span :class="{ 'sub-row--selected': draft.subreddit === s.name.replace(/^r\//, '') }">{{ s.name }}</span>
          <span class="hint">{{ s.subscribers?.toLocaleString() || "?" }} members</span>
        </div>

        <label class="field">
          <span>Subreddit to post to</span>
          <input v-model="draft.subreddit" placeholder="e.g. podcasts" />
        </label>

        <button class="btn btn--primary" :disabled="!draft.title || !draft.subreddit" @click="saveDraft">
          Save as draft
        </button>
      </div>
    </div>

    <!-- INTELLIGENCE -->
    <div v-else-if="subTab === 'Intel'" class="pane">
      <div class="intel-head">
        <div>
          <h4>Community Intelligence</h4>
          <p class="hint">Map where the conversation already exists. PULSE observes public Reddit activity; it does not manufacture grassroots support.</p>
        </div>
        <button class="btn btn--primary" :disabled="loadingIntel || !intelSubreddits.trim()" @click="loadIntelligence">
          {{ loadingIntel ? "Scanning…" : "Scan communities" }}
        </button>
      </div>
      <label class="field">
        <span>Communities to scan</span>
        <input v-model="intelSubreddits" placeholder="podcasts, documentary, filmmaking" />
      </label>

      <div v-if="intel" class="intel-grid">
        <div class="analysis-card">
          <h4>Conversation signal</h4>
          <div class="intel-score">{{ intel.movement_signal?.signal_score ?? 0 }}</div>
          <p class="hint">{{ intel.movement_signal?.communities_detected ?? 0 }} communities · {{ intel.movement_signal?.total_mentions ?? 0 }} observed mentions</p>
          <p class="body-text">{{ intel.movement_signal?.interpretation }}</p>
        </div>

        <div v-for="c in intel.communities" :key="c.subreddit" class="analysis-card">
          <div class="post-top">
            <h4>{{ c.subreddit }}</h4>
            <strong>{{ c.fit_score }}/100 fit</strong>
          </div>
          <p class="hint">{{ c.subscribers?.toLocaleString() || "?" }} members · {{ c.active_users?.toLocaleString() || "?" }} active</p>
          <p v-if="c.topic_overlap?.length" class="hint">Topic overlap: {{ c.topic_overlap.join(", ") }}</p>
          <p class="hint">Promotion risk: {{ c.promotion_risk }}</p>
          <p v-if="c.rules?.length" class="rules"><strong>Rules:</strong> {{ c.rules.join(" · ") }}</p>
        </div>

        <div v-if="intel.opportunities?.length" class="analysis-card intel-opportunities">
          <h4>Live contribution opportunities</h4>
          <div v-for="o in intel.opportunities.slice(0, 8)" :key="`${o.subreddit}-${o.source_url}`" class="opportunity">
            <div class="post-top"><strong>{{ o.subreddit }}</strong><span>{{ o.score }}/100</span></div>
            <p class="body-text">{{ o.title }}</p>
            <p class="hint">{{ o.rationale }}</p>
            <p class="body-text"><strong>Contribution:</strong> {{ o.suggested_contribution }}</p>
            <a v-if="o.source_url" :href="o.source_url" target="_blank" rel="noopener noreferrer">Open discussion ↗</a>
          </div>
        </div>
      </div>
    </div>

    <!-- SUBREDDITS -->
    <div v-else-if="subTab === 'Subreddits'" class="pane">
      <div class="search-row">
        <input v-model="searchQuery" placeholder="Search subreddits…" @keyup.enter="doSearch" />
        <button class="btn btn--ghost" @click="doSearch">Search</button>
      </div>
      <div v-for="s in searchResults" :key="s.name" class="sub-row" @click="analyze(s.name)">
        <strong>{{ s.name }}</strong>
        <span class="hint">{{ s.subscribers?.toLocaleString() || "?" }} members</span>
      </div>

      <div v-if="analysis" class="analysis-card">
        <h4>{{ analysis.name }}</h4>
        <p class="hint">{{ analysis.subscribers?.toLocaleString() }} members · {{ analysis.active_users || "?" }} active</p>
        <p class="body-text">{{ analysis.description }}</p>
        <p v-if="analysis.rules_summary?.length" class="rules"><strong>Rules:</strong> {{ analysis.rules_summary.join(" · ") }}</p>
        <p class="hint">{{ analysis.note }}</p>
      </div>
    </div>

    <!-- POSTS / PERFORMANCE -->
    <div v-else-if="subTab === 'Posts'" class="pane">
      <button class="btn-link" @click="refreshPerformance">Refresh performance</button>
      <div v-for="post in posts" :key="post.id" class="post-card">
        <div class="post-top">
          <strong>r/{{ post.subreddit }}</strong>
          <span class="status-badge" :class="`status-badge--${post.status}`">{{ post.status }}</span>
        </div>
        <p class="body-text">{{ post.title }}</p>
        <p class="hint">▲ {{ post.upvotes }} · 💬 {{ post.comment_count }}</p>
        <div v-if="post.status === 'draft'" class="schedule-row">
          <select v-model="scheduleSelections[post.id]">
            <option value="" disabled>Choose channel…</option>
            <option v-for="i in integrations" :key="i.id" :value="i.id">{{ i.name }}</option>
          </select>
          <button class="btn-link" :disabled="!scheduleSelections[post.id]" @click="schedule(post.id)">Schedule</button>
        </div>
      </div>
    </div>

    <!-- KARMA -->
    <div v-else-if="subTab === 'Karma'" class="pane">
      <form class="add-form" @submit.prevent="submitKarma">
        <input v-model.number="karmaForm.total_karma" type="number" placeholder="Total" required />
        <input v-model.number="karmaForm.post_karma" type="number" placeholder="Post" required />
        <input v-model.number="karmaForm.comment_karma" type="number" placeholder="Comment" required />
        <button class="btn btn--ghost" type="submit">Log</button>
      </form>
      <p class="hint">Manual entry — no live Reddit account polling wired up yet.</p>
      <div v-for="k in karmaHistory" :key="k.id" class="karma-row">
        <span class="mono">{{ new Date(k.recorded_at).toLocaleDateString() }}</span>
        <span>{{ k.total_karma }} total</span>
      </div>
    </div>

    <!-- COMMENTS -->
    <div v-else-if="subTab === 'Comments'" class="pane">
      <p class="hint">Draft a reply for your own disclosed account — nothing is posted automatically.</p>
      <textarea v-model="commentInput" rows="3" placeholder="Paste the comment you're replying to…" class="body-input"></textarea>
      <button class="btn btn--primary" :disabled="!commentInput || suggestingReply" @click="suggestReply">
        {{ suggestingReply ? "Drafting…" : "Suggest reply" }}
      </button>
      <div v-if="suggestedReply" class="reply-card">
        <p class="body-text">{{ suggestedReply }}</p>
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

const subTabs = ["Generate", "Intel", "Subreddits", "Posts", "Karma", "Comments"];
const subTab = ref("Generate");
const error = ref("");

const generating = ref(false);
const generated = ref(null);
const genNote = ref("");
const draft = reactive({ title: "", body: "", flair: "", subreddit: "" });

const searchQuery = ref("");
const searchResults = ref([]);
const analysis = ref(null);
const intelSubreddits = ref("");
const intel = ref(null);
const loadingIntel = ref(false);

const posts = ref([]);
const integrations = ref([]);
const scheduleSelections = reactive({});

const karmaHistory = ref([]);
const karmaForm = reactive({ total_karma: null, post_karma: null, comment_karma: null });

const commentInput = ref("");
const suggestingReply = ref(false);
const suggestedReply = ref("");

async function generate() {
  generating.value = true;
  error.value = "";
  try {
    generated.value = await api.generateRedditContent(props.episodeId);
    genNote.value = generated.value.note;
    draft.body = generated.value.body;
    draft.title = generated.value.title_options[0] || "";
  } catch (err) {
    error.value = err?.response?.data?.detail || "Failed to generate Reddit post.";
  } finally {
    generating.value = false;
  }
}

async function saveDraft() {
  try {
    const post = await api.createRedditPost(props.episodeId, {
      subreddit: draft.subreddit.replace(/^r\//, ""),
      title: draft.title,
      body: draft.body,
      flair: draft.flair || null,
    });
    posts.value.unshift(post);
    subTab.value = "Posts";
  } catch (err) {
    error.value = err?.response?.data?.detail || "Failed to save draft.";
  }
}

async function loadIntelligence() {
  loadingIntel.value = true;
  error.value = "";
  try {
    intel.value = await api.getRedditIntelligence(props.episodeId, intelSubreddits.value.trim());
  } catch (err) {
    error.value = err?.response?.data?.detail || "Community intelligence scan failed.";
  } finally {
    loadingIntel.value = false;
  }
}

async function doSearch() {
  if (!searchQuery.value.trim()) return;
  try {
    const data = await api.searchSubreddits(searchQuery.value.trim());
    searchResults.value = data.results;
  } catch (err) {
    error.value = err?.response?.data?.detail || "Search failed.";
  }
}

async function analyze(name) {
  try {
    analysis.value = await api.analyzeSubreddit(name);
  } catch (err) {
    error.value = err?.response?.data?.detail || "Analysis failed.";
  }
}

async function loadPosts() {
  try {
    posts.value = await api.listRedditPosts(props.episodeId);
  } catch (err) {
    // non-fatal
  }
}

async function loadIntegrations() {
  try {
    integrations.value = await api.listPlatformIntegrations();
  } catch (err) {
    // Postiz likely not configured — scheduling just won't be available.
  }
}

async function schedule(postId) {
  try {
    const updated = await api.scheduleRedditPost(props.episodeId, {
      reddit_post_id: postId,
      postiz_integration_id: scheduleSelections[postId],
    });
    const idx = posts.value.findIndex((p) => p.id === postId);
    if (idx !== -1) posts.value[idx] = updated;
  } catch (err) {
    error.value = err?.response?.data?.detail || "Failed to schedule.";
  }
}

async function refreshPerformance() {
  try {
    posts.value = await api.getRedditPerformance(props.episodeId);
  } catch (err) {
    error.value = err?.response?.data?.detail || "Failed to refresh performance.";
  }
}

async function loadKarma() {
  try {
    karmaHistory.value = await api.getKarmaHistory();
  } catch (err) {
    // non-fatal
  }
}

async function submitKarma() {
  try {
    const entry = await api.logKarma({ ...karmaForm });
    karmaHistory.value.push(entry);
    karmaForm.total_karma = null;
    karmaForm.post_karma = null;
    karmaForm.comment_karma = null;
  } catch (err) {
    error.value = err?.response?.data?.detail || "Failed to log karma.";
  }
}

async function suggestReply() {
  suggestingReply.value = true;
  try {
    const result = await api.suggestCommentReply(commentInput.value);
    suggestedReply.value = result.suggested_reply;
  } catch (err) {
    error.value = err?.response?.data?.detail || "Failed to draft reply.";
  } finally {
    suggestingReply.value = false;
  }
}

onMounted(() => {
  loadPosts();
  loadIntegrations();
  loadKarma();
});
</script>

<style scoped>
.reddit-panel {
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
.disclosure {
  font-size: 11.5px;
  color: var(--secondary);
  background: var(--surface-inset);
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  padding: 8px 10px;
}
.pane h4 {
  font-size: 12px;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  color: var(--text-faint);
  margin-top: 8px;
}
.radio-row {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12.5px;
  color: var(--text-dim);
  padding: 4px 0;
}
.body-input {
  width: 100%;
  background: var(--surface-inset);
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  color: var(--text);
  padding: 8px 10px;
  font-size: 12.5px;
  font-family: inherit;
  resize: vertical;
}
select, .field input {
  background: var(--surface-inset);
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  color: var(--text);
  padding: 7px 9px;
  font-size: 12.5px;
}
.field {
  display: flex;
  flex-direction: column;
  gap: 4px;
  font-size: 11.5px;
  color: var(--text-dim);
  margin: 8px 0;
}
.sub-row {
  display: flex;
  justify-content: space-between;
  padding: 6px 8px;
  border-radius: var(--radius-sm);
  cursor: pointer;
  font-size: 12.5px;
  color: var(--text-dim);
}
.sub-row:hover {
  background: var(--surface-inset);
}
.sub-row--selected {
  color: var(--primary);
  font-weight: 600;
}
.search-row {
  display: flex;
  gap: 6px;
}
.search-row input {
  flex: 1;
  background: var(--surface-inset);
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  color: var(--text);
  padding: 8px 10px;
  font-size: 12.5px;
}
.intel-head {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  align-items: flex-start;
}
.intel-grid {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.intel-score {
  font-size: 30px;
  font-weight: 800;
  line-height: 1;
  margin: 8px 0;
}
.intel-opportunities {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.opportunity {
  padding: 10px 0;
  border-top: 1px solid var(--border);
}
.opportunity a {
  color: var(--primary);
  font-size: 11.5px;
}
.analysis-card {
  background: var(--surface-inset);
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  padding: 12px;
  margin-top: 8px;
}
.rules {
  font-size: 11.5px;
  color: var(--text-dim);
  margin-top: 6px;
}
.body-text {
  font-size: 12.5px;
  color: var(--text-dim);
  line-height: 1.6;
  white-space: pre-wrap;
}
.post-card {
  background: var(--surface-inset);
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  padding: 10px 12px;
  margin-bottom: 6px;
}
.post-top {
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
.status-badge--scheduled, .status-badge--posted {
  color: var(--secondary);
}
.schedule-row {
  display: flex;
  gap: 8px;
  margin-top: 8px;
  align-items: center;
}
.add-form {
  display: flex;
  gap: 6px;
}
.add-form input {
  flex: 1;
  background: var(--surface-inset);
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  color: var(--text);
  padding: 7px 9px;
  font-size: 12px;
}
.karma-row {
  display: flex;
  gap: 12px;
  font-size: 12px;
  color: var(--text-dim);
  padding: 4px 0;
  border-bottom: 1px solid var(--border);
}
.reply-card {
  background: var(--surface-inset);
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  padding: 12px;
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
