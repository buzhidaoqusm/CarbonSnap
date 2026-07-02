/**
 * Shared HTTP client for CarbonSnap API.
 * Set VITE_USE_MOCK=true to serve in-memory fixtures (parallel frontend dev).
 */

import { resolveMock } from "../mocks/resolver.js";

function getApiBaseUrl() {
  const configured = import.meta.env.VITE_API_BASE_URL;
  const runtime =
    configured !== undefined
      ? configured
      : import.meta.env.DEV
        ? ""
        : "";
  return String(runtime).replace(/\/$/, "");
}

export function buildEndpoint(path) {
  const base = getApiBaseUrl();
  return base ? `${base}${path}` : path;
}

export function resolveBackendUrl(url) {
  const value = String(url || "").trim();
  if (!value) {
    return "";
  }

  if (/^(?:https?:|data:|blob:)/i.test(value)) {
    return value;
  }

  if (!value.startsWith("/")) {
    return value;
  }

  return buildEndpoint(value);
}

export function isMockMode() {
  return import.meta.env.VITE_USE_MOCK === "true";
}

/**
 * @param {string} path - e.g. /api/forum/posts
 * @param {{ method?: string, body?: unknown, token?: string | null }} options
 */
export async function apiRequest(path, { method = "GET", body, token } = {}) {
  if (isMockMode()) {
    return resolveMock({ path, method, body, token });
  }

  const headers = {};
  if (body !== undefined) {
    headers["Content-Type"] = "application/json";
  }
  if (token) {
    headers.Authorization = `Bearer ${token}`;
  }

  const response = await fetch(buildEndpoint(path), {
    method,
    headers,
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });

  const rawPayload = await response.text();
  let payload = null;

  if (rawPayload) {
    try {
      payload = JSON.parse(rawPayload);
    } catch {
      throw new Error("The server returned an invalid JSON response.");
    }
  }

  if (!response.ok) {
    throw new Error(payload?.message || `Request failed (${response.status})`);
  }

  if (payload === null || payload === undefined || payload === "") {
    return null;
  }

  if (typeof payload === "object" && payload !== null && "code" in payload) {
    if (payload.code !== 0) {
      throw new Error(payload.message || `Request failed (${response.status})`);
    }

    return payload.data;
  }

  return payload;
}
