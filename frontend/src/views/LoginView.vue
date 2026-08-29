<template>
  <div class="login-view">
    <div class="login-card">
      <h1>PULSE</h1>

      <template v-if="mode === 'accept-invite'">
        <p class="subtitle">Set up your account</p>
        <form @submit.prevent="doAcceptInvite">
          <label class="field">
            <span>Name</span>
            <input v-model="name" type="text" />
          </label>
          <label class="field">
            <span>Password (optional — you can also use email sign-in links)</span>
            <input v-model="password" type="password" minlength="8" />
          </label>
          <button class="btn btn--primary" type="submit" :disabled="loading">
            {{ loading ? "Creating account…" : "Create account" }}
          </button>
        </form>
      </template>

      <template v-else-if="mode === 'magic-verify'">
        <p class="subtitle">Signing you in…</p>
      </template>

      <template v-else>
        <div class="tabs">
          <button class="tab" :class="{ 'tab--active': loginMode === 'password' }" @click="loginMode = 'password'">
            Password
          </button>
          <button class="tab" :class="{ 'tab--active': loginMode === 'magic' }" @click="loginMode = 'magic'">
            Email link
          </button>
        </div>

        <form v-if="loginMode === 'password'" @submit.prevent="doLogin">
          <label class="field">
            <span>Email</span>
            <input v-model="email" type="email" required />
          </label>
          <label class="field">
            <span>Password</span>
            <input v-model="password" type="password" required />
          </label>
          <button class="btn btn--primary" type="submit" :disabled="loading">
            {{ loading ? "Signing in…" : "Sign in" }}
          </button>
        </form>

        <form v-else @submit.prevent="doRequestMagicLink">
          <label class="field">
            <span>Email</span>
            <input v-model="email" type="email" required />
          </label>
          <button class="btn btn--primary" type="submit" :disabled="loading">
            {{ loading ? "Sending…" : "Send sign-in link" }}
          </button>
          <p v-if="magicLinkSent" class="hint hint--ok">
            If that email is registered, a link has been sent.
            <router-link v-if="devLink" :to="devLink" class="dev-link">(dev: open link)</router-link>
          </p>
        </form>
      </template>

      <p v-if="error" class="hint hint--error">{{ error }}</p>
      <p class="footnote">
        Invite-only — an admin needs to add you before you can sign in.
      </p>
    </div>
  </div>
</template>

<script setup>
import { onMounted, ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import api from "../api/client";
import { useAuth } from "../composables/useAuth";

const route = useRoute();
const router = useRouter();
const { setSession } = useAuth();

const mode = ref("login"); // "login" | "accept-invite" | "magic-verify"
const loginMode = ref("password");

const email = ref("");
const password = ref("");
const name = ref("");
const loading = ref(false);
const error = ref("");
const magicLinkSent = ref(false);
const devLink = ref("");

async function doLogin() {
  loading.value = true;
  error.value = "";
  try {
    const data = await api.login(email.value, password.value);
    setSession(data.access_token, data.user);
    router.push("/");
  } catch (err) {
    error.value = err?.response?.data?.detail || "Login failed.";
  } finally {
    loading.value = false;
  }
}

async function doRequestMagicLink() {
  loading.value = true;
  error.value = "";
  magicLinkSent.value = false;
  try {
    const data = await api.requestMagicLink(email.value);
    magicLinkSent.value = true;
    if (data.dev_link) devLink.value = data.dev_link;
  } catch (err) {
    error.value = err?.response?.data?.detail || "Failed to send link.";
  } finally {
    loading.value = false;
  }
}

async function doAcceptInvite() {
  loading.value = true;
  error.value = "";
  try {
    const data = await api.acceptInvite({
      token: route.query.token,
      name: name.value || undefined,
      password: password.value || undefined,
    });
    setSession(data.access_token, data.user);
    router.push("/");
  } catch (err) {
    error.value = err?.response?.data?.detail || "Failed to create account.";
  } finally {
    loading.value = false;
  }
}

async function verifyMagicLinkToken(token) {
  loading.value = true;
  error.value = "";
  try {
    const data = await api.verifyMagicLink(token);
    setSession(data.access_token, data.user);
    router.push("/");
  } catch (err) {
    error.value = err?.response?.data?.detail || "This link is invalid or expired.";
    mode.value = "login";
  } finally {
    loading.value = false;
  }
}

onMounted(() => {
  if (route.path === "/accept-invite" && route.query.token) {
    mode.value = "accept-invite";
  } else if (route.path === "/magic-link" && route.query.token) {
    mode.value = "magic-verify";
    verifyMagicLinkToken(route.query.token);
  }
});
</script>

<style scoped>
.login-view {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
}
.login-card {
  width: 100%;
  max-width: 380px;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  padding: 28px;
}
.login-card h1 {
  font-family: var(--font-display);
  font-size: 20px;
  letter-spacing: 0.06em;
  margin-bottom: 4px;
}
.subtitle {
  font-size: 13px;
  color: var(--text-dim);
  margin-bottom: 18px;
}

.tabs {
  display: flex;
  gap: 4px;
  margin-bottom: 16px;
}
.tab {
  flex: 1;
  background: var(--surface-inset);
  border: 1px solid var(--border);
  color: var(--text-faint);
  font-size: 12px;
  padding: 8px;
  border-radius: var(--radius-sm);
}
.tab--active {
  background: var(--primary-dim);
  border-color: var(--primary);
  color: white;
}

.field {
  display: flex;
  flex-direction: column;
  gap: 6px;
  font-size: 12px;
  color: var(--text-dim);
  margin-bottom: 14px;
}
.field input {
  background: var(--surface-inset);
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  color: var(--text);
  padding: 10px 12px;
  font-size: 14px;
}
.field input:focus {
  outline: none;
  border-color: var(--primary);
}

.btn {
  width: 100%;
  font-family: var(--font-body);
  font-weight: 600;
  font-size: 13px;
  border-radius: var(--radius-md);
  padding: 10px;
  border: 1px solid transparent;
}
.btn--primary {
  background: var(--primary);
  color: white;
}
.btn:disabled {
  opacity: 0.5;
}

.hint {
  font-size: 12px;
  margin-top: 12px;
}
.hint--ok {
  color: var(--secondary);
}
.hint--error {
  color: var(--weak);
}
.dev-link {
  color: var(--primary);
}

.footnote {
  font-size: 11px;
  color: var(--text-faint);
  margin-top: 18px;
  text-align: center;
}
</style>
