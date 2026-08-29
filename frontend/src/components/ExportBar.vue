<template>
  <div class="export-bar">
    <a
      class="export-btn export-btn--primary pulse-on-click"
      :class="{ 'export-btn--disabled': acceptedCount === 0 }"
      :href="acceptedCount > 0 ? resolveUrl : undefined"
      download
      @click="onExportClick"
    >
      ⇩ Export to Resolve
      <span class="export-count mono">{{ acceptedCount }}</span>
    </a>

    <button class="export-btn export-btn--stub" disabled title="Not yet available">
      Export to Premiere (XML)
      <span class="soon">soon</span>
    </button>

    <button class="export-btn export-btn--stub" disabled title="Not yet available">
      Export to FCP (FCPXML)
      <span class="soon">soon</span>
    </button>

    <button class="export-btn export-btn--stub" disabled title="Not yet available">
      Generate campaign pack
      <span class="soon">soon</span>
    </button>
  </div>
</template>

<script setup>
import { computed } from "vue";
import api from "../api/client";

const props = defineProps({
  episodeId: { type: Number, required: true },
  acceptedCount: { type: Number, default: 0 },
});

const emit = defineEmits(["exported"]);

const resolveUrl = computed(() => api.exportMarkersUrl(props.episodeId));

function onExportClick(evt) {
  if (props.acceptedCount === 0) {
    evt.preventDefault();
    return;
  }
  emit("exported");
}
</script>

<style scoped>
.export-bar {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.export-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-family: var(--font-body);
  font-weight: 600;
  font-size: 12.5px;
  padding: 9px 14px;
  border-radius: var(--radius-md);
  border: 1px solid var(--border-bright);
  background: var(--surface-raised);
  color: var(--text-dim);
  text-decoration: none;
}
.export-btn--primary {
  background: var(--secondary);
  border-color: var(--secondary);
  color: #06170d;
}
.export-btn--primary:hover {
  filter: brightness(1.08);
}
.export-btn--disabled {
  opacity: 0.4;
  pointer-events: none;
}
.export-count {
  background: rgba(0, 0, 0, 0.18);
  border-radius: 999px;
  padding: 1px 6px;
  font-size: 11px;
}

.export-btn--stub {
  cursor: not-allowed;
  opacity: 0.55;
}
.soon {
  font-family: var(--font-mono);
  font-size: 9px;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  color: var(--text-faint);
  border: 1px solid var(--border-bright);
  border-radius: 999px;
  padding: 1px 5px;
}
</style>
