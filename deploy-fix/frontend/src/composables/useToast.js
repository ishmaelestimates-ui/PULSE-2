import { reactive } from "vue";

// Module-level reactive queue — same lightweight-singleton pattern as
// useAuth.js, no Pinia dependency needed for this.
const toasts = reactive([]);
let nextId = 1;

function push(message, { type = "success", durationMs = 3200 } = {}) {
  const id = nextId++;
  toasts.push({ id, message, type });
  setTimeout(() => dismiss(id), durationMs);
  return id;
}

function dismiss(id) {
  const idx = toasts.findIndex((t) => t.id === id);
  if (idx !== -1) toasts.splice(idx, 1);
}

export function useToast() {
  return {
    toasts,
    success: (msg, opts) => push(msg, { ...opts, type: "success" }),
    error: (msg, opts) => push(msg, { ...opts, type: "error" }),
    info: (msg, opts) => push(msg, { ...opts, type: "info" }),
    dismiss,
  };
}
