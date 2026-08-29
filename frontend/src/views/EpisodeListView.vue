<template>
  <div class="list-view">
    <div class="list-header">
      <div>
        <h1>Episodes</h1>
        <p class="subtitle">{{ episodes.length }} in the queue</p>
      </div>
      <button class="btn btn--primary" @click="showCreate = true">
        + New episode
      </button>
    </div>

    <div v-if="loading" class="state-msg">Loading episodes…</div>
    <div v-else-if="error" class="state-msg state-msg--error">{{ error }}</div>
    <div v-else-if="episodes.length === 0" class="empty">
      <div class="empty-icon">🎬</div>
      <p class="empty-title">No episodes yet</p>
      <p class="text-dim">Create one, then upload media to get started.</p>
      <button class="btn btn--primary empty-cta" @click="showCreate = true">+ New episode</button>
    </div>

    <div v-else class="grid">
      <router-link
        v-for="ep in episodes"
        :key="ep.id"
        :to="`/episodes/${ep.id}`"
        class="card"
      >
        <div class="card-top">
          <h3>{{ ep.title }}</h3>
          <StatusPill :status="ep.status" />
        </div>
        <div class="card-meta mono">
          <span>{{ formatDuration(ep.duration) }}</span>
          <span class="dot">·</span>
          <span>{{ formatDate(ep.created_at) }}</span>
        </div>
        <div class="card-counts">
          <span v-if="ep.media_count" class="count">{{ ep.media_count }} media</span>
          <span v-if="ep.accepted_count" class="count count--accept"
            >{{ ep.accepted_count }} accepted</span
          >
          <span v-if="ep.recommended_count" class="count count--pending"
            >{{ ep.recommended_count }} pending</span
          >
        </div>
      </router-link>
    </div>

    <div v-if="showCreate" class="modal-backdrop" @click.self="showCreate = false">
      <div class="modal">
        <h2>New episode</h2>
        <label class="field">
          <span>Title</span>
          <input
            v-model="newTitle"
            type="text"
            placeholder="e.g. Episode 42 — The Signal and the Noise"
            @keyup.enter="createEpisode"
          />
        </label>
        <p class="hint">
          You can upload media and transcribe right after — a transcript
          isn't required to create the episode.
        </p>
        <div class="modal-actions">
          <button class="btn btn--ghost" @click="showCreate = false">Cancel</button>
          <button
            class="btn btn--primary"
            :disabled="!newTitle.trim() || creating"
            @click="createEpisode"
          >
            {{ creating ? "Creating…" : "Create episode" }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { onMounted, ref } from "vue";
import { useRouter } from "vue-router";
import api from "../api/client";
import StatusPill from "../components/StatusPill.vue";

const router = useRouter();
const episodes = ref([]);
const loading = ref(true);
const error = ref("");

const showCreate = ref(false);
const newTitle = ref("");
const creating = ref(false);

async function load() {
  loading.value = true;
  error.value = "";
  try {
    episodes.value = await api.listEpisodes();
  } catch (err) {
    error.value = err?.response?.data?.detail || "Failed to load episodes.";
  } finally {
    loading.value = false;
  }
}

async function createEpisode() {
  if (!newTitle.value.trim()) return;
  creating.value = true;
  try {
    const episode = await api.createEpisode({ title: newTitle.value.trim() });
    router.push(`/episodes/${episode.id}`);
  } catch (err) {
    error.value = err?.response?.data?.detail || "Failed to create episode.";
  } finally {
    creating.value = false;
  }
}

function formatDuration(seconds) {
  if (!seconds && seconds !== 0) return "—:—";
  const total = Math.round(seconds);
  const h = Math.floor(total / 3600);
  const m = Math.floor((total % 3600) / 60);
  const s = total % 60;
  return h > 0
    ? `${h}:${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`
    : `${m}:${String(s).padStart(2, "0")}`;
}

function formatDate(iso) {
  return new Date(iso).toLocaleDateString(undefined, {
    month: "short",
    day: "numeric",
  });
}

onMounted(load);
</script>

<style scoped>
.list-view {
  max-width: 1100px;
  width: 100%;
  margin: 0 auto;
  padding: 40px 24px 64px;
}

.list-header {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  margin-bottom: 28px;
}

.subtitle {
  color: var(--text-dim);
  margin-top: 6px;
  font-size: 13px;
}

.state-msg {
  color: var(--text-dim);
  padding: 40px 0;
}
.state-msg--error {
  color: var(--weak);
}

.empty {
  padding: 64px 0;
  text-align: center;
  color: var(--text-dim);
}
.empty-icon {
  font-size: 40px;
  margin-bottom: 10px;
}
.empty-title {
  color: var(--text);
  font-size: 16px;
  margin-bottom: 4px;
}
.empty-cta {
  margin-top: 18px;
}

.grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 14px;
}

.card {
  display: block;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  padding: 18px;
  text-decoration: none;
  color: var(--text);
  transition: border-color 0.15s var(--ease), transform 0.15s var(--ease);
}
.card:hover {
  border-color: var(--border-bright);
  transform: translateY(-1px);
}

.card-top {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 10px;
  margin-bottom: 10px;
}
.card-top h3 {
  font-size: 15px;
  font-weight: 600;
  line-height: 1.35;
}

.card-meta {
  color: var(--text-faint);
  font-size: 12px;
  display: flex;
  gap: 8px;
  margin-bottom: 12px;
}

.card-counts {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}
.count {
  font-size: 11px;
  font-family: var(--font-mono);
  color: var(--text-dim);
  background: var(--surface-inset);
  border: 1px solid var(--border);
  border-radius: 999px;
  padding: 3px 8px;
}
.count--accept {
  color: var(--secondary);
}
.count--pending {
  color: var(--bookend);
}

/* Buttons (shared) */
.btn {
  font-family: var(--font-body);
  font-weight: 600;
  font-size: 13px;
  border-radius: var(--radius-md);
  padding: 9px 16px;
  border: 1px solid transparent;
  transition: filter 0.15s var(--ease), border-color 0.15s var(--ease);
}
.btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
.btn--primary {
  background: var(--primary);
  color: white;
  box-shadow: 0 0 0 0 var(--primary-glow);
}
.btn--primary:not(:disabled):hover {
  filter: brightness(1.1);
}
.btn--ghost {
  background: transparent;
  color: var(--text-dim);
  border-color: var(--border-bright);
}
.btn--ghost:hover {
  color: var(--text);
  border-color: var(--text-faint);
}

/* Modal */
.modal-backdrop {
  position: fixed;
  inset: 0;
  background: rgba(5, 5, 10, 0.7);
  backdrop-filter: blur(2px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 40;
}
.modal {
  width: 100%;
  max-width: 420px;
  background: var(--surface-raised);
  border: 1px solid var(--border-bright);
  border-radius: var(--radius-lg);
  padding: 24px;
}
.modal h2 {
  font-size: 17px;
  margin-bottom: 16px;
}
.field {
  display: flex;
  flex-direction: column;
  gap: 6px;
  font-size: 12px;
  color: var(--text-dim);
  margin-bottom: 10px;
}
.field input {
  font-family: var(--font-body);
  font-size: 14px;
  color: var(--text);
  background: var(--surface-inset);
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  padding: 10px 12px;
}
.field input:focus {
  outline: none;
  border-color: var(--primary);
}
.hint {
  font-size: 12px;
  color: var(--text-faint);
  margin-bottom: 20px;
}
.modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}
.text-dim {
  color: var(--text-faint);
  font-size: 13px;
}
.dot {
  color: var(--text-faint);
}
</style>
