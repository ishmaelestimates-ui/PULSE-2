<template>
  <div class="detail-view">
    <div v-if="loading" class="state-msg">Loading episode…</div>
    <div v-else-if="loadError" class="state-msg state-msg--error">{{ loadError }}</div>

    <template v-else>
      <div class="detail-header">
        <div class="header-left">
          <router-link to="/" class="back-link">← Episodes</router-link>
          <h1>{{ episode.title }}</h1>
          <StatusPill :status="derivedStatus" />
        </div>
        <ExportBar :episode-id="episodeId" :accepted-count="acceptedCount" @exported="handleExported" />
      </div>

      <ol class="workflow-steps">
        <li
          v-for="step in workflowSteps"
          :key="step.key"
          class="workflow-step"
          :class="`workflow-step--${step.state}`"
        >
          <span class="step-icon">
            <span v-if="step.state === 'done'">✓</span>
            <span v-else-if="step.state === 'active'" class="step-spinner"></span>
            <span v-else>{{ step.index }}</span>
          </span>
          <span class="step-label">{{ step.label }}</span>
        </li>
      </ol>

      <div v-if="actionError" class="banner banner--error">
        {{ actionError }}
        <button class="banner-dismiss" @click="actionError = ''">✕</button>
      </div>

      <div class="action-row">
        <button class="btn btn--primary pulse-on-click" :disabled="primaryAction.disabled" @click="primaryAction.handler">
          {{ primaryAction.label }}
        </button>
        <button
          v-for="sa in secondaryActions"
          :key="sa.key"
          class="btn btn--ghost btn--small"
          :disabled="sa.disabled"
          @click="sa.handler"
        >
          {{ sa.label }}
        </button>
      </div>

      <div class="workstation">
        <div class="col-main">
          <UploadDropzone
            v-if="!primaryMediaFile"
            :uploading="uploading"
            :progress="uploadProgress"
            @file-selected="handleUpload"
          />
          <MediaPlayer
            v-else
            ref="playerRef"
            :media-file="primaryMediaFile"
            :reviews="episode.reviews"
            :duration="episode.duration || 0"
            @time-update="currentTime = $event"
          />
          <UploadDropzone
            v-if="primaryMediaFile"
            class="reupload"
            :uploading="uploading"
            :progress="uploadProgress"
            @file-selected="handleUpload"
          />
        </div>

        <div class="col-side">
          <ReviewPanel
            :reviews="episode.reviews"
            :segments="episode.transcript_segments || []"
            :transcript="episode.transcript || ''"
            :current-time="currentTime"
            :episode-id="episodeId"
            :has-video="primaryMediaFile?.media_type === 'video'"
            :campaign="campaign"
            @seek="handleSeek"
            @set-status="handleSetStatus"
            @campaign-updated="(pack) => (campaign = pack)"
          />
        </div>
      </div>
    </template>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from "vue";
import { useRouter } from "vue-router";
import api from "../api/client";
import StatusPill from "../components/StatusPill.vue";
import MediaPlayer from "../components/MediaPlayer.vue";
import ReviewPanel from "../components/ReviewPanel.vue";
import UploadDropzone from "../components/UploadDropzone.vue";
import ExportBar from "../components/ExportBar.vue";
import { useToast } from "../composables/useToast";
import { useKeyboardShortcuts } from "../composables/useKeyboardShortcuts";

const props = defineProps({
  id: { type: Number, required: true },
});

const router = useRouter();
const toast = useToast();

const episodeId = props.id;

const episode = ref(null);
const mediaFiles = ref([]);
const loading = ref(true);
const loadError = ref("");
const actionError = ref("");

const uploading = ref(false);
const uploadProgress = ref(0);
const transcribing = ref(false);
const analyzing = ref(false);
const hasExported = ref(false);

const currentTime = ref(0);
const playerRef = ref(null);
const campaign = ref(null);

const primaryMediaFile = computed(() =>
  mediaFiles.value.length ? mediaFiles.value[mediaFiles.value.length - 1] : null
);

const hasTranscript = computed(() => !!episode.value?.transcript?.trim());

const reviews = computed(() => episode.value?.reviews || []);
const acceptedCount = computed(() => reviews.value.filter((r) => r.status === "accepted").length);
const reviewsFullyDecided = computed(
  () => reviews.value.length > 0 && reviews.value.every((r) => r.status !== "recommended")
);

const derivedStatus = computed(() => {
  if (reviews.value.some((r) => r.status === "accepted" || r.status === "rejected")) return "reviewed";
  if (reviews.value.length || episode.value?.analysis) return "analyzed";
  if (hasTranscript.value) return "transcribed";
  if (primaryMediaFile.value) return "uploaded";
  return "draft";
});

// --- Workflow step indicators -------------------------------------------
const workflowSteps = computed(() => {
  const steps = [
    { key: "upload", label: "Upload", done: !!primaryMediaFile.value, loading: uploading.value },
    { key: "transcribe", label: "Transcribe", done: hasTranscript.value, loading: transcribing.value },
    { key: "analyze", label: "Analyze", done: !!episode.value?.analysis, loading: analyzing.value },
    { key: "review", label: "Review", done: reviewsFullyDecided.value, loading: false },
    { key: "export", label: "Export", done: hasExported.value, loading: false },
    { key: "campaign", label: "Campaign", done: !!campaign.value, loading: false },
  ];
  let currentAssigned = false;
  return steps.map((s, i) => {
    let state = "pending";
    if (s.done) state = "done";
    else if (s.loading) state = "active";
    else if (!currentAssigned) {
      state = "active";
      currentAssigned = true;
    }
    return { ...s, index: i + 1, state };
  });
});

// --- Contextual primary/secondary actions -------------------------------
const primaryAction = computed(() => {
  if (!primaryMediaFile.value) {
    return { label: "Upload media to begin", disabled: true, handler: () => {} };
  }
  if (!hasTranscript.value) {
    return {
      label: transcribing.value ? "Transcribing…" : "▶ Transcribe",
      disabled: transcribing.value,
      handler: handleTranscribe,
    };
  }
  if (!episode.value?.analysis) {
    return {
      label: analyzing.value ? "Analyzing…" : "▶ Run analysis",
      disabled: analyzing.value,
      handler: handleAnalyze,
    };
  }
  if (!reviewsFullyDecided.value) {
    return { label: "Review moments below", disabled: true, handler: () => {} };
  }
  if (!campaign.value) {
    return { label: "Generate campaign in the Campaign tab", disabled: true, handler: () => {} };
  }
  return { label: "All caught up", disabled: true, handler: () => {} };
});

const secondaryActions = computed(() => {
  const actions = [];
  if (primaryMediaFile.value && !hasTranscript.value) {
    // nothing secondary yet at this stage
  }
  if (hasTranscript.value && !episode.value?.analysis) {
    actions.push({ key: "reupload", label: "Re-transcribe", disabled: transcribing.value, handler: handleTranscribe });
  }
  if (episode.value?.analysis) {
    actions.push({ key: "reanalyze", label: "Re-run analysis", disabled: analyzing.value, handler: handleAnalyze });
  }
  return actions;
});

async function loadAll() {
  loading.value = true;
  loadError.value = "";
  try {
    const [episodeData, mediaStatus] = await Promise.all([
      api.getEpisode(episodeId),
      api.mediaStatus(episodeId),
    ]);
    episode.value = episodeData;
    mediaFiles.value = mediaStatus.media_files;
  } catch (err) {
    loadError.value = err?.response?.data?.detail || "Failed to load episode.";
  } finally {
    loading.value = false;
  }
  // Best-effort — a 404 here just means no campaign has been generated
  // yet, which is the normal starting state, not an error.
  try {
    campaign.value = await api.getCampaign(episodeId);
  } catch (err) {
    campaign.value = null;
  }
}

async function refreshEpisode() {
  episode.value = await api.getEpisode(episodeId);
}

async function refreshMedia() {
  const mediaStatus = await api.mediaStatus(episodeId);
  mediaFiles.value = mediaStatus.media_files;
}

async function handleUpload(file) {
  uploading.value = true;
  uploadProgress.value = 0;
  actionError.value = "";
  try {
    await api.uploadMedia(episodeId, file, (pct) => (uploadProgress.value = pct));
    await Promise.all([refreshMedia(), refreshEpisode()]);
    toast.success("Media uploaded ✅");
  } catch (err) {
    actionError.value = err?.response?.data?.detail || "Upload failed.";
  } finally {
    uploading.value = false;
  }
}

async function handleTranscribe() {
  transcribing.value = true;
  actionError.value = "";
  try {
    await api.transcribe(episodeId, primaryMediaFile.value?.id);
    await Promise.all([refreshEpisode(), refreshMedia()]);
    toast.success("Transcription complete ✅");
  } catch (err) {
    actionError.value = err?.response?.data?.detail || "Transcription failed.";
  } finally {
    transcribing.value = false;
  }
}

async function handleAnalyze() {
  analyzing.value = true;
  actionError.value = "";
  try {
    await api.analyze(episodeId);
    await refreshEpisode();
    toast.success("Analysis complete ✅");
  } catch (err) {
    actionError.value = err?.response?.data?.detail || "Analysis failed.";
  } finally {
    analyzing.value = false;
  }
}

async function handleSetStatus(reviewId, statusValue) {
  const target = episode.value.reviews.find((r) => r.id === reviewId);
  const previous = target?.status;
  if (target) target.status = statusValue; // optimistic
  try {
    await api.updateReview(episodeId, reviewId, statusValue);
  } catch (err) {
    if (target) target.status = previous;
    actionError.value = err?.response?.data?.detail || "Failed to update review.";
  }
}

function handleExported() {
  hasExported.value = true;
  toast.success("CSV exported for Resolve ✅");
}

function handleSeek(time) {
  currentTime.value = time;
  playerRef.value?.seekTo(time);
}

// --- Keyboard shortcuts (see composables/useKeyboardShortcuts.js) -------
const focusedReviewId = ref(null);

function focusableReviews() {
  return reviews.value.filter((r) => r.decision_type === "strong_moment" || r.decision_type === "clip_candidate");
}

function currentFocusedIndex() {
  const list = focusableReviews();
  if (focusedReviewId.value == null) return list.length ? 0 : -1;
  const idx = list.findIndex((r) => r.id === focusedReviewId.value);
  return idx === -1 ? (list.length ? 0 : -1) : idx;
}

useKeyboardShortcuts({
  "ctrl+s": () => toast.info("Everything here saves automatically — nothing to do 👍"),
  a: () => {
    const list = focusableReviews();
    const idx = currentFocusedIndex();
    if (idx === -1) return;
    handleSetStatus(list[idx].id, "accepted");
    toast.success("Accepted ✅");
  },
  r: () => {
    const list = focusableReviews();
    const idx = currentFocusedIndex();
    if (idx === -1) return;
    handleSetStatus(list[idx].id, "rejected");
  },
  e: () => {
    if (acceptedCount.value === 0) return;
    window.location.href = api.exportMarkersUrl(episodeId);
    handleExported();
  },
  "shift+arrowright": async () => {
    try {
      const list = await api.listEpisodes();
      const idx = list.findIndex((e) => e.id === episodeId);
      if (idx !== -1 && idx < list.length - 1) router.push(`/episodes/${list[idx + 1].id}`);
    } catch (e) {
      // non-fatal
    }
  },
  "shift+arrowleft": async () => {
    try {
      const list = await api.listEpisodes();
      const idx = list.findIndex((e) => e.id === episodeId);
      if (idx > 0) router.push(`/episodes/${list[idx - 1].id}`);
    } catch (e) {
      // non-fatal
    }
  },
});

onMounted(loadAll);
</script>

<style scoped>
.detail-view {
  max-width: 1400px;
  width: 100%;
  margin: 0 auto;
  padding: 24px 24px 48px;
  display: flex;
  flex-direction: column;
  min-height: 0;
  flex: 1;
}

.state-msg {
  padding: 60px 0;
  text-align: center;
  color: var(--text-dim);
}
.state-msg--error {
  color: var(--weak);
}

.detail-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  flex-wrap: wrap;
  margin-bottom: 14px;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.back-link {
  font-size: 12px;
  color: var(--text-faint);
  text-decoration: none;
}
.back-link:hover {
  color: var(--text-dim);
}

.header-left h1 {
  font-size: 20px;
}

.workflow-steps {
  display: flex;
  align-items: center;
  gap: 4px;
  list-style: none;
  padding: 0;
  margin: 0 0 16px;
}
.workflow-step {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 12px 6px 6px;
  border-radius: 999px;
  background: var(--surface-inset);
  border: 1px solid var(--border);
}
.workflow-step:not(:last-child) {
  margin-right: 6px;
}
.step-icon {
  width: 20px;
  height: 20px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 10.5px;
  font-family: var(--font-mono);
  background: var(--surface);
  color: var(--text-faint);
  border: 1px solid var(--border-bright);
  flex-shrink: 0;
}
.step-label {
  font-size: 11.5px;
  color: var(--text-faint);
}
.workflow-step--done .step-icon {
  background: var(--secondary);
  border-color: var(--secondary);
  color: #06170d;
}
.workflow-step--done .step-label {
  color: var(--text-dim);
}
.workflow-step--active {
  border-color: var(--primary);
}
.workflow-step--active .step-icon {
  border-color: var(--primary);
  color: var(--primary);
}
.workflow-step--active .step-label {
  color: var(--text);
  font-weight: 600;
}
.step-spinner {
  width: 9px;
  height: 9px;
  border-radius: 50%;
  border: 2px solid var(--primary);
  border-top-color: transparent;
  animation: spin 0.7s linear infinite;
}
@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}
@media (prefers-reduced-motion: reduce) {
  .step-spinner {
    animation: none;
  }
}

.banner {
  padding: 10px 14px;
  border-radius: var(--radius-md);
  font-size: 12.5px;
  margin-bottom: 14px;
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.banner--error {
  background: color-mix(in srgb, var(--weak) 14%, var(--surface));
  border: 1px solid color-mix(in srgb, var(--weak) 40%, var(--border));
  color: var(--weak);
}
.banner-dismiss {
  background: transparent;
  border: none;
  color: inherit;
  font-size: 12px;
}

.action-row {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 16px;
}
.hint {
  font-size: 12px;
  color: var(--text-faint);
}

.btn {
  font-family: var(--font-body);
  font-weight: 600;
  font-size: 13px;
  border-radius: var(--radius-md);
  padding: 9px 16px;
  border: 1px solid var(--border-bright);
  background: var(--surface-raised);
  color: var(--text);
}
.btn:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}
.btn--ghost:not(:disabled):hover {
  border-color: var(--primary);
  color: var(--primary);
}
.btn--small {
  padding: 7px 12px;
  font-size: 12px;
}
.btn--primary {
  background: var(--primary);
  border-color: var(--primary);
  color: white;
}
.btn--primary:not(:disabled):hover {
  filter: brightness(1.1);
}

.workstation {
  display: grid;
  grid-template-columns: 1.6fr 1fr;
  gap: 18px;
  flex: 1;
  min-height: 0;
  align-items: start;
}

.col-main {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.reupload {
  padding: 16px;
}

.col-side {
  height: 640px;
}

@media (max-width: 980px) {
  .workstation {
    grid-template-columns: 1fr;
  }
  .col-side {
    height: 480px;
  }
}
</style>
