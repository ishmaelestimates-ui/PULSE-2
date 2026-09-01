<template>
  <div class="modal-backdrop" @click.self="emit('close')">
    <div class="modal">
      <div class="modal-header">
        <h3>Keyboard shortcuts</h3>
        <button class="close-btn" @click="emit('close')">✕</button>
      </div>
      <div class="shortcut-row" v-for="s in SHORTCUT_LIST" :key="s.keys">
        <kbd>{{ s.keys }}</kbd>
        <span>{{ s.description }}</span>
      </div>
      <p class="hint">Shortcuts are active on the episode workstation, not while typing in a field.</p>
    </div>
  </div>
</template>

<script setup>
import { SHORTCUT_LIST } from "../composables/useKeyboardShortcuts";

const emit = defineEmits(["close"]);
</script>

<style scoped>
.modal-backdrop {
  position: fixed;
  inset: 0;
  background: rgba(5, 5, 10, 0.7);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 120;
}
.modal {
  width: 100%;
  max-width: 380px;
  background: var(--surface-raised);
  border: 1px solid var(--border-bright);
  border-radius: var(--radius-lg);
  padding: 22px;
}
.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 14px;
}
.modal-header h3 {
  font-size: 15px;
}
.close-btn {
  background: transparent;
  border: none;
  color: var(--text-faint);
  font-size: 14px;
}
.shortcut-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 0;
  border-bottom: 1px solid var(--border);
  font-size: 12.5px;
  color: var(--text-dim);
}
.shortcut-row:last-of-type {
  border-bottom: none;
}
kbd {
  font-family: var(--font-mono);
  font-size: 11px;
  background: var(--surface-inset);
  border: 1px solid var(--border-bright);
  border-radius: 4px;
  padding: 3px 7px;
  color: var(--text);
}
.hint {
  font-size: 11px;
  color: var(--text-faint);
  margin-top: 12px;
}
</style>
