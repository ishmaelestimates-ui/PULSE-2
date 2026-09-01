<template>
  <div class="coloring">
    <div v-if="!hasVideo" class="empty">
      Color grading needs an uploaded video file. This episode has no
      video media yet (audio-only episodes have nothing to grade).
    </div>

    <template v-else>
      <section class="block">
        <h4>LUT</h4>
        <div class="lut-row">
          <select v-model="selectedLut" class="lut-select">
            <option value="" disabled>Choose a LUT…</option>
            <option v-for="lut in luts" :key="lut.name" :value="lut.name">
              {{ lut.title }}{{ lut.builtin ? "" : " (custom)" }}
            </option>
          </select>
          <button
            class="btn btn--primary"
            :disabled="!selectedLut || applyingLut"
            @click="applyLut"
          >
            {{ applyingLut ? "Applying…" : "Apply LUT" }}
          </button>
        </div>
        <p class="hint">
          Generates a fast preview frame by default. Full-video render is
          available but runs synchronously and can be slow — ask if you
          need it wired into the UI.
        </p>
      </section>

      <section class="block">
        <h4>AI style transfer</h4>
        <p class="hint hint--pre">
          Gemini compares a reference image to a frame from your episode
          and suggests grading parameters (brightness, contrast,
          saturation, temperature, tint), which are then applied with
          FFmpeg. This is AI-suggested settings, not literal neural style
          transfer.
        </p>
        <button class="btn btn--ghost" @click="showStyleModal = true">
          + Upload reference image
        </button>
      </section>

      <section v-if="preview" class="block">
        <h4>Preview</h4>
        <img :src="preview.url" class="preview-img" alt="Color grade preview" />
        <p v-if="preview.rationale" class="rationale">"{{ preview.rationale }}"</p>
      </section>

      <section class="block">
        <div class="block-header">
          <h4>Delivery compliance</h4>
          <button class="btn-link" :disabled="loadingSpecs" @click="loadSpecs">
            {{ loadingSpecs ? "Checking…" : "Refresh" }}
          </button>
        </div>
        <p class="hint">{{ specsNote }}</p>

        <div v-if="specsError" class="hint hint--error">{{ specsError }}</div>

        <div v-for="platform in specs" :key="platform.platform" class="platform">
          <h5>{{ platform.platform }}</h5>
          <div class="check-row" v-for="check in platform.checks" :key="check.label">
            <span class="check-dot" :class="`check-dot--${check.status}`"></span>
            <span class="check-label">{{ check.label }}</span>
            <span class="check-target mono">{{ check.target }}</span>
            <span class="check-actual mono">{{ check.actual || "—" }}</span>
          </div>
        </div>
      </section>
    </template>

    <div v-if="showStyleModal" class="modal-backdrop" @click.self="showStyleModal = false">
      <div class="modal">
        <h3>AI style transfer</h3>
        <p class="hint">Upload an image with the look you want to match.</p>
        <input type="file" accept="image/*" @change="onRefFileChange" />
        <div class="modal-actions">
          <button class="btn btn--ghost" @click="showStyleModal = false">Cancel</button>
          <button
            class="btn btn--primary"
            :disabled="!refFile || applyingStyle"
            @click="runStyleTransfer"
          >
            {{ applyingStyle ? "Analyzing…" : "Suggest & apply" }}
          </button>
        </div>
        <p v-if="styleError" class="hint hint--error">{{ styleError }}</p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { onMounted, ref } from "vue";
import api from "../api/client";
import { useToast } from "../composables/useToast";

const toast = useToast();

const props = defineProps({
  episodeId: { type: Number, required: true },
  hasVideo: { type: Boolean, default: false },
});

const luts = ref([]);
const selectedLut = ref("");
const applyingLut = ref(false);

const showStyleModal = ref(false);
const refFile = ref(null);
const applyingStyle = ref(false);
const styleError = ref("");

const preview = ref(null); // { url, rationale }

const specs = ref([]);
const specsNote = ref("");
const loadingSpecs = ref(false);
const specsError = ref("");

async function loadLuts() {
  try {
    luts.value = await api.listLuts();
  } catch (err) {
    // non-fatal — LUT dropdown just stays empty
  }
}

async function applyLut() {
  if (!selectedLut.value) return;
  applyingLut.value = true;
  try {
    const grade = await api.applyLut(props.episodeId, selectedLut.value);
    preview.value = { url: grade.preview_url, rationale: null };
    toast.success("LUT applied — preview ready ✅");
  } catch (err) {
    specsError.value = err?.response?.data?.detail || "Failed to apply LUT.";
  } finally {
    applyingLut.value = false;
  }
}

function onRefFileChange(evt) {
  refFile.value = evt.target.files?.[0] || null;
}

async function runStyleTransfer() {
  if (!refFile.value) return;
  applyingStyle.value = true;
  styleError.value = "";
  try {
    const grade = await api.styleTransfer(props.episodeId, refFile.value);
    preview.value = {
      url: grade.preview_url,
      rationale: grade.style_transfer_params?.rationale || null,
    };
    showStyleModal.value = false;
  } catch (err) {
    styleError.value = err?.response?.data?.detail || "Style transfer failed.";
  } finally {
    applyingStyle.value = false;
  }
}

async function loadSpecs() {
  loadingSpecs.value = true;
  specsError.value = "";
  try {
    const data = await api.colorSpecs(props.episodeId);
    specs.value = data.platforms;
    specsNote.value = data.note;
  } catch (err) {
    specsError.value = err?.response?.data?.detail || "Failed to load compliance checks.";
  } finally {
    loadingSpecs.value = false;
  }
}

onMounted(() => {
  loadLuts();
  if (props.hasVideo) loadSpecs();
});
</script>

<style scoped>
.coloring {
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.empty {
  color: var(--text-dim);
  font-size: 13px;
  padding: 24px 4px;
}

.block h4 {
  font-size: 12px;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  color: var(--text-faint);
  margin-bottom: 10px;
}
.block-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 4px;
}
.block-header h4 {
  margin-bottom: 0;
}

.lut-row {
  display: flex;
  gap: 8px;
}
.lut-select {
  flex: 1;
  background: var(--surface-inset);
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  color: var(--text);
  padding: 8px 10px;
  font-size: 13px;
}

.hint {
  font-size: 11.5px;
  color: var(--text-faint);
  margin-top: 8px;
  line-height: 1.5;
}
.hint--pre {
  margin-top: 0;
  margin-bottom: 10px;
}
.hint--error {
  color: var(--weak);
}

.preview-img {
  width: 100%;
  border-radius: var(--radius-md);
  border: 1px solid var(--border);
}
.rationale {
  font-size: 12px;
  color: var(--text-dim);
  font-style: italic;
  margin-top: 8px;
}

.platform {
  margin-top: 14px;
}
.platform h5 {
  font-size: 12.5px;
  font-weight: 600;
  margin-bottom: 6px;
}
.check-row {
  display: grid;
  grid-template-columns: 12px 1fr auto auto;
  align-items: center;
  gap: 8px;
  padding: 5px 0;
  font-size: 11.5px;
  color: var(--text-dim);
}
.check-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
}
.check-dot--pass {
  background: var(--secondary);
}
.check-dot--fail {
  background: var(--weak);
}
.check-dot--unknown {
  background: var(--text-faint);
}
.check-target {
  color: var(--text-faint);
}
.check-actual {
  color: var(--text);
}

.btn {
  font-family: var(--font-body);
  font-weight: 600;
  font-size: 12.5px;
  border-radius: var(--radius-md);
  padding: 8px 14px;
  border: 1px solid var(--border-bright);
  background: var(--surface-raised);
  color: var(--text);
}
.btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
.btn--primary {
  background: var(--primary);
  border-color: var(--primary);
  color: white;
}
.btn--ghost:hover {
  border-color: var(--primary);
  color: var(--primary);
}
.btn-link {
  background: transparent;
  border: none;
  color: var(--primary);
  font-size: 11.5px;
  font-weight: 600;
}
.btn-link:disabled {
  opacity: 0.5;
}

.modal-backdrop {
  position: fixed;
  inset: 0;
  background: rgba(5, 5, 10, 0.7);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 50;
}
.modal {
  width: 100%;
  max-width: 380px;
  background: var(--surface-raised);
  border: 1px solid var(--border-bright);
  border-radius: var(--radius-lg);
  padding: 22px;
}
.modal h3 {
  font-size: 15px;
  margin-bottom: 8px;
}
.modal input[type="file"] {
  margin: 12px 0;
  font-size: 12px;
  color: var(--text-dim);
}
.modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  margin-top: 12px;
}
</style>
