<template>
  <div
    class="dropzone"
    :class="{ 'dropzone--active': dragging, 'dropzone--busy': uploading }"
    @dragover.prevent="dragging = true"
    @dragleave.prevent="dragging = false"
    @drop.prevent="onDrop"
    @click="!uploading && fileInput.click()"
  >
    <input
      ref="fileInput"
      type="file"
      class="hidden-input"
      :accept="acceptAttr"
      @change="onFileSelected"
    />

    <template v-if="uploading">
      <div class="progress-ring mono">{{ progress }}%</div>
      <p>Processing with FFmpeg…</p>
    </template>
    <template v-else>
      <div class="dropzone-icon">⇪</div>
      <p class="dropzone-title">Drop media here, or click to browse</p>

      <div class="format-groups" @click.stop>
        <div class="format-group">
          <span class="format-group-label">Video</span>
          <span v-for="f in videoFormats" :key="f.ext" class="format-badge" :class="{ 'format-badge--disabled': !f.supported }" :title="f.supported ? '' : 'Not yet supported'">
            {{ f.ext }}
          </span>
        </div>
        <div class="format-group">
          <span class="format-group-label">Audio</span>
          <span v-for="f in audioFormats" :key="f.ext" class="format-badge" :class="{ 'format-badge--disabled': !f.supported }" :title="f.supported ? '' : 'Not yet supported'">
            {{ f.ext }}
          </span>
        </div>
      </div>
      <p class="dropzone-hint">Grayed-out formats aren't supported yet — everything else works today.</p>
    </template>

    <p v-if="localError" class="dropzone-error">{{ localError }}</p>
  </div>
</template>

<script setup>
import { ref } from "vue";

const props = defineProps({
  uploading: { type: Boolean, default: false },
  progress: { type: Number, default: 0 },
});

const emit = defineEmits(["file-selected"]);

const dragging = ref(false);
const fileInput = ref(null);
const localError = ref("");

// Reflects what the backend's media_service.py actually accepts (Sprint
// 2). The extras requested in Sprint 9 (FLV/WMV/OGG/WMA, plus direct
// transcript-file upload) aren't implemented server-side, so they're
// shown as visibly disabled rather than badged as if they work.
const videoFormats = [
  { ext: "MP4", supported: true },
  { ext: "MOV", supported: true },
  { ext: "AVI", supported: true },
  { ext: "MKV", supported: true },
  { ext: "WebM", supported: true },
  { ext: "FLV", supported: false },
  { ext: "WMV", supported: false },
];
const audioFormats = [
  { ext: "MP3", supported: true },
  { ext: "WAV", supported: true },
  { ext: "M4A", supported: true },
  { ext: "FLAC", supported: true },
  { ext: "AAC", supported: true },
  { ext: "OGG", supported: false },
  { ext: "WMA", supported: false },
];

const supportedExts = [...videoFormats, ...audioFormats].filter((f) => f.supported).map((f) => f.ext.toLowerCase());
const acceptAttr = supportedExts.map((e) => `.${e}`).join(",");

function validate(file) {
  const ext = file.name.split(".").pop()?.toLowerCase();
  if (!supportedExts.includes(ext)) {
    localError.value = `.${ext} isn't supported yet. Supported: ${supportedExts.join(", ")}.`;
    return false;
  }
  localError.value = "";
  return true;
}

function onDrop(evt) {
  dragging.value = false;
  if (props.uploading) return;
  const file = evt.dataTransfer?.files?.[0];
  if (file && validate(file)) emit("file-selected", file);
}

function onFileSelected(evt) {
  const file = evt.target.files?.[0];
  if (file && validate(file)) emit("file-selected", file);
  evt.target.value = "";
}
</script>

<style scoped>
.dropzone {
  border: 1.5px dashed var(--border-bright);
  border-radius: var(--radius-lg);
  padding: 32px 20px;
  text-align: center;
  cursor: pointer;
  transition: border-color 0.15s var(--ease), background-color 0.15s var(--ease);
  background: var(--surface-inset);
}
.dropzone:hover {
  border-color: var(--primary);
}
.dropzone--active {
  border-color: var(--primary);
  background: color-mix(in srgb, var(--primary) 8%, var(--surface-inset));
}
.dropzone--busy {
  cursor: default;
}

.hidden-input {
  display: none;
}

.dropzone-icon {
  font-size: 22px;
  color: var(--primary);
  margin-bottom: 8px;
}
.dropzone-title {
  font-size: 13px;
  color: var(--text);
  margin-bottom: 12px;
}
.dropzone-hint {
  font-size: 10.5px;
  color: var(--text-faint);
  margin-top: 8px;
}
.dropzone-error {
  font-size: 11px;
  color: var(--weak);
  margin-top: 10px;
}

.format-groups {
  display: flex;
  flex-direction: column;
  gap: 6px;
  align-items: center;
  cursor: default;
}
.format-group {
  display: flex;
  align-items: center;
  gap: 5px;
  flex-wrap: wrap;
  justify-content: center;
}
.format-group-label {
  font-size: 10px;
  color: var(--text-faint);
  text-transform: uppercase;
  letter-spacing: 0.06em;
  width: 38px;
  text-align: right;
  flex-shrink: 0;
}
.format-badge {
  font-family: var(--font-mono);
  font-size: 10px;
  padding: 2px 7px;
  border-radius: 999px;
  border: 1px solid var(--border-bright);
  color: var(--text-dim);
}
.format-badge--disabled {
  color: var(--text-faint);
  border-color: var(--border);
  opacity: 0.5;
  text-decoration: line-through;
}

.progress-ring {
  font-size: 20px;
  font-weight: 600;
  color: var(--primary);
  margin-bottom: 6px;
}
</style>

