import { ref } from "vue";

/**
 * Generic debounced auto-save. Call `trigger()` whenever the watched
 * data changes; `saveFn` is called after `debounceMs` of inactivity.
 * `status` is one of "idle" | "saving" | "saved" | "error", for a
 * "Saving… / Saved" indicator in the UI.
 *
 * Note on "resume capability": most of PULSE's state is already
 * persisted to the backend immediately on each action (accept/reject,
 * add competitor, etc.) — reloading the page or returning later already
 * shows exactly where you left off via GET requests keyed off the URL's
 * episode id, with no extra mechanism needed. This composable exists for
 * the handful of places with local draft state before an explicit save
 * (e.g. brand settings form fields) — it's a debounce/status utility, not
 * a new persistence layer.
 */
export function useAutoSave(saveFn, { debounceMs = 900 } = {}) {
  const status = ref("idle");
  let timer = null;

  function trigger(...args) {
    status.value = "saving";
    if (timer) clearTimeout(timer);
    timer = setTimeout(async () => {
      try {
        await saveFn(...args);
        status.value = "saved";
        setTimeout(() => {
          if (status.value === "saved") status.value = "idle";
        }, 1800);
      } catch (err) {
        status.value = "error";
      }
    }, debounceMs);
  }

  function cancel() {
    if (timer) clearTimeout(timer);
  }

  return { status, trigger, cancel };
}
