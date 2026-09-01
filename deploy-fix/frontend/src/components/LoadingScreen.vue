<template>
  <transition name="loading-fade">
    <div v-if="visible" class="loading-screen">
      <img src="/logo.svg" class="loading-logo" alt="PULSE" />
      <div class="loading-wordmark">
        <span class="pulse-text">PULSE</span>
        <span class="studio-text">STUDIO</span>
      </div>
      <div class="loading-bar">
        <div class="loading-bar-fill"></div>
      </div>
    </div>
  </transition>
</template>

<script setup>
import { onMounted, ref } from "vue";

const props = defineProps({
  durationMs: { type: Number, default: 2400 },
});
const emit = defineEmits(["done"]);

const visible = ref(true);

// Tries a real audio file first (drop a licensed engine-roar.mp3 into
// frontend/public/ to use it); falls back to a short synthesized sweep
// via the Web Audio API — no fabricated binary asset shipped here. Also
// respects that browsers block autoplay-with-sound until a user gesture;
// failures here are silent by design, the visual animation still runs.
function playIntroSound() {
  const audio = new Audio("/engine-roar.mp3");
  audio.volume = 0.5;
  audio
    .play()
    .then(() => true)
    .catch(() => {
      try {
        playSynthesizedSweep();
      } catch (e) {
        // Autoplay blocked or Web Audio unavailable — fine, silent fallback.
      }
    });
}

function playSynthesizedSweep() {
  const Ctx = window.AudioContext || window.webkitAudioContext;
  if (!Ctx) return;
  const ctx = new Ctx();
  const osc = ctx.createOscillator();
  const gain = ctx.createGain();
  osc.type = "sawtooth";
  osc.frequency.setValueAtTime(60, ctx.currentTime);
  osc.frequency.exponentialRampToValueAtTime(220, ctx.currentTime + 0.6);
  osc.frequency.exponentialRampToValueAtTime(90, ctx.currentTime + 1.4);
  gain.gain.setValueAtTime(0.0001, ctx.currentTime);
  gain.gain.exponentialRampToValueAtTime(0.15, ctx.currentTime + 0.2);
  gain.gain.exponentialRampToValueAtTime(0.0001, ctx.currentTime + 1.4);
  osc.connect(gain).connect(ctx.destination);
  osc.start();
  osc.stop(ctx.currentTime + 1.5);
}

onMounted(() => {
  playIntroSound();
  setTimeout(() => {
    visible.value = false;
    setTimeout(() => emit("done"), 400); // matches the fade transition below
  }, props.durationMs);
});
</script>

<style scoped>
.loading-screen {
  position: fixed;
  inset: 0;
  z-index: 200;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 18px;
  background: var(--bg);
}

.loading-logo {
  width: 72px;
  height: 72px;
  animation: pulse-zoom 1.6s ease-in-out infinite;
}

@keyframes pulse-zoom {
  0%,
  100% {
    transform: scale(1);
    filter: drop-shadow(0 0 0 rgba(108, 92, 231, 0));
  }
  50% {
    transform: scale(1.12);
    filter: drop-shadow(0 0 22px rgba(108, 92, 231, 0.55));
  }
}

.loading-wordmark {
  display: flex;
  align-items: baseline;
  gap: 8px;
  font-family: var(--font-display);
}
.pulse-text {
  font-size: 22px;
  font-weight: 700;
  letter-spacing: 0.12em;
  color: var(--text);
}
.studio-text {
  font-size: 12px;
  font-weight: 500;
  letter-spacing: 0.3em;
  color: var(--text-faint);
}

.loading-bar {
  width: 140px;
  height: 3px;
  border-radius: 999px;
  background: var(--surface-inset);
  overflow: hidden;
}
.loading-bar-fill {
  height: 100%;
  width: 40%;
  border-radius: 999px;
  background: linear-gradient(90deg, var(--primary), var(--secondary));
  animation: loading-sweep 1.2s ease-in-out infinite;
}
@keyframes loading-sweep {
  0% {
    transform: translateX(-100%);
  }
  100% {
    transform: translateX(350%);
  }
}

.loading-fade-enter-active {
  transition: opacity 0.2s ease;
}
.loading-fade-leave-active {
  transition: opacity 0.4s ease;
}
.loading-fade-enter-from,
.loading-fade-leave-to {
  opacity: 0;
}

@media (prefers-reduced-motion: reduce) {
  .loading-logo,
  .loading-bar-fill {
    animation: none;
  }
}
</style>
