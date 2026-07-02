import { computed, ref } from "vue";

import {
  fetchNotifications,
  fetchUnreadNotificationCount,
  markNotificationRead,
} from "../api/notification/notification.js";
import { useAuth } from "./useAuth.js";
import { dismissToast, dismissToastsByKind, showToast, toasts } from "./useToast.js";

const POLL_INTERVAL_MS = 20_000;
const RECENT_WINDOW_PAGE = 1;
const RECENT_WINDOW_PER_PAGE = 50;
const MAX_SEEN_IDS = 200;

const notifications = ref([]);
const unreadCount = ref(0);

let authState = null;
let isPolling = false;
let isRefreshing = false;
let pollTimerId = null;
let focusListener = null;
let hasBootstrapped = false;
const seenNotificationIds = new Set();
const seenNotificationOrder = [];

function getAuthState() {
  if (!authState) {
    authState = useAuth();
  }
  return authState;
}

function getCurrentToken() {
  const state = getAuthState();
  return String(state.token?.value || "").trim();
}

function normalizeNotificationId(notificationOrId) {
  if (notificationOrId && typeof notificationOrId === "object") {
    return notificationOrId.id ?? null;
  }
  return notificationOrId ?? null;
}

function rememberSeenId(notificationId) {
  const id = normalizeNotificationId(notificationId);
  if (id === null || id === undefined) {
    return;
  }

  const key = String(id);
  if (seenNotificationIds.has(key)) {
    return;
  }

  seenNotificationIds.add(key);
  seenNotificationOrder.push(key);

  while (seenNotificationOrder.length > MAX_SEEN_IDS) {
    const removedId = seenNotificationOrder.shift();
    if (removedId !== undefined) {
      seenNotificationIds.delete(removedId);
    }
  }
}

function isNotificationSeen(notificationId) {
  const id = normalizeNotificationId(notificationId);
  if (id === null || id === undefined) {
    return false;
  }
  return seenNotificationIds.has(String(id));
}

function clearToasts() {
  dismissToastsByKind("notification");
}

function clearState() {
  notifications.value = [];
  unreadCount.value = 0;
  hasBootstrapped = false;
  seenNotificationIds.clear();
  seenNotificationOrder.length = 0;
  clearToasts();
}

function pushToast(notification) {
  if (!notification) {
    return;
  }

  const existingToastIds = new Set(toasts.value.map((item) => String(item.id)));
  if (existingToastIds.has(String(notification.id))) {
    return;
  }

  showToast({
    ...notification,
    id: notification.id,
    kind: "notification",
    type: "info",
    notification,
  });
}

function syncUnreadCountFromNotifications(items) {
  unreadCount.value = items.reduce((total, item) => total + (item?.is_read ? 0 : 1), 0);
}

function resolveNotificationTarget(notification) {
  return String(notification?.source_url || "").trim() || "/notification";
}

async function refresh() {
  const token = getCurrentToken();
  if (!token) {
    clearState();
    return;
  }

  if (isRefreshing) {
    return;
  }

  isRefreshing = true;
  try {
    const [countResult, notificationsResult] = await Promise.allSettled([
      fetchUnreadNotificationCount(token),
      fetchNotifications({
        page: RECENT_WINDOW_PAGE,
        perPage: RECENT_WINDOW_PER_PAGE,
        unreadOnly: false,
        token,
      }),
    ]);

    if (countResult.status === "fulfilled") {
      unreadCount.value = Number(countResult.value?.unread_count ?? 0) || 0;
    }

    if (notificationsResult.status === "fulfilled") {
      const items = Array.isArray(notificationsResult.value?.items)
        ? notificationsResult.value.items
        : [];
      notifications.value = items;

      if (!hasBootstrapped) {
        items.forEach((item) => rememberSeenId(item.id));
        hasBootstrapped = true;
      } else {
        const newNotifications = items.filter((item) => !isNotificationSeen(item.id));
        newNotifications.forEach((item) => {
          pushToast(item);
          rememberSeenId(item.id);
        });
      }

      if (countResult.status !== "fulfilled") {
        syncUnreadCountFromNotifications(items);
      }
    }
  } finally {
    isRefreshing = false;
  }
}

function stopPolling() {
  if (pollTimerId !== null) {
    clearInterval(pollTimerId);
    pollTimerId = null;
  }
  if (focusListener !== null && typeof window !== "undefined") {
    window.removeEventListener("focus", focusListener);
    focusListener = null;
  }
  isPolling = false;
  clearState();
}

async function startPolling() {
  const token = getCurrentToken();
  if (!token) {
    stopPolling();
    return;
  }

  if (isPolling) {
    return;
  }

  isPolling = true;
  focusListener = () => {
    if (getCurrentToken()) {
      void refresh();
    }
  };

  window.addEventListener("focus", focusListener);
  await refresh();

  if (!isPolling) {
    return;
  }

  pollTimerId = window.setInterval(() => {
    void refresh();
  }, POLL_INTERVAL_MS);
}

async function markAsRead(notificationOrId) {
  const notificationId = normalizeNotificationId(notificationOrId);
  if (notificationId === null || notificationId === undefined) {
    return false;
  }

  const token = getCurrentToken();
  if (!token) {
    return false;
  }

  try {
    await markNotificationRead(notificationId, token);
    notifications.value = notifications.value.map((item) =>
      String(item.id) === String(notificationId) ? { ...item, is_read: true } : item,
    );
    unreadCount.value = notifications.value.reduce(
      (total, item) => total + (item?.is_read ? 0 : 1),
      0,
    );
    return true;
  } catch {
    return false;
  }
}

async function openNotification(notification) {
  const target = resolveNotificationTarget(notification);
  await markAsRead(notification);
  dismissToast(notification?.id);
  return target;
}

export function useNotifications() {
  const isSignedIn = computed(() => Boolean(getAuthState().isLoggedIn?.value));

  return {
    notifications,
    toasts,
    unreadCount,
    isSignedIn,
    refresh,
    start: startPolling,
    stop: stopPolling,
    markAsRead,
    openNotification,
    dismissToast,
  };
}
