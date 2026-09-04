<template>
  <span class="autosave-indicator" :class="`autosave-indicator--${status}`" role="status" aria-live="polite">
    <span class="autosave-dot" aria-hidden="true"></span>
    <span v-if="status === 'saving'">Saving…</span>
    <span v-else-if="status === 'saved'">Saved</span>
    <span v-else-if="status === 'error'">Save failed</span>
    <span v-else>Auto-save ready</span>
  </span>
</template>

<script setup>
defineProps({
  status: {
    type: String,
    default: "idle",
    validator: (value) => ["idle", "saving", "saved", "error"].includes(value),
  },
});
</script>

<style scoped>
.autosave-indicator {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 11px;
  color: var(--text-faint);
}
.autosave-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: currentColor;
}
.autosave-indicator--saving { color: var(--primary); }
.autosave-indicator--saved { color: var(--secondary); }
.autosave-indicator--error { color: var(--danger, #d66); }
</style>
