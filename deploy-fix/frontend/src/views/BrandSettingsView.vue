<template>
  <div class="settings-view">
    <div class="settings-header">
      <router-link to="/" class="back-link">← Episodes</router-link>
      <router-link to="/settings/users" class="back-link users-link">Users →</router-link>
      <h1>Brand settings</h1>
      <p class="subtitle">
        Applies project-wide — one shared configuration, not per-account
        (see the Users page for account management).
      </p>
    </div>

    <div v-if="loading" class="state-msg">Loading…</div>

    <template v-else>
      <div v-if="error" class="banner banner--error">{{ error }}</div>

      <section class="card">
        <h3>Colors</h3>
        <div class="color-row">
          <label class="color-field">
            <span>Primary</span>
            <div class="swatch-input">
              <input type="color" v-model="form.primary_color" />
              <input
                type="text"
                v-model="form.primary_color"
                class="hex-input mono"
                maxlength="7"
              />
            </div>
          </label>
          <label class="color-field">
            <span>Secondary</span>
            <div class="swatch-input">
              <input type="color" v-model="form.secondary_color" />
              <input
                type="text"
                v-model="form.secondary_color"
                class="hex-input mono"
                maxlength="7"
              />
            </div>
          </label>
          <label class="color-field">
            <span>Tertiary <em>(optional)</em></span>
            <div class="swatch-input">
              <input type="color" v-model="tertiaryColorModel" />
              <input
                type="text"
                v-model="form.tertiary_color"
                class="hex-input mono"
                placeholder="#000000"
                maxlength="7"
              />
            </div>
          </label>
        </div>
      </section>

      <section class="card">
        <h3>Typography</h3>
        <label class="field">
          <span>Font</span>
          <select v-model="form.font">
            <option v-for="f in fontOptions" :key="f" :value="f">{{ f }}</option>
          </select>
        </label>
      </section>

      <div class="save-row">
        <span class="save-status mono">
          <span v-if="autoSave.status.value === 'saving'">Saving…</span>
          <span v-else-if="autoSave.status.value === 'saved'" class="save-status--ok">✓ Saved</span>
          <span v-else-if="autoSave.status.value === 'error'" class="save-status--error">Failed to save</span>
          <span v-else>Auto-saves as you edit</span>
        </span>
      </div>

      <section class="card">
        <h3>Logo</h3>
        <div class="asset-row">
          <img v-if="settings.logo_url" :src="settings.logo_url" class="logo-preview" alt="Logo" />
          <div v-else class="asset-placeholder">No logo uploaded</div>
          <label class="btn btn--ghost upload-btn">
            {{ uploadingLogo ? "Uploading…" : "Upload logo" }}
            <input type="file" accept="image/*" class="hidden-input" @change="onLogoChange" />
          </label>
        </div>
      </section>

      <section class="card">
        <h3>Intro / outro music</h3>
        <div class="asset-row">
          <span class="asset-label">Intro</span>
          <audio v-if="settings.intro_music_url" :src="settings.intro_music_url" controls></audio>
          <span v-else class="asset-placeholder">None set</span>
          <label class="btn btn--ghost upload-btn">
            {{ uploadingIntro ? "Uploading…" : "Upload" }}
            <input type="file" accept="audio/*" class="hidden-input" @change="onIntroChange" />
          </label>
        </div>
        <div class="asset-row">
          <span class="asset-label">Outro</span>
          <audio v-if="settings.outro_music_url" :src="settings.outro_music_url" controls></audio>
          <span v-else class="asset-placeholder">None set</span>
          <label class="btn btn--ghost upload-btn">
            {{ uploadingOutro ? "Uploading…" : "Upload" }}
            <input type="file" accept="audio/*" class="hidden-input" @change="onOutroChange" />
          </label>
        </div>
      </section>
    </template>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref, watch } from "vue";
import api from "../api/client";
import { useAutoSave } from "../composables/useAutoSave";

const settings = ref({});
const loading = ref(true);
const error = ref("");

const uploadingLogo = ref(false);
const uploadingIntro = ref(false);
const uploadingOutro = ref(false);

const fontOptions = ["Inter", "Space Grotesk", "Montserrat", "Poppins", "IBM Plex Sans", "Roboto"];

const form = reactive({
  primary_color: "#6C5CE7",
  secondary_color: "#00E676",
  tertiary_color: "",
  font: "Inter",
});

// Debounced auto-save — see composables/useAutoSave.js. `suppressNextSave`
// avoids firing a save the instant we populate the form from the initial
// GET (that would just re-save what we just loaded).
let suppressNextSave = true;
const autoSave = useAutoSave(async () => {
  settings.value = await api.updateBrandSettings({
    primary_color: form.primary_color,
    secondary_color: form.secondary_color,
    tertiary_color: form.tertiary_color || null,
    font: form.font,
  });
});
watch(
  () => ({ ...form }),
  () => {
    if (suppressNextSave) {
      suppressNextSave = false;
      return;
    }
    autoSave.trigger();
  },
  { deep: true }
);

// Native <input type="color"> requires a valid #rrggbb value at all
// times, but tertiary is optional/nullable in the form — fall back to a
// neutral swatch when empty rather than binding directly.
const tertiaryColorModel = computed({
  get: () => form.tertiary_color || "#000000",
  set: (v) => (form.tertiary_color = v),
});

async function load() {
  loading.value = true;
  error.value = "";
  try {
    settings.value = await api.getBrandSettings();
    suppressNextSave = true;
    form.primary_color = settings.value.primary_color;
    form.secondary_color = settings.value.secondary_color;
    form.tertiary_color = settings.value.tertiary_color || "";
    form.font = settings.value.font;
  } catch (err) {
    error.value = err?.response?.data?.detail || "Failed to load brand settings.";
  } finally {
    loading.value = false;
  }
}

async function onLogoChange(evt) {
  const file = evt.target.files?.[0];
  if (!file) return;
  uploadingLogo.value = true;
  try {
    settings.value = await api.uploadBrandLogo(file);
  } catch (err) {
    error.value = err?.response?.data?.detail || "Logo upload failed.";
  } finally {
    uploadingLogo.value = false;
  }
}

async function onIntroChange(evt) {
  const file = evt.target.files?.[0];
  if (!file) return;
  uploadingIntro.value = true;
  try {
    settings.value = await api.uploadBrandIntroMusic(file);
  } catch (err) {
    error.value = err?.response?.data?.detail || "Upload failed.";
  } finally {
    uploadingIntro.value = false;
  }
}

async function onOutroChange(evt) {
  const file = evt.target.files?.[0];
  if (!file) return;
  uploadingOutro.value = true;
  try {
    settings.value = await api.uploadBrandOutroMusic(file);
  } catch (err) {
    error.value = err?.response?.data?.detail || "Upload failed.";
  } finally {
    uploadingOutro.value = false;
  }
}

onMounted(load);
</script>

<style scoped>
.settings-view {
  max-width: 640px;
  width: 100%;
  margin: 0 auto;
  padding: 32px 24px 64px;
}

.settings-header {
  margin-bottom: 24px;
}
.back-link {
  font-size: 12px;
  color: var(--text-faint);
  text-decoration: none;
}
.users-link {
  float: right;
}
.settings-header h1 {
  font-size: 22px;
  margin: 8px 0 6px;
}
.subtitle {
  font-size: 12.5px;
  color: var(--text-faint);
}

.state-msg {
  padding: 40px 0;
  color: var(--text-dim);
}

.banner {
  padding: 10px 14px;
  border-radius: var(--radius-md);
  font-size: 12.5px;
  margin-bottom: 16px;
}
.banner--error {
  background: color-mix(in srgb, var(--weak) 14%, var(--surface));
  border: 1px solid color-mix(in srgb, var(--weak) 40%, var(--border));
  color: var(--weak);
}
.banner--ok {
  background: color-mix(in srgb, var(--secondary) 14%, var(--surface));
  border: 1px solid color-mix(in srgb, var(--secondary) 40%, var(--border));
  color: var(--secondary);
}

.card {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  padding: 20px;
  margin-bottom: 16px;
}
.card h3 {
  font-size: 13px;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  color: var(--text-faint);
  margin-bottom: 16px;
}

.color-row {
  display: flex;
  gap: 20px;
  flex-wrap: wrap;
}
.color-field {
  display: flex;
  flex-direction: column;
  gap: 6px;
  font-size: 12px;
  color: var(--text-dim);
}
.color-field em {
  color: var(--text-faint);
  font-style: normal;
  font-size: 10.5px;
}
.swatch-input {
  display: flex;
  align-items: center;
  gap: 8px;
}
.swatch-input input[type="color"] {
  width: 36px;
  height: 36px;
  border-radius: 8px;
  border: 1px solid var(--border-bright);
  background: transparent;
  padding: 0;
  cursor: pointer;
}
.hex-input {
  width: 90px;
  background: var(--surface-inset);
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  color: var(--text);
  padding: 8px 10px;
  font-size: 12.5px;
}

.field {
  display: flex;
  flex-direction: column;
  gap: 6px;
  font-size: 12px;
  color: var(--text-dim);
}
.field select {
  background: var(--surface-inset);
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  color: var(--text);
  padding: 9px 10px;
  font-size: 13px;
}

.save-row {
  margin-bottom: 16px;
}
.save-status {
  font-size: 11px;
  color: var(--text-faint);
}
.save-status--ok {
  color: var(--secondary);
}
.save-status--error {
  color: var(--weak);
}

.asset-row {
  display: flex;
  align-items: center;
  gap: 14px;
  margin-bottom: 10px;
}
.asset-row:last-child {
  margin-bottom: 0;
}
.asset-label {
  width: 44px;
  font-size: 12px;
  color: var(--text-dim);
  flex-shrink: 0;
}
.logo-preview {
  width: 56px;
  height: 56px;
  object-fit: contain;
  background: var(--surface-inset);
  border-radius: var(--radius-md);
  border: 1px solid var(--border);
}
.asset-placeholder {
  font-size: 12px;
  color: var(--text-faint);
  flex: 1;
}
audio {
  height: 32px;
  flex: 1;
}

.btn {
  font-family: var(--font-body);
  font-weight: 600;
  font-size: 12.5px;
  border-radius: var(--radius-md);
  padding: 9px 16px;
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
.upload-btn {
  cursor: pointer;
  flex-shrink: 0;
}
.hidden-input {
  display: none;
}
</style>
