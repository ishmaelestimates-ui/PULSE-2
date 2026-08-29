<template>
  <div class="campaign">
    <div class="header-row">
      <button
        class="btn btn--primary"
        :disabled="generating || !hasAcceptedContent"
        @click="generate"
      >
        {{ generating ? "Generating…" : campaign ? "Regenerate campaign" : "Generate campaign" }}
      </button>
      <div v-if="campaign" class="download-group">
        <button class="btn-link" @click="downloadJson">Download JSON</button>
        <button class="btn-link" @click="downloadMarkdown">Download Markdown</button>
      </div>
    </div>

    <p v-if="!hasAcceptedContent" class="hint">
      Accept at least one strong moment or clip in the Review tab before
      generating a campaign.
    </p>
    <p v-if="error" class="hint hint--error">{{ error }}</p>
    <p v-if="loadingExisting" class="hint">Loading existing campaign…</p>

    <template v-if="campaign">
      <p class="disclaimer">{{ campaign.disclaimer }}</p>

      <section class="block">
        <div class="block-header">
          <h4>Social posts</h4>
        </div>
        <div class="platform-tabs">
          <button
            v-for="p in platformKeys"
            :key="p"
            class="platform-tab"
            :class="{ 'platform-tab--active': activePlatform === p }"
            @click="activePlatform = p"
          >
            {{ p }}
          </button>
        </div>
        <div v-if="activePost" class="post-card">
          <p class="post-text">{{ activePost.text }}</p>
          <p v-if="activePost.hashtags?.length" class="post-hashtags">
            {{ activePost.hashtags.map((h) => "#" + h.replace(/^#/, "")).join(" ") }}
          </p>
          <button class="btn-link" @click="copy(postFullText(activePost), 'post-' + activePlatform)">
            {{ copiedKey === "post-" + activePlatform ? "Copied!" : "Copy" }}
          </button>
        </div>
      </section>

      <section class="block">
        <h4>Hooks</h4>
        <div v-for="(hook, i) in campaign.hooks" :key="i" class="hook-row">
          <button
            v-if="hook.review_id"
            class="hook-jump"
            title="Jump to this moment"
            @click="jumpToReview(hook.review_id)"
          >
            ↗
          </button>
          <p class="hook-text">{{ hook.text }}</p>
          <div class="score-bar" :title="`Curiosity gap: ${hook.curiosity_gap_score}/10`">
            <div class="score-fill" :style="{ width: hook.curiosity_gap_score * 10 + '%' }"></div>
          </div>
        </div>
      </section>

      <section class="block">
        <h4>Release schedule</h4>
        <p class="hint">{{ campaign.schedule.note }}</p>
        <div class="schedule-grid">
          <div v-for="d in campaign.schedule.suggested_dates" :key="d.platform" class="schedule-row">
            <span class="schedule-platform">{{ d.platform }}</span>
            <span class="mono">{{ d.date }}</span>
            <span class="mono">{{ d.suggested_time }}</span>
          </div>
        </div>
      </section>

      <section class="block">
        <div class="block-header">
          <h4>Press blurb</h4>
          <button class="btn-link" @click="copy(campaign.press_blurb, 'press')">
            {{ copiedKey === "press" ? "Copied!" : "Copy" }}
          </button>
        </div>
        <p class="body-text">{{ campaign.press_blurb }}</p>
      </section>

      <section class="block">
        <div class="block-header">
          <h4>Email newsletter</h4>
          <button class="btn-link" @click="copy(newsletterFullText, 'newsletter')">
            {{ copiedKey === "newsletter" ? "Copied!" : "Copy" }}
          </button>
        </div>
        <p class="newsletter-subject">{{ campaign.newsletter.subject }}</p>
        <p class="newsletter-preview">{{ campaign.newsletter.preview }}</p>
        <p class="body-text">{{ campaign.newsletter.body }}</p>
      </section>

      <section class="block">
        <div class="block-header">
          <h4>Show notes</h4>
          <button class="btn-link" @click="copy(campaign.show_notes, 'notes')">
            {{ copiedKey === "notes" ? "Copied!" : "Copy" }}
          </button>
        </div>
        <pre class="show-notes">{{ campaign.show_notes }}</pre>
      </section>

      <section class="block">
        <h4>60-second trailer cut list</h4>
        <div v-for="(item, i) in campaign.trailer_cutlist" :key="i" class="cut-row" @click="emit('seek', item.start)">
          <span class="cut-time mono">{{ formatTime(item.start) }}–{{ formatTime(item.end) }}</span>
          <span class="cut-label">{{ item.label }}</span>
        </div>
      </section>
    </template>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from "vue";
import api from "../api/client";
import { useToast } from "../composables/useToast";

const toast = useToast();

const props = defineProps({
  episodeId: { type: Number, required: true },
  hasAcceptedContent: { type: Boolean, default: false },
});

const emit = defineEmits(["seek", "campaign-updated"]);

const campaign = ref(null);
const generating = ref(false);
const loadingExisting = ref(true);
const error = ref("");
const copiedKey = ref("");
const activePlatform = ref("tiktok");

const platformKeys = computed(() =>
  campaign.value ? Object.keys(campaign.value.social_posts) : []
);
const activePost = computed(() => campaign.value?.social_posts?.[activePlatform.value]);

const newsletterFullText = computed(() => {
  if (!campaign.value) return "";
  const n = campaign.value.newsletter;
  return `Subject: ${n.subject}\nPreview: ${n.preview}\n\n${n.body}`;
});

function postFullText(post) {
  const tags = post.hashtags?.length
    ? "\n" + post.hashtags.map((h) => "#" + h.replace(/^#/, "")).join(" ")
    : "";
  return post.text + tags;
}

async function loadExisting() {
  loadingExisting.value = true;
  try {
    campaign.value = await api.getCampaign(props.episodeId);
    if (campaign.value.social_posts) {
      activePlatform.value = Object.keys(campaign.value.social_posts)[0] || "tiktok";
    }
  } catch (err) {
    // 404 just means nothing generated yet — not an error state.
  } finally {
    loadingExisting.value = false;
  }
}

async function generate() {
  generating.value = true;
  error.value = "";
  try {
    campaign.value = await api.generateCampaign(props.episodeId);
    activePlatform.value = Object.keys(campaign.value.social_posts)[0] || "tiktok";
    emit("campaign-updated", campaign.value);
    toast.success("Campaign generated successfully ✅");
  } catch (err) {
    error.value = err?.response?.data?.detail || "Failed to generate campaign.";
  } finally {
    generating.value = false;
  }
}

function jumpToReview(reviewId) {
  // Trailer/hook items reference a review_id but not a timestamp
  // directly here — the parent already has the full review list, so we
  // just ask it to resolve + seek.
  emit("seek", { reviewId });
}

async function copy(text, key) {
  try {
    await navigator.clipboard.writeText(text);
    copiedKey.value = key;
    setTimeout(() => {
      if (copiedKey.value === key) copiedKey.value = "";
    }, 1800);
  } catch (err) {
    error.value = "Clipboard access was denied by the browser.";
  }
}

function downloadJson() {
  const blob = new Blob([JSON.stringify(campaign.value, null, 2)], {
    type: "application/json",
  });
  triggerDownload(blob, `campaign-episode-${props.episodeId}.json`);
}

function downloadMarkdown() {
  const c = campaign.value;
  const lines = [`# Campaign — Episode ${props.episodeId}`, ""];
  lines.push("## Social posts", "");
  for (const [platform, post] of Object.entries(c.social_posts)) {
    lines.push(`### ${platform}`, post.text, post.hashtags?.map((h) => "#" + h).join(" ") || "", "");
  }
  lines.push("## Hooks", "");
  for (const h of c.hooks) lines.push(`- (${h.curiosity_gap_score}/10) ${h.text}`);
  lines.push("", "## Press blurb", "", c.press_blurb, "");
  lines.push("## Newsletter", "", `**Subject:** ${c.newsletter.subject}`, `**Preview:** ${c.newsletter.preview}`, "", c.newsletter.body, "");
  lines.push("## Show notes", "", c.show_notes, "");
  lines.push("## Trailer cut list", "");
  for (const item of c.trailer_cutlist) {
    lines.push(`- ${formatTime(item.start)}–${formatTime(item.end)}: ${item.label}`);
  }
  lines.push("", `_${c.disclaimer}_`);

  const blob = new Blob([lines.join("\n")], { type: "text/markdown" });
  triggerDownload(blob, `campaign-episode-${props.episodeId}.md`);
}

function triggerDownload(blob, filename) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

function formatTime(seconds) {
  const total = Math.floor(seconds || 0);
  const m = Math.floor(total / 60);
  const s = total % 60;
  return `${m}:${String(s).padStart(2, "0")}`;
}

onMounted(loadExisting);
</script>

<style scoped>
.campaign {
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.header-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 8px;
}
.download-group {
  display: flex;
  gap: 12px;
}

.hint {
  font-size: 11.5px;
  color: var(--text-faint);
}
.hint--error {
  color: var(--weak);
}

.disclaimer {
  font-size: 11px;
  color: var(--text-faint);
  background: var(--surface-inset);
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  padding: 8px 10px;
  line-height: 1.5;
}

.block h4 {
  font-size: 12px;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  color: var(--text-faint);
  margin-bottom: 10px;
}
.block-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 6px;
}
.block-header h4 {
  margin-bottom: 0;
}

.platform-tabs {
  display: flex;
  gap: 4px;
  flex-wrap: wrap;
  margin-bottom: 8px;
}
.platform-tab {
  background: var(--surface-inset);
  border: 1px solid var(--border);
  color: var(--text-faint);
  font-size: 11px;
  text-transform: capitalize;
  padding: 5px 10px;
  border-radius: 999px;
}
.platform-tab--active {
  background: var(--primary-dim);
  border-color: var(--primary);
  color: white;
}
.post-card {
  background: var(--surface-inset);
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  padding: 12px;
}
.post-text {
  font-size: 13px;
  color: var(--text);
  white-space: pre-wrap;
  line-height: 1.5;
}
.post-hashtags {
  font-size: 11.5px;
  color: var(--clip);
  margin-top: 6px;
}

.hook-row {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 0;
  border-bottom: 1px solid var(--border);
}
.hook-row:last-child {
  border-bottom: none;
}
.hook-jump {
  background: transparent;
  border: none;
  color: var(--primary);
  font-size: 12px;
  flex-shrink: 0;
}
.hook-text {
  flex: 1;
  font-size: 12.5px;
  color: var(--text);
}
.score-bar {
  width: 50px;
  height: 5px;
  border-radius: 999px;
  background: var(--surface-inset);
  overflow: hidden;
  flex-shrink: 0;
}
.score-fill {
  height: 100%;
  background: var(--secondary);
}

.schedule-grid {
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.schedule-row {
  display: grid;
  grid-template-columns: 1fr auto auto;
  gap: 10px;
  font-size: 12px;
  color: var(--text-dim);
  padding: 4px 0;
}
.schedule-platform {
  text-transform: capitalize;
  color: var(--text);
}

.body-text {
  font-size: 12.5px;
  color: var(--text-dim);
  line-height: 1.6;
  white-space: pre-wrap;
}
.newsletter-subject {
  font-size: 13px;
  font-weight: 600;
  color: var(--text);
}
.newsletter-preview {
  font-size: 11.5px;
  color: var(--text-faint);
  margin: 4px 0 10px;
}

.show-notes {
  font-family: var(--font-body);
  font-size: 12.5px;
  color: var(--text-dim);
  white-space: pre-wrap;
  line-height: 1.6;
  max-height: 240px;
  overflow-y: auto;
  margin: 0;
}

.cut-row {
  display: flex;
  gap: 10px;
  padding: 6px 0;
  cursor: pointer;
  border-bottom: 1px solid var(--border);
}
.cut-row:last-child {
  border-bottom: none;
}
.cut-row:hover .cut-label {
  color: var(--primary);
}
.cut-time {
  flex-shrink: 0;
  font-size: 11px;
  color: var(--text-faint);
  width: 90px;
}
.cut-label {
  font-size: 12.5px;
  color: var(--text-dim);
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
