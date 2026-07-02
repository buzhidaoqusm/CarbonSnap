import { buildEndpoint } from "./chat.js";

function getStoredAuthToken() {
  try {
    return localStorage.getItem("cs_token") || "";
  } catch {
    return "";
  }
}

async function apiGet(path) {
  const token = getStoredAuthToken();
  const response = await fetch(buildEndpoint(path), {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  });

  const data = await response.json();
  if (!response.ok || data.code !== 0) {
    throw new Error(data.message || `Request failed (${response.status})`);
  }

  return data.data;
}

async function apiDelete(path) {
  const token = getStoredAuthToken();
  const response = await fetch(buildEndpoint(path), {
    method: "DELETE",
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  });

  const data = await response.json();
  if (!response.ok || data.code !== 0) {
    throw new Error(data.message || `Request failed (${response.status})`);
  }

  return data.data;
}

export async function fetchAiConversations({ page = 1, perPage = 20 } = {}) {
  const query = new URLSearchParams({
    page: String(page),
    per_page: String(perPage),
  });
  return apiGet(`/api/ai/conversations?${query.toString()}`);
}

export async function fetchAiConversationMessages(conversationId) {
  if (conversationId === null || conversationId === undefined || conversationId === "") {
    throw new Error("Conversation id is required.");
  }

  return apiGet(`/api/ai/conversations/${conversationId}/messages`);
}

export async function deleteAiConversation(conversationId) {
  if (conversationId === null || conversationId === undefined || conversationId === "") {
    throw new Error("Conversation id is required.");
  }

  return apiDelete(`/api/ai/conversations/${conversationId}`);
}
