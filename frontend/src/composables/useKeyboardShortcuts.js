import { onMounted, onUnmounted } from "vue";

// Shared shortcut reference list (used by both the registration
// composable and the help modal, so they can't drift apart).
export const SHORTCUT_LIST = [
  { keys: "Ctrl/Cmd + S", description: "Confirm everything is saved" },
  { keys: "A", description: "Accept the focused moment" },
  { keys: "R", description: "Reject the focused moment" },
  { keys: "E", description: "Export accepted moments to Resolve (CSV)" },
  { keys: "Shift + →", description: "Next episode" },
  { keys: "Shift + ←", description: "Previous episode" },
  { keys: "?", description: "Show this shortcut list" },
];

function isTypingTarget(el) {
  if (!el) return false;
  const tag = el.tagName?.toLowerCase();
  return tag === "input" || tag === "textarea" || tag === "select" || el.isContentEditable;
}

/**
 * Registers a set of keyboard shortcuts for as long as the calling
 * component is mounted. `handlers` maps a normalized key description
 * (see below) to a callback. Typing in an input/textarea/select is
 * ignored so shortcuts don't fire while someone's filling out a form.
 *
 * Supported key strings: "a", "r", "e", "?", "shift+arrowright",
 * "shift+arrowleft", "ctrl+s" (also matches Cmd+S on Mac).
 */
export function useKeyboardShortcuts(handlers) {
  function onKeydown(e) {
    if (isTypingTarget(e.target)) return;

    const ctrlOrCmd = e.ctrlKey || e.metaKey;
    let key = e.key.toLowerCase();
    if (ctrlOrCmd) key = `ctrl+${key}`;
    if (e.shiftKey && (key === "arrowright" || key === "arrowleft")) key = `shift+${key}`;

    const handler = handlers[key];
    if (handler) {
      e.preventDefault();
      handler(e);
    }
  }

  onMounted(() => window.addEventListener("keydown", onKeydown));
  onUnmounted(() => window.removeEventListener("keydown", onKeydown));
}
