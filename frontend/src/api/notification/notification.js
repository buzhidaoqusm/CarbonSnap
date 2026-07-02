import { apiRequest } from "../http.js";

export async function fetchNotifications({ page = 1, perPage = 20, unreadOnly = false, token }) {
  const params = new URLSearchParams({
    page: String(page),
    per_page: String(perPage),
    unread_only: unreadOnly ? "true" : "false",
  });

  return apiRequest(`/api/notifications?${params.toString()}`, { token });
}

export async function fetchUnreadNotificationCount(token) {
  return apiRequest("/api/notifications/unread-count", { token });
}

export async function markNotificationRead(notificationId, token) {
  return apiRequest(`/api/notifications/${notificationId}/read`, {
    method: "PATCH",
    token,
  });
}

export async function markAllNotificationsRead(token) {
  return apiRequest("/api/notifications/read-all", {
    method: "PATCH",
    token,
  });
}
