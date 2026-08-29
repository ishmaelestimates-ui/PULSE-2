<template>
  <div class="toast-host">
    <transition-group name="toast">
      <div v-for="t in toasts" :key="t.id" class="toast" :class="`toast--${t.type}`" @click="dismiss(t.id)">
        {{ t.message }}
      </div>
    </transition-group>
  </div>
</template>

<script setup>
import { useToast } from "../composables/useToast";

const { toasts, dismiss } = useToast();
</script>

<style scoped>
.toast-host {
  position: fixed;
  bottom: 20px;
  right: 20px;
  z-index: 150;
  display: flex;
  flex-direction: column;
  gap: 8px;
  align-items: flex-end;
}

.toast {
  background: var(--surface-raised);
  border: 1px solid var(--border-bright);
  border-radius: var(--radius-md);
  padding: 12px 16px;
  font-size: 13px;
  color: var(--text);
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.35);
  cursor: pointer;
  max-width: 320px;
}
.toast--success {
  border-left: 3px solid var(--secondary);
}
.toast--error {
  border-left: 3px solid var(--weak);
}
.toast--info {
  border-left: 3px solid var(--clip);
}

.toast-enter-active,
.toast-leave-active {
  transition: transform 0.25s var(--ease, ease), opacity 0.25s ease;
}
.toast-enter-from {
  transform: translateX(24px);
  opacity: 0;
}
.toast-leave-to {
  transform: translateX(24px);
  opacity: 0;
}

@media (prefers-reduced-motion: reduce) {
  .toast-enter-active,
  .toast-leave-active {
    transition: none;
  }
}
</style>
