<template>
  <div class="panel">
    <div class="tabs">
      <button
        v-for="tab in tabs"
        :key="tab.id"
        class="tab"
        :class="{ 'tab--active': activeTab === tab.id }"
        @click="activeTab = tab.id"
      >
        {{ tab.label }}
        <span v-if="tab.count !== null" class="tab-count">{{ tab.count }}</span>
      </button>
    </div>

    <div class="tab-body">
      <TranscriptSync
        v-if="activeTab === 'transcript'"
        :segments="segments"
        :plain-transcript="transcript"
        :current-time="currentTime"
        @segment-click="(t) => emit('seek', t)"
      />

      <ReviewList
        v-else-if="activeTab === 'strong'"
        :items="strongMoments"
        kind="strong"
        :hype-map="hypeMap"
        empty-label="No strong moments recommended yet."
        @set-status="onSetStatus"
        @jump="(t) => emit('seek', t)"
      />

      <ReviewList
        v-else-if="activeTab === 'weak'"
        :items="weakSections"
        kind="weak"
        empty-label="No weak sections recommended yet."
        @set-status="onSetStatus"
        @jump="(t) => emit('seek', t)"
      />

      <ReviewList
        v-else-if="activeTab === 'clips'"
        :items="clipCandidates"
        kind="clip"
        :hype-map="hypeMap"
        empty-label="No clip candidates recommended yet."
        @set-status="onSetStatus"
        @jump="(t) => emit('seek', t)"
      />

      <div v-else-if="activeTab === 'summary'" class="summary">
        <div class="stat-grid">
          <div class="stat">
            <span class="stat-value">{{ reviews.length }}</span>
            <span class="stat-label">Total recommendations</span>
          </div>
          <div class="stat stat--accept">
            <span class="stat-value">{{ counts.accepted }}</span>
            <span class="stat-label">Accepted</span>
          </div>
          <div class="stat stat--reject">
            <span class="stat-value">{{ counts.rejected }}</span>
            <span class="stat-label">Rejected</span>
          </div>
          <div class="stat">
            <span class="stat-value">{{ counts.recommended }}</span>
            <span class="stat-label">Pending review</span>
          </div>
        </div>

        <div class="progress-block">
          <div class="progress-label">
            <span>Review progress</span>
            <span class="mono">{{ reviewedPct }}%</span>
          </div>
          <div class="progress-track">
            <div class="progress-fill" :style="{ width: reviewedPct + '%' }"></div>
          </div>
        </div>

        <div class="breakdown">
          <div class="breakdown-row">
            <span class="dot dot--strong"></span> Strong moments
            <span class="mono">{{ strongMoments.length }}</span>
          </div>
          <div class="breakdown-row">
            <span class="dot dot--weak"></span> Weak sections
            <span class="mono">{{ weakSections.length }}</span>
          </div>
          <div class="breakdown-row">
            <span class="dot dot--clip"></span> Clip candidates
            <span class="mono">{{ clipCandidates.length }}</span>
          </div>
        </div>

        <div v-if="bookends.length" class="bookends">
          <h4>Opening / closing candidates</h4>
          <ReviewList
            :items="bookends"
            kind="bookend"
            empty-label=""
            @set-status="onSetStatus"
            @jump="(t) => emit('seek', t)"
          />
        </div>
      </div>

      <ColoringPanel
        v-else-if="activeTab === 'coloring'"
        :episode-id="episodeId"
        :has-video="hasVideo"
      />

      <CampaignPanel
        v-else-if="activeTab === 'campaign'"
        :episode-id="episodeId"
        :has-accepted-content="hasAcceptedContent"
        @seek="onCampaignSeek"
        @campaign-updated="(pack) => emit('campaign-updated', pack)"
      />

      <PRPanel v-else-if="activeTab === 'pr'" :episode-id="episodeId" />

      <RedditPanel v-else-if="activeTab === 'reddit'" :episode-id="episodeId" />

      <FilmPanel v-else-if="activeTab === 'film'" :episode-id="episodeId" @seek="(t) => emit('seek', t)" />

      <DashboardPanel v-else-if="activeTab === 'dashboard'" :episode-id="episodeId" />

      <FamePanel v-else-if="activeTab === 'fame'" :episode-id="episodeId" />
    </div>
  </div>
</template>

<script setup>
import { computed, ref } from "vue";
import TranscriptSync from "./TranscriptSync.vue";
import ReviewList from "./ReviewList.vue";
import ColoringPanel from "./ColoringPanel.vue";
import CampaignPanel from "./CampaignPanel.vue";
import PRPanel from "./PRPanel.vue";
import RedditPanel from "./RedditPanel.vue";
import FilmPanel from "./FilmPanel.vue";
import DashboardPanel from "./DashboardPanel.vue";
import FamePanel from "./FamePanel.vue";

const props = defineProps({
  reviews: { type: Array, default: () => [] },
  segments: { type: Array, default: () => [] },
  transcript: { type: String, default: "" },
  currentTime: { type: Number, default: 0 },
  episodeId: { type: Number, default: null },
  hasVideo: { type: Boolean, default: false },
  campaign: { type: Object, default: null },
});

const emit = defineEmits(["seek", "set-status", "campaign-updated"]);

const activeTab = ref("transcript");

const byType = (type) => props.reviews.filter((r) => r.decision_type === type);

const strongMoments = computed(() => byType("strong_moment"));
const weakSections = computed(() => byType("weak_section"));
const clipCandidates = computed(() => byType("clip_candidate"));
const bookends = computed(() => [...byType("opening"), ...byType("closing")]);

const hasAcceptedContent = computed(() =>
  props.reviews.some(
    (r) =>
      r.status === "accepted" &&
      (r.decision_type === "strong_moment" || r.decision_type === "clip_candidate")
  )
);

// Merge hype scores + viral predictions from the campaign pack (if any)
// into a single map keyed by review_id, for ReviewList badges.
const hypeMap = computed(() => {
  if (!props.campaign) return {};
  const map = {};
  for (const h of props.campaign.hype_scores || []) {
    map[h.review_id] = { ...(map[h.review_id] || {}), score: h.score };
  }
  for (const v of props.campaign.viral_predictions || []) {
    map[v.review_id] = {
      ...(map[v.review_id] || {}),
      viralLabel: v.label,
      platform: v.platform,
    };
  }
  return map;
});

function onCampaignSeek(payload) {
  if (typeof payload === "number") {
    emit("seek", payload);
    return;
  }
  // Hook items reference a review_id but not a raw timestamp — resolve
  // it against the full review list before asking the player to seek.
  const review = props.reviews.find((r) => r.id === payload.reviewId);
  if (!review) return;
  const ref_ = review.decision_reference || {};
  const t = "start" in ref_ ? ref_.start : ref_.timestamp || 0;
  emit("seek", t);
}

const counts = computed(() => ({
  recommended: props.reviews.filter((r) => r.status === "recommended").length,
  accepted: props.reviews.filter((r) => r.status === "accepted").length,
  rejected: props.reviews.filter((r) => r.status === "rejected").length,
}));

const reviewedPct = computed(() => {
  if (!props.reviews.length) return 0;
  const decided = counts.value.accepted + counts.value.rejected;
  return Math.round((decided / props.reviews.length) * 100);
});

const tabs = computed(() => [
  { id: "transcript", label: "Transcript", count: null },
  { id: "strong", label: "Strong", count: strongMoments.value.length },
  { id: "weak", label: "Weak", count: weakSections.value.length },
  { id: "clips", label: "Clips", count: clipCandidates.value.length },
  { id: "summary", label: "Summary", count: null },
  { id: "coloring", label: "Coloring", count: null },
  { id: "campaign", label: "Campaign", count: null },
  { id: "pr", label: "PR", count: null },
  { id: "reddit", label: "Reddit", count: null },
  { id: "film", label: "Film", count: null },
  { id: "dashboard", label: "Dashboard", count: null },
  { id: "fame", label: "Fame", count: null },
]);

function onSetStatus(reviewId, status) {
  emit("set-status", reviewId, status);
}
</script>

<style scoped>
.panel {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  overflow: hidden;
}

.tabs {
  display: flex;
  border-bottom: 1px solid var(--border);
  background: var(--surface-inset);
  flex-shrink: 0;
  overflow-x: auto;
}

.tab {
  background: transparent;
  border: none;
  border-bottom: 2px solid transparent;
  color: var(--text-faint);
  font-family: var(--font-body);
  font-weight: 600;
  font-size: 12.5px;
  padding: 12px 14px;
  display: flex;
  align-items: center;
  gap: 6px;
  white-space: nowrap;
}
.tab--active {
  color: var(--text);
  border-bottom-color: var(--primary);
}
.tab-count {
  font-family: var(--font-mono);
  font-size: 10.5px;
  color: var(--text-faint);
  background: var(--surface);
  border-radius: 999px;
  padding: 1px 6px;
}
.tab--active .tab-count {
  color: var(--primary);
}

.tab-body {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
}

.summary {
  padding: 18px;
}

.stat-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 10px;
  margin-bottom: 20px;
}
.stat {
  background: var(--surface-inset);
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  padding: 14px;
}
.stat-value {
  display: block;
  font-family: var(--font-display);
  font-size: 22px;
  font-weight: 700;
}
.stat-label {
  font-size: 11px;
  color: var(--text-faint);
}
.stat--accept .stat-value {
  color: var(--secondary);
}
.stat--reject .stat-value {
  color: var(--weak);
}

.progress-block {
  margin-bottom: 20px;
}
.progress-label {
  display: flex;
  justify-content: space-between;
  font-size: 12px;
  color: var(--text-dim);
  margin-bottom: 6px;
}
.progress-track {
  height: 6px;
  border-radius: 999px;
  background: var(--surface-inset);
  overflow: hidden;
}
.progress-fill {
  height: 100%;
  background: linear-gradient(90deg, var(--primary), var(--secondary));
  transition: width 0.25s var(--ease);
}

.breakdown {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-bottom: 20px;
}
.breakdown-row {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12.5px;
  color: var(--text-dim);
}
.breakdown-row .mono {
  margin-left: auto;
  color: var(--text);
}
.dot {
  width: 8px;
  height: 8px;
  border-radius: 2px;
}
.dot--strong {
  background: var(--strong);
}
.dot--weak {
  background: var(--weak);
}
.dot--clip {
  background: var(--clip);
}

.bookends h4 {
  font-size: 12px;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  color: var(--text-faint);
  margin-bottom: 10px;
}
</style>
