import { apiRequest } from "../http.js";

export function parseMarketImageUrls(imageUrlsJson) {
  if (!imageUrlsJson) {
    return [];
  }
  if (Array.isArray(imageUrlsJson)) {
    return imageUrlsJson.filter((v) => typeof v === "string" && v.trim());
  }
  try {
    const parsed = JSON.parse(imageUrlsJson);
    return Array.isArray(parsed)
      ? parsed.filter((v) => typeof v === "string" && v.trim())
      : [];
  } catch {
    return [];
  }
}

export async function fetchMarketItems({ page = 1, perPage = 20, token } = {}) {
  const params = new URLSearchParams({
    page: String(page),
    per_page: String(perPage),
  });
  return apiRequest(`/api/market/items?${params.toString()}`, token ? { token } : {});
}

export async function fetchMyMarketItems({ page = 1, perPage = 20, token }) {
  const params = new URLSearchParams({
    page: String(page),
    per_page: String(perPage),
  });
  return apiRequest(`/api/market/items/mine?${params.toString()}`, { token });
}

export async function fetchMarketItem(itemId, token) {
  return apiRequest(`/api/market/items/${itemId}`, token ? { token } : {});
}

export async function createMarketItem(
  { title, description = "", pricePoints, imageUrlsJson = null },
  token,
) {
  return apiRequest("/api/market/items", {
    method: "POST",
    body: {
      title,
      description: description || null,
      price_points: pricePoints,
      image_urls_json: imageUrlsJson,
    },
    token,
  });
}

export async function deleteMarketItem(itemId, token) {
  return apiRequest(`/api/market/items/${itemId}`, {
    method: "DELETE",
    token,
  });
}

export async function placeMarketOrder({ itemId }, token) {
  return apiRequest("/api/market/orders", {
    method: "POST",
    body: { item_id: itemId },
    token,
  });
}

export async function recordMarketLongView(itemId, token) {
  return apiRequest(`/api/market/items/${itemId}/long-view`, {
    method: "POST",
    token,
  });
}

export async function fetchMyOrders({ page = 1, perPage = 20, role = "all", token }) {
  const params = new URLSearchParams({
    page: String(page),
    per_page: String(perPage),
    role,
  });
  return apiRequest(`/api/market/orders?${params.toString()}`, { token });
}

export async function shipMarketOrder(orderId, token) {
  return apiRequest(`/api/market/orders/${orderId}/ship`, {
    method: "PATCH",
    token,
  });
}

export async function confirmMarketOrder(orderId, token) {
  return apiRequest(`/api/market/orders/${orderId}/confirm`, {
    method: "PATCH",
    token,
  });
}

export async function cancelMarketOrder(orderId, token) {
  return apiRequest(`/api/market/orders/${orderId}/cancel`, {
    method: "PATCH",
    token,
  });
}
