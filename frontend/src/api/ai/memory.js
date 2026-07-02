import { buildEndpoint } from "./chat";

function getStoredAuthToken() {
  try {
    return localStorage.getItem("cs_token") || "";
  } catch {
    return "";
  }
}

async function requestJson(path, options = {}) {
  const headers = {
    "Content-Type": "application/json",
    ...options.headers,
  };

  const authToken = getStoredAuthToken();
  if (authToken) {
    headers.Authorization = `Bearer ${authToken}`;
  }

  const response = await fetch(buildEndpoint(path), {
    ...options,
    headers,
  });
  const data = await response.json();

  if (!response.ok || data.code !== 0) {
    throw new Error(data.message || "AI memory request failed.");
  }

  return data.data;
}

export async function fetchAiMemory() {
  return requestJson("/api/ai/memory", {
    method: "GET",
  });
}

export async function createAiMemoryItem(payload) {
  return requestJson("/api/ai/memory", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function updateAiMemoryItem(id, payload) {
  return requestJson(`/api/ai/memory/${id}`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}

export async function deleteAiMemoryItem(id) {
  return requestJson(`/api/ai/memory/${id}`, {
    method: "DELETE",
  });
}
