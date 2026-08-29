<template>
  <div class="users-view">
    <div class="header">
      <router-link to="/settings" class="back-link">← Settings</router-link>
      <h1>Users</h1>
      <p class="subtitle">Up to {{ maxUsers }} users. Invite-only.</p>
    </div>

    <div v-if="!isAdmin" class="hint hint--error">Admin access required.</div>

    <template v-else>
      <p v-if="error" class="hint hint--error">{{ error }}</p>

      <section class="card">
        <h3>Invite someone</h3>
        <form class="invite-form" @submit.prevent="sendInvite">
          <input v-model="inviteEmail" type="email" placeholder="email@example.com" required />
          <select v-model="inviteRole">
            <option value="editor">Editor</option>
            <option value="admin">Admin</option>
          </select>
          <button class="btn btn--primary" type="submit" :disabled="inviting">
            {{ inviting ? "Sending…" : "Invite" }}
          </button>
        </form>
        <div v-if="lastInviteLink" class="dev-invite">
          Dev mode — no email was sent. Share this link directly:
          <code>{{ lastInviteLink }}</code>
        </div>
      </section>

      <section class="card">
        <h3>Users ({{ users.length }}/{{ maxUsers }})</h3>
        <div v-for="u in users" :key="u.id" class="user-row">
          <div>
            <strong>{{ u.name || u.email }}</strong>
            <span class="hint">{{ u.email }}</span>
          </div>
          <span class="role-badge">{{ u.role }}</span>
          <span v-if="!u.is_active" class="inactive-badge">deactivated</span>
          <div class="user-actions">
            <button class="btn-link" @click="viewActivity(u)">Activity</button>
            <button
              v-if="u.is_active"
              class="btn-link btn-link--danger"
              @click="deactivate(u)"
            >
              Deactivate
            </button>
            <button v-else class="btn-link" @click="reactivate(u)">Reactivate</button>
          </div>
        </div>
      </section>

      <section class="card" v-if="pendingInvites.length">
        <h3>Pending invites</h3>
        <div v-for="inv in pendingInvites" :key="inv.id" class="invite-row">
          <span>{{ inv.email }}</span>
          <span class="hint">{{ inv.role }}</span>
          <button class="btn-link btn-link--danger" @click="revoke(inv.id)">Revoke</button>
        </div>
      </section>

      <div v-if="activityUser" class="modal-backdrop" @click.self="activityUser = null">
        <div class="modal">
          <h3>Activity — {{ activityUser.name || activityUser.email }}</h3>
          <div v-if="activityLog.length === 0" class="hint">No recorded activity yet.</div>
          <div v-for="a in activityLog" :key="a.id" class="activity-row">
            <span class="mono">{{ new Date(a.created_at).toLocaleString() }}</span>
            <span>{{ a.action }}</span>
            <span class="hint">{{ a.detail }}</span>
          </div>
          <p class="hint">
            Only actions through authenticated endpoints (login, invites) are
            recorded — most of PULSE doesn't require login yet.
          </p>
          <button class="btn btn--ghost" @click="activityUser = null">Close</button>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from "vue";
import api from "../api/client";
import { useAuth } from "../composables/useAuth";
import { useToast } from "../composables/useToast";

const toast = useToast();

const { currentUser } = useAuth();
const isAdmin = computed(() => currentUser.value?.role === "admin");
const maxUsers = 8;

const users = ref([]);
const invites = ref([]);
const pendingInvites = computed(() => invites.value.filter((i) => i.status === "pending"));
const error = ref("");

const inviteEmail = ref("");
const inviteRole = ref("editor");
const inviting = ref(false);
const lastInviteLink = ref("");

const activityUser = ref(null);
const activityLog = ref([]);

async function loadUsers() {
  try {
    users.value = await api.listUsers();
  } catch (err) {
    error.value = err?.response?.data?.detail || "Failed to load users.";
  }
}

async function loadInvites() {
  try {
    invites.value = await api.listInvites();
  } catch (err) {
    // non-fatal
  }
}

async function sendInvite() {
  inviting.value = true;
  error.value = "";
  lastInviteLink.value = "";
  try {
    const invite = await api.createInvite(inviteEmail.value, inviteRole.value);
    if (invite.magic_link_url) lastInviteLink.value = invite.magic_link_url;
    inviteEmail.value = "";
    await loadInvites();
    toast.success("Invite sent ✅");
  } catch (err) {
    error.value = err?.response?.data?.detail || "Failed to send invite.";
  } finally {
    inviting.value = false;
  }
}

async function deactivate(user) {
  try {
    await api.updateUser(user.id, { is_active: false });
    await loadUsers();
  } catch (err) {
    error.value = err?.response?.data?.detail || "Failed to update user.";
  }
}

async function reactivate(user) {
  try {
    await api.updateUser(user.id, { is_active: true });
    await loadUsers();
  } catch (err) {
    error.value = err?.response?.data?.detail || "Failed to update user.";
  }
}

async function revoke(inviteId) {
  try {
    await api.revokeInvite(inviteId);
    await loadInvites();
  } catch (err) {
    error.value = "Failed to revoke invite.";
  }
}

async function viewActivity(user) {
  activityUser.value = user;
  try {
    const data = await api.getUserActivity(user.id);
    activityLog.value = data.activity;
  } catch (err) {
    activityLog.value = [];
  }
}

onMounted(() => {
  if (isAdmin.value) {
    loadUsers();
    loadInvites();
  }
});
</script>

<style scoped>
.users-view {
  max-width: 640px;
  width: 100%;
  margin: 0 auto;
  padding: 32px 24px 64px;
}
.header {
  margin-bottom: 24px;
}
.back-link {
  font-size: 12px;
  color: var(--text-faint);
  text-decoration: none;
}
.header h1 {
  font-size: 22px;
  margin: 8px 0 4px;
}
.subtitle {
  font-size: 12.5px;
  color: var(--text-faint);
}

.hint {
  font-size: 11.5px;
  color: var(--text-faint);
}
.hint--error {
  color: var(--weak);
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
  margin-bottom: 14px;
}

.invite-form {
  display: flex;
  gap: 8px;
}
.invite-form input {
  flex: 1;
  background: var(--surface-inset);
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  color: var(--text);
  padding: 9px 11px;
  font-size: 13px;
}
.invite-form select {
  background: var(--surface-inset);
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  color: var(--text);
  padding: 9px 11px;
  font-size: 13px;
}
.dev-invite {
  margin-top: 10px;
  font-size: 11.5px;
  color: var(--bookend);
  word-break: break-all;
}
.dev-invite code {
  color: var(--text);
}

.user-row, .invite-row {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 0;
  border-bottom: 1px solid var(--border);
  font-size: 13px;
}
.user-row:last-child, .invite-row:last-child {
  border-bottom: none;
}
.user-row > div:first-child {
  flex: 1;
  display: flex;
  flex-direction: column;
}
.role-badge {
  font-size: 10px;
  padding: 2px 8px;
  border-radius: 999px;
  border: 1px solid var(--border-bright);
  color: var(--text-dim);
  text-transform: capitalize;
}
.inactive-badge {
  font-size: 10px;
  color: var(--weak);
}
.user-actions {
  display: flex;
  gap: 10px;
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
}
.btn--primary {
  background: var(--primary);
  border-color: var(--primary);
  color: white;
}
.btn-link {
  background: transparent;
  border: none;
  color: var(--primary);
  font-size: 11.5px;
  font-weight: 600;
}
.btn-link--danger {
  color: var(--weak);
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
  max-width: 420px;
  max-height: 70vh;
  overflow-y: auto;
  background: var(--surface-raised);
  border: 1px solid var(--border-bright);
  border-radius: var(--radius-lg);
  padding: 22px;
}
.modal h3 {
  font-size: 14px;
  margin-bottom: 12px;
}
.activity-row {
  display: flex;
  gap: 10px;
  font-size: 12px;
  color: var(--text-dim);
  padding: 6px 0;
  border-bottom: 1px solid var(--border);
}
</style>
