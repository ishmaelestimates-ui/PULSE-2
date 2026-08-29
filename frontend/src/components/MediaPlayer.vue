<template>
  <div class="player">
    <div v-if="!mediaFile" class="player-empty">
      <p>No media uploaded yet.</p>
      <p class="text-dim">Upload a file to load the player.</p>
    </div>

    <template v-else>
      <div class="stage">
        <video
          v-if="mediaFile.media_type === 'video'"
          ref="mediaEl"
          :src="mediaFile.url"
          class="stage-video"
          @timeupdate="onTimeUpdate"
          @loadedmetadata="onLoadedMetadata"
          @ended="playing = false"
        />
        <div v-else class="stage-audio">
          <img
            v-if="mediaFile.thumbnail_url"
            :src="mediaFile.thumbnail_url"
            class="stage-audio-art"
            alt=""
          />
          <div v-else class="stage-audio-icon">♪</div>
          <audio
            ref="mediaEl"
            :src="mediaFile.url"
            style="display: none"
            @timeupdate="onTimeUpdate"
            @loadedmetadata="onLoadedMetadata"
            @ended="playing = false"
          />
        </div>
      </div>

      <div class="waveform-wrap">
        <div class="markers-row">
          <button
            v-for="m in markers"
            :key="m.id"
            class="marker-pin"
            :class="[`marker-pin--${m.color}`, { 'marker-pin--rejected': m.rejected }]"
            :style="{ left: m.leftPct + '%' }"
            :title="`${m.label} · ${formatTime(m.start)}`"
            @click.stop="onMarkerClick(m)"
          ></button>
        </div>

        <div class="waveform" ref="waveformEl" @mousedown="startScrub">
          <div class="waveform-bars">
            <span
              v-for="(v, i) in waveform"
              :key="i"
              class="bar"
              :style="{ height: Math.max(v * 100, 4) + '%' }"
              :class="{ 'bar--played': i / waveform.length <= progress }"
            ></span>
          </div>
          <div class="playhead" :style="{ left: progress * 100 + '%' }"></div>
        </div>
      </div>

      <div class="controls">
        <button class="ctrl-btn ctrl-btn--play" @click="togglePlay">
          <span v-if="playing">❚❚</span>
          <span v-else>▶</span>
        </button>

        <span class="time mono">{{ formatTime(currentTime) }}</span>
        <span class="time-sep mono">/</span>
        <span class="time time--dim mono">{{ formatTime(duration) }}</span>

        <div class="spacer"></div>

        <div class="speed-group">
          <button
            v-for="s in speeds"
            :key="s"
            class="speed-btn"
            :class="{ 'speed-btn--active': speed === s }"
            @click="setSpeed(s)"
          >
            {{ s }}×
          </button>
        </div>

        <div class="volume-group">
          <span class="vol-icon">{{ volume === 0 ? "🔇" : "🔊" }}</span>
          <input
            type="range"
            min="0"
            max="1"
            step="0.05"
            v-model.number="volume"
            @input="setVolume"
          />
        </div>

        <button
          v-if="mediaFile.media_type === 'video'"
          class="ctrl-btn"
          @click="toggleFullscreen"
        >
          ⛶
        </button>
      </div>
    </template>
  </div>
</template>

<script setup>
import { computed, nextTick, ref, watch } from "vue";

const props = defineProps({
  mediaFile: { type: Object, default: null },
  reviews: { type: Array, default: () => [] },
  duration: { type: Number, default: 0 },
});

const emit = defineEmits([
  "time-update",
  "duration-change",
  "seek",
  "play",
  "pause",
  "marker-click",
]);

const mediaEl = ref(null);
const waveformEl = ref(null);
const playing = ref(false);
const currentTime = ref(0);
const duration = ref(props.duration || 0);
const volume = ref(1);
const speed = ref(1);
const speeds = [0.5, 0.75, 1, 1.25, 1.5, 1.75, 2];

const waveform = computed(() => {
  const w = props.mediaFile?.media_metadata?.waveform;
  return Array.isArray(w) && w.length ? w : new Array(150).fill(0.05);
});

const progress = computed(() => (duration.value ? currentTime.value / duration.value : 0));

const MARKER_COLOR_BY_TYPE = {
  strong_moment: "strong",
  weak_section: "weak",
  clip_candidate: "clip",
  opening: "open",
  closing: "close",
};

const MARKER_LABEL_BY_TYPE = {
  strong_moment: "Strong moment",
  weak_section: "Weak section",
  clip_candidate: "Clip candidate",
  opening: "Opening candidate",
  closing: "Closing candidate",
};

function spanOf(review) {
  const ref_ = review.decision_reference || {};
  if ("start" in ref_ && "end" in ref_) return [ref_.start, ref_.end];
  const t = ref_.timestamp ?? 0;
  return [t, t];
}

const markers = computed(() => {
  if (!duration.value) return [];
  return props.reviews
    .filter((r) => r.status !== "rejected")
    .map((r) => {
      const [start] = spanOf(r);
      return {
        id: r.id,
        start,
        leftPct: Math.min(100, Math.max(0, (start / duration.value) * 100)),
        color: MARKER_COLOR_BY_TYPE[r.decision_type] || "clip",
        label: MARKER_LABEL_BY_TYPE[r.decision_type] || "Marker",
        rejected: false,
      };
    });
});

function onLoadedMetadata() {
  duration.value = mediaEl.value?.duration || props.duration || 0;
  emit("duration-change", duration.value);
}

function onTimeUpdate() {
  currentTime.value = mediaEl.value?.currentTime || 0;
  emit("time-update", currentTime.value);
}

function togglePlay() {
  if (!mediaEl.value) return;
  if (playing.value) {
    mediaEl.value.pause();
    emit("pause", currentTime.value);
  } else {
    mediaEl.value.play();
    emit("play", currentTime.value);
  }
  playing.value = !playing.value;
}

function setSpeed(s) {
  speed.value = s;
  if (mediaEl.value) mediaEl.value.playbackRate = s;
}

function setVolume() {
  if (mediaEl.value) mediaEl.value.volume = volume.value;
}

function toggleFullscreen() {
  if (mediaEl.value?.requestFullscreen) mediaEl.value.requestFullscreen();
}

function seekTo(t) {
  if (!mediaEl.value) return;
  mediaEl.value.currentTime = t;
  currentTime.value = t;
  emit("seek", t);
}

function onMarkerClick(marker) {
  seekTo(marker.start);
  emit("marker-click", marker);
}

function startScrub(evt) {
  scrubToClientX(evt.clientX);
  const onMove = (e) => scrubToClientX(e.clientX);
  const onUp = () => {
    window.removeEventListener("mousemove", onMove);
    window.removeEventListener("mouseup", onUp);
  };
  window.addEventListener("mousemove", onMove);
  window.addEventListener("mouseup", onUp);
}

function scrubToClientX(clientX) {
  if (!waveformEl.value || !duration.value) return;
  const rect = waveformEl.value.getBoundingClientRect();
  const pct = Math.min(1, Math.max(0, (clientX - rect.left) / rect.width));
  seekTo(pct * duration.value);
}

function formatTime(seconds) {
  if (!seconds && seconds !== 0) return "0:00";
  const total = Math.floor(seconds);
  const h = Math.floor(total / 3600);
  const m = Math.floor((total % 3600) / 60);
  const s = total % 60;
  return h > 0
    ? `${h}:${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`
    : `${m}:${String(s).padStart(2, "0")}`;
}

// Allow parent to command a seek (e.g. clicking a transcript line).
defineExpose({
  seekTo,
});

watch(
  () => props.mediaFile,
  async () => {
    playing.value = false;
    currentTime.value = 0;
    await nextTick();
    if (mediaEl.value) {
      mediaEl.value.volume = volume.value;
      mediaEl.value.playbackRate = speed.value;
    }
  }
);
</script>

<style scoped>
.player {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  overflow: hidden;
}

.player-empty {
  padding: 60px 20px;
  text-align: center;
  color: var(--text-dim);
}
.player-empty .text-dim {
  color: var(--text-faint);
  font-size: 13px;
  margin-top: 4px;
}

.stage {
  background: #000;
  aspect-ratio: 16 / 9;
  display: flex;
  align-items: center;
  justify-content: center;
}
.stage-video {
  width: 100%;
  height: 100%;
}
.stage-audio {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  background: radial-gradient(circle at 50% 30%, #1c1c2e, #08080d 75%);
}
.stage-audio-art {
  width: 40%;
  aspect-ratio: 1;
  object-fit: cover;
  border-radius: var(--radius-md);
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.5);
}
.stage-audio-icon {
  font-size: 48px;
  color: var(--text-faint);
}

.waveform-wrap {
  padding: 14px 18px 6px;
  background: var(--surface-inset);
  border-top: 1px solid var(--border);
  border-bottom: 1px solid var(--border);
}

.markers-row {
  position: relative;
  height: 14px;
  margin-bottom: 2px;
}
.marker-pin {
  position: absolute;
  top: 0;
  width: 8px;
  height: 8px;
  border-radius: 2px 2px 6px 6px;
  transform: translateX(-50%);
  border: none;
  padding: 0;
  cursor: pointer;
}
.marker-pin--strong {
  background: var(--strong);
}
.marker-pin--weak {
  background: var(--weak);
}
.marker-pin--clip {
  background: var(--clip);
}
.marker-pin--open {
  background: var(--primary);
}
.marker-pin--close {
  background: var(--bookend);
}
.marker-pin--rejected {
  opacity: 0.3;
}

.waveform {
  position: relative;
  height: 56px;
  cursor: pointer;
  user-select: none;
}
.waveform-bars {
  height: 100%;
  display: flex;
  align-items: center;
  gap: 1px;
}
.bar {
  flex: 1;
  min-width: 1px;
  background: var(--border-bright);
  border-radius: 1px;
  transition: background-color 0.1s linear;
}
.bar--played {
  background: var(--primary);
}
.playhead {
  position: absolute;
  top: 0;
  bottom: 0;
  width: 2px;
  background: var(--secondary);
  box-shadow: 0 0 8px var(--secondary);
  pointer-events: none;
}

.controls {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 18px;
}

.ctrl-btn {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  border: 1px solid var(--border-bright);
  background: var(--surface-raised);
  color: var(--text);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
}
.ctrl-btn--play {
  background: var(--primary);
  border-color: var(--primary);
  color: white;
}
.ctrl-btn:hover {
  filter: brightness(1.15);
}

.time {
  font-size: 12px;
}
.time--dim {
  color: var(--text-faint);
}
.time-sep {
  color: var(--text-faint);
}

.spacer {
  flex: 1;
}

.speed-group {
  display: flex;
  gap: 2px;
  background: var(--surface-inset);
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  padding: 2px;
}
.speed-btn {
  border: none;
  background: transparent;
  color: var(--text-faint);
  font-family: var(--font-mono);
  font-size: 11px;
  padding: 4px 7px;
  border-radius: 4px;
}
.speed-btn--active {
  background: var(--primary-dim);
  color: white;
}

.volume-group {
  display: flex;
  align-items: center;
  gap: 6px;
}
.vol-icon {
  font-size: 12px;
}
.volume-group input {
  width: 70px;
  accent-color: var(--primary);
}
</style>
