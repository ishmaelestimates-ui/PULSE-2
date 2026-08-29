<template>
  <span class="pill" :class="`pill--${status}`">
    <span class="pill-dot"></span>
    {{ label }}
  </span>
</template>

<script setup>
import { computed } from "vue";

const props = defineProps({
  status: { type: String, required: true },
});

const labels = {
  draft: "Draft",
  uploaded: "Uploaded",
  transcribed: "Transcribed",
  analyzed: "Analyzed",
  reviewed: "Reviewed",
};

const label = computed(() => labels[props.status] ?? props.status);
</script>

<style scoped>
.pill {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-family: var(--font-mono);
  font-size: 11px;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  padding: 4px 9px;
  border-radius: 999px;
  border: 1px solid var(--border-bright);
  color: var(--text-dim);
  background: var(--surface-inset);
}

.pill-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--text-faint);
}

.pill--draft .pill-dot {
  background: var(--text-faint);
}
.pill--uploaded .pill-dot {
  background: var(--clip);
}
.pill--uploaded {
  color: var(--clip);
  border-color: color-mix(in srgb, var(--clip) 40%, var(--border-bright));
}
.pill--transcribed .pill-dot {
  background: var(--bookend);
}
.pill--transcribed {
  color: var(--bookend);
  border-color: color-mix(in srgb, var(--bookend) 40%, var(--border-bright));
}
.pill--analyzed .pill-dot {
  background: var(--primary);
}
.pill--analyzed {
  color: #bcb3ff;
  border-color: color-mix(in srgb, var(--primary) 45%, var(--border-bright));
}
.pill--reviewed .pill-dot {
  background: var(--secondary);
}
.pill--reviewed {
  color: var(--secondary);
  border-color: color-mix(in srgb, var(--secondary) 45%, var(--border-bright));
}
</style>
