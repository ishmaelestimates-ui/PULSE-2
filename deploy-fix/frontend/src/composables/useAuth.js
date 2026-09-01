import { ref } from "vue";
import api from "../api/client";

// Simple module-level reactive singleton — no Pinia dependency added
// for just this. See frontend/README.md for why the rest of the app
// doesn't use a central store either.
const currentUser = ref(null);
const initialized = ref(false);

async function loadCurrentUser() {
  const token = localStorage.getItem("pulse_token");
  if (!token) {
    currentUser.value = null;
    initialized.value = true;
    return;
  }
  try {
    currentUser.value = await api.getMe();
  } catch (err) {
    localStorage.removeItem("pulse_token");
    currentUser.value = null;
  } finally {
    initialized.value = true;
  }
}

function setSession(token, user) {
  localStorage.setItem("pulse_token", token);
  currentUser.value = user;
}

function clearSession() {
  localStorage.removeItem("pulse_token");
  currentUser.value = null;
}

export function useAuth() {
  if (!initialized.value) {
    loadCurrentUser();
  }
  return { currentUser, initialized, setSession, clearSession, loadCurrentUser };
}
