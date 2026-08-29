<template>
  <div class="review-list">
    <div v-if="!items.length && emptyLabel" class="empty">{{ emptyLabel }}</div>

    <transition-group name="fade-slide" tag="div">
      <div
        v-for="item in items"
        :key="item.id"
        class="card"
        :class="`card--${kind}`"
      >
      <button class="card-time mono" @click="emit('jump', spanOf(item)[0])">
        {{ formatTime(spanOf(item)[0]) }}
        <template v-if="spanOf(item)[1] !== spanOf(item)[0]">
          – {{ formatTime(spanOf(item)[1]) }}
        </template>
      </button>

      <div class="card-body">
        <p class="card-text">{{ textOf(item) }}</p>
        <div class="card-meta">
          <span v-if="item.decision_reference?.confidence !== undefined" class="confidence">
            {{ Math.round(item.decision_reference.confidence * 100) }}% confidence
          </span>
          <span v-if="item.decision_reference?.reason" class="reason">
            {{ item.decision_reference.reason }}
          </span>
        </div>
        <div v-if="hypeMap[item.id]" class="hype-row">
          <div v-if="hypeMap[item.id].score !== undefined" class="hype-badge" :title="'AI-estimated hype score (not measured engagement)'">
            <div class="hype-bar">
              <div class="hype-fill" :style="{ width: hypeMap[item.id].score + '%' }"></div>
            </div>
            <span class="hype-value mono">{{ hypeMap[item.id].score }}</span>
          </div>
          <span v-if="hypeMap[item.id].viralLabel" class="viral-badge" :class="`viral-badge--${hypeMap[item.id].viralLabel}`">
            {{ viralIcon(hypeMap[item.id].viralLabel) }} {{ hypeMap[item.id].viralLabel }}
            <template v-if="hypeMap[item.id].platform"> · {{ hypeMap[item.id].platform }}</template>
          </span>
        </div>
      </div>

      <div class="card-actions">
        <button
          class="action-btn action-btn--accept pulse-on-click"
          :class="{ 'action-btn--active': item.status === 'accepted', 'check-pop': item.status === 'accepted' }"
          title="Accept"
          @click="emit('set-status', item.id, 'accepted')"
        >
          ✓
        </button>
        <button
          class="action-btn action-btn--reject pulse-on-click"
          :class="{ 'action-btn--active': item.status === 'rejected' }"
          title="Reject"
          @click="emit('set-status', item.id, 'rejected')"
        >
          ✕
        </button>
      </div>
      </div>
    </transition-group>
  </div>
</template>

<script setup>
defineProps({
  items: { type: Array, default: () => [] },
  kind: { type: String, default: "clip" },
  emptyLabel: { type: String, default: "" },
  hypeMap: { type: Object, default: () => ({}) },
});

const emit = defineEmits(["set-status", "jump"]);

const VIRAL_ICONS = { viral: "🔥", high: "📈", moderate: "📊", low: "📉" };
function viralIcon(label) {
  return VIRAL_ICONS[label] || "";
}

function spanOf(item) {
  const ref_ = item.decision_reference || {};
  if ("start" in ref_ && "end" in ref_) return [ref_.start, ref_.end];
  const t = ref_.timestamp ?? 0;
  return [t, t];
}

function textOf(item) {
  const ref_ = item.decision_reference || {};
  return ref_.description || ref_.hook || ref_.reason || "";
}

function formatTime(seconds) {
  const total = Math.floor(seconds || 0);
  const m = Math.floor(total / 60);
  const s = total % 60;
  return `${m}:${String(s).padStart(2, "0")}`;
}
</script>

<style scoped>
.review-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 14px;
}

.empty {
  color: var(--text-faint);
  font-size: 13px;
  padding: 20px 6px;
  text-align: center;
}

.card {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  background: var(--surface-inset);
  border: 1px solid var(--border);
  border-left: 3px solid var(--border-bright);
  border-radius: var(--radius-md);
  padding: 10px 12px;
}
.card--strong {
  border-left-color: var(--strong);
}
.card--weak {
  border-left-color: var(--weak);
}
.card--clip {
  border-left-color: var(--clip);
}
.card--bookend {
  border-left-color: var(--bookend);
}

.card-time {
  flex-shrink: 0;
  background: transparent;
  border: none;
  color: var(--text-dim);
  font-size: 11px;
  padding: 2px 0;
  white-space: nowrap;
}
.card-time:hover {
  color: var(--primary);
}

.card-body {
  flex: 1;
  min-width: 0;
}
.card-text {
  font-size: 13px;
  color: var(--text);
  line-height: 1.45;
}
.card-meta {
  display: flex;
  gap: 8px;
  margin-top: 4px;
  flex-wrap: wrap;
}
.confidence {
  font-size: 10.5px;
  color: var(--secondary);
  font-family: var(--font-mono);
}
.reason {
  font-size: 11px;
  color: var(--text-faint);
  font-style: italic;
}

.hype-row {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-top: 6px;
  flex-wrap: wrap;
}
.hype-badge {
  display: flex;
  align-items: center;
  gap: 5px;
}
.hype-bar {
  width: 44px;
  height: 4px;
  border-radius: 999px;
  background: var(--surface);
  overflow: hidden;
}
.hype-fill {
  height: 100%;
  background: var(--primary);
}
.hype-value {
  font-size: 10px;
  color: var(--text-faint);
}
.viral-badge {
  font-size: 10px;
  padding: 2px 7px;
  border-radius: 999px;
  border: 1px solid var(--border-bright);
  color: var(--text-dim);
  text-transform: capitalize;
}
.viral-badge--viral {
  color: var(--weak);
  border-color: color-mix(in srgb, var(--weak) 45%, var(--border-bright));
}
.viral-badge--high {
  color: var(--secondary);
  border-color: color-mix(in srgb, var(--secondary) 45%, var(--border-bright));
}
.viral-badge--moderate {
  color: var(--clip);
  border-color: color-mix(in srgb, var(--clip) 45%, var(--border-bright));
}
.viral-badge--low {
  color: var(--text-faint);
}

.card-actions {
  flex-shrink: 0;
  display: flex;
  gap: 4px;
}
.action-btn {
  width: 24px;
  height: 24px;
  border-radius: 6px;
  border: 1px solid var(--border-bright);
  background: var(--surface);
  color: var(--text-faint);
  font-size: 11px;
  display: flex;
  align-items: center;
  justify-content: center;
}
.action-btn--accept.action-btn--active {
  background: var(--secondary);
  border-color: var(--secondary);
  color: #06170d;
}
.action-btn--reject.action-btn--active {
  background: var(--weak);
  border-color: var(--weak);
  color: #200608;
}
.action-btn:hover {
  filter: brightness(1.2);
}
</style>
