<template>
  <div v-if="snapshot" class="recovery-card" role="alert">
    <div class="recovery-copy">
      <strong>Unsaved work found</strong>
      <span>Recovered draft from {{ formattedTime }}.</span>
    </div>
    <div class="recovery-actions">
      <button class="btn btn--primary btn--small" @click="$emit('recover', snapshot)">Recover</button>
      <button class="btn btn--ghost btn--small" @click="$emit('dismiss', snapshot)">Dismiss</button>
    </div>
  </div>
</template>

<script setup>
import { computed } from "vue";

const props = defineProps({
  snapshot: { type: Object, default: null },
});

defineEmits(["recover", "dismiss"]);

const formattedTime = computed(() => {
  if (!props.snapshot?.saved_at) return "recently";
  const date = new Date(props.snapshot.saved_at);
  if (Number.isNaN(date.getTime())) return "recently";
  return date.toLocaleString();
});
</script>

<style scoped>
.recovery-card {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 12px 14px;
  margin-bottom: 14px;
  border: 1px solid var(--border);
  border-radius: 8px;
  background: var(--surface);
}
.recovery-copy {
  display: flex;
  flex-direction: column;
  gap: 3px;
}
.recovery-copy span {
  color: var(--text-faint);
  font-size: 12px;
}
.recovery-actions {
  display: flex;
  gap: 8px;
  flex-shrink: 0;
}
</style>
