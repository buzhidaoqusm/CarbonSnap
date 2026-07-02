import { computed, ref } from "vue";
import { fetchCurrentUser, loginUser, registerUser } from "../api/auth/auth.js";
import { showSuccessToast } from "./useToast.js";

// Module-level singletons - one shared reactive state across all components
const TOKEN_KEY = "cs_token";
const USER_KEY = "cs_user";

function _readUser() {
  try {
    return JSON.parse(localStorage.getItem(USER_KEY) || "null");
  } catch {
    localStorage.removeItem(USER_KEY);
    return null;
  }
}

const _token = ref(localStorage.getItem(TOKEN_KEY) || null);
const _user = ref(_readUser());

function _persist(newToken, newUser) {
  _token.value = newToken;
  _user.value = newUser;
  localStorage.setItem(TOKEN_KEY, newToken);
  localStorage.setItem(USER_KEY, JSON.stringify(newUser));
}

function _clear() {
  _token.value = null;
  _user.value = null;
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(USER_KEY);
}

function _updateUser(partialUser) {
  if (!_user.value || !partialUser) {
    return;
  }

  const nextUser = {
    ..._user.value,
    ...partialUser,
  };

  _user.value = nextUser;
  localStorage.setItem(USER_KEY, JSON.stringify(nextUser));
}

// Composable - call inside any component setup
export function useAuth() {
  async function register(username, email, password) {
    const data = await registerUser(username, email, password);
    _persist(data.access_token, data.user);
    showSuccessToast("Account created", "Welcome to CarbonSnap.");
    return data;
  }

  async function login(email, password) {
    const data = await loginUser(email, password);
    _persist(data.access_token, data.user);
    showSuccessToast("Signed in", `Welcome back${data.user?.username ? `, ${data.user.username}` : ""}.`);
    return data;
  }

  function logout() {
    _clear();
    showSuccessToast("Signed out", "You have been logged out.");
  }

  function updateUser(partialUser) {
    _updateUser(partialUser);
  }

  async function refreshCurrentUser() {
    if (!_token.value) {
      return null;
    }

    try {
      const data = await fetchCurrentUser(_token.value);
      const nextUser = data?.user || data;
      if (nextUser) {
        _updateUser(nextUser);
      }
      return nextUser || null;
    } catch (error) {
      throw error;
    }
  }

  const isLoggedIn = computed(() => !!_token.value);

  return {
    token: _token,
    user: _user,
    isLoggedIn,
    register,
    login,
    logout,
    updateUser,
    refreshCurrentUser,
  };
}
