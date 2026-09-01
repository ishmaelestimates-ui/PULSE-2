<template>
  <LoadingScreen v-if="showLoading" @done="showLoading = false" />
  <div v-else class="shell">
    <header class="topbar">
      <router-link to="/" class="brand">
        <span class="brand-mark"></span>
        <span class="brand-word">PULSE <span class="brand-word-sub">STUDIO</span></span>
      </router-link>
      <div class="topbar-meta">
        <span class="live-dot"></span>
        <span class="mono topbar-label">EDITORIAL CONSOLE</span>
        <router-link to="/features" class="settings-link">Features</router-link>
        <button class="settings-link shortcuts-btn" title="Keyboard shortcuts" @click="showShortcuts = true">⌘?</button>
        <router-link to="/settings" class="settings-link">Settings</router-link>
        <span v-if="currentUser" class="settings-link user-chip">{{ currentUser.name || currentUser.email }}</span>
        <router-link v-else to="/login" class="settings-link">Sign in</router-link>
      </div>
    </header>
    <main class="content">
      <router-view />
    </main>
    <ToastHost />
    <KeyboardShortcuts v-if="showShortcuts" @close="showShortcuts = false" />
  </div>
</template>

<script setup>
import { ref } from "vue";
import { useAuth } from "./composables/useAuth";
import LoadingScreen from "./components/LoadingScreen.vue";
import ToastHost from "./components/ToastHost.vue";
import KeyboardShortcuts from "./components/KeyboardShortcuts.vue";

const { currentUser } = useAuth();

// Only show the branded intro once per browser session, not on every
// route change (Vue SPA navigation doesn't reload App.vue, so this only
// naturally fires once per tab anyway — the sessionStorage check guards
// a hard page refresh from replaying it every time too).
const showLoading = ref(!sessionStorage.getItem("pulse_intro_seen"));
if (showLoading.value) {
  sessionStorage.setItem("pulse_intro_seen", "1");
}
const showShortcuts = ref(false);
</script>

<style scoped>
.shell {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}

.topbar {
  height: 56px;
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 20px;
  background: var(--surface);
  border-bottom: 1px solid var(--border);
}

.brand {
  display: flex;
  align-items: center;
  gap: 10px;
  text-decoration: none;
  color: var(--text);
}

.brand-mark {
  width: 18px;
  height: 18px;
  border-radius: 5px;
  background: linear-gradient(135deg, var(--primary), var(--secondary));
  box-shadow: 0 0 16px var(--primary-glow);
}

.brand-word {
  font-family: var(--font-display);
  font-weight: 700;
  font-size: 16px;
  letter-spacing: 0.06em;
}
.brand-word-sub {
  font-weight: 500;
  font-size: 11px;
  letter-spacing: 0.2em;
  color: var(--text-faint);
}

.topbar-meta {
  display: flex;
  align-items: center;
  gap: 8px;
  color: var(--text-faint);
}

.live-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--secondary);
  box-shadow: 0 0 8px var(--secondary);
  animation: pulse 2.4s ease-in-out infinite;
}

.topbar-label {
  font-size: 11px;
  letter-spacing: 0.14em;
}

.settings-link {
  margin-left: 6px;
  padding-left: 14px;
  border-left: 1px solid var(--border);
  font-size: 12px;
  color: var(--text-dim);
  text-decoration: none;
}
.settings-link:hover {
  color: var(--primary);
}
.shortcuts-btn {
  background: transparent;
  border: none;
  font-family: inherit;
}
.user-chip {
  border-left: 1px solid var(--border);
  padding-left: 14px;
  cursor: default;
}
.user-chip:hover {
  color: var(--text-dim);
}

.content {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
}

@keyframes pulse {
  0%,
  100% {
    opacity: 1;
  }
  50% {
    opacity: 0.35;
  }
}

@media (prefers-reduced-motion: reduce) {
  .live-dot {
    animation: none;
  }
}
</style>
