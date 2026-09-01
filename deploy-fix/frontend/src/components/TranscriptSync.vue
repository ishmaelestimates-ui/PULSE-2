<template>
  <div class="transcript" ref="containerEl">
    <div v-if="!segments || segments.length === 0" class="transcript-empty">
      <p v-if="hasPlainTranscript">
        Transcript available, but without timestamps — segment sync isn't
        possible for this episode.
      </p>
      <p v-else>No transcript yet. Upload media and run transcription.</p>
      <p v-if="hasPlainTranscript" class="plain-transcript">{{ plainTranscript }}</p>
    </div>

    <button
      v-else
      v-for="(seg, i) in segments"
      :key="i"
      :ref="(el) => setSegRef(el, i)"
      class="segment"
      :class="{ 'segment--active': i === activeIndex }"
      @click="onClick(seg)"
    >
      <span class="segment-time mono">{{ formatTime(seg.start) }}</span>
      <span v-if="seg.speaker" class="segment-speaker">{{ seg.speaker }}</span>
      <span class="segment-text">{{ seg.text }}</span>
    </button>
  </div>
</template>

<script setup>
import { computed, nextTick, ref, watch } from "vue";

const props = defineProps({
  segments: { type: Array, default: () => [] },
  currentTime: { type: Number, default: 0 },
  plainTranscript: { type: String, default: "" },
  autoScroll: { type: Boolean, default: true },
});

const emit = defineEmits(["segment-click"]);

const containerEl = ref(null);
const segEls = ref([]);

const hasPlainTranscript = computed(() => !!props.plainTranscript?.trim());

function setSegRef(el, i) {
  if (el) segEls.value[i] = el;
}

const activeIndex = computed(() => {
  if (!props.segments?.length) return -1;
  const t = props.currentTime;
  const idx = props.segments.findIndex((s) => t >= s.start && t < s.end);
  if (idx !== -1) return idx;
  // Between segments (gap) or past the last one: highlight the most
  // recent segment whose start has already passed.
  for (let i = props.segments.length - 1; i >= 0; i--) {
    if (t >= props.segments[i].start) return i;
  }
  return -1;
});

watch(activeIndex, async (idx) => {
  if (idx < 0 || !props.autoScroll) return;
  await nextTick();
  const el = segEls.value[idx];
  if (el?.scrollIntoView) {
    el.scrollIntoView({ block: "center", behavior: "smooth" });
  }
});

function onClick(seg) {
  emit("segment-click", seg.start);
}

function formatTime(seconds) {
  const total = Math.floor(seconds || 0);
  const m = Math.floor(total / 60);
  const s = total % 60;
  return `${m}:${String(s).padStart(2, "0")}`;
}
</script>

<style scoped>
.transcript {
  height: 100%;
  overflow-y: auto;
  padding: 4px;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.transcript-empty {
  padding: 32px 16px;
  color: var(--text-dim);
  font-size: 13px;
  text-align: center;
}
.plain-transcript {
  margin-top: 14px;
  text-align: left;
  color: var(--text-dim);
  line-height: 1.7;
  white-space: pre-wrap;
}

.segment {
  display: flex;
  align-items: baseline;
  gap: 10px;
  text-align: left;
  background: transparent;
  border: none;
  border-radius: var(--radius-sm);
  padding: 8px 10px;
  color: var(--text-dim);
  transition: background-color 0.15s var(--ease), color 0.15s var(--ease);
}
.segment:hover {
  background: var(--surface-raised);
  color: var(--text);
}
.segment--active {
  background: color-mix(in srgb, var(--primary) 16%, var(--surface-raised));
  color: var(--text);
  box-shadow: inset 2px 0 0 var(--primary);
}

.segment-time {
  flex-shrink: 0;
  font-size: 11px;
  color: var(--text-faint);
  width: 34px;
}
.segment--active .segment-time {
  color: var(--primary);
}

.segment-speaker {
  flex-shrink: 0;
  font-size: 11px;
  font-weight: 600;
  color: var(--secondary);
}

.segment-text {
  font-size: 13px;
  line-height: 1.5;
}
</style>
