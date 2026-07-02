import { apiRequest } from "../http.js";

async function apiJson(method, path, body, token = null) {
  return apiRequest(path, { method, body, token });
}

function apiPost(path, body, token = null) {
  return apiJson("POST", path, body, token);
}

async function apiGet(path, token) {
  return apiRequest(path, { token });
}

export async function registerUser(username, email, password) {
  return apiPost("/api/auth/register", { username, email, password });
}

export async function loginUser(email, password) {
  return apiPost("/api/auth/login", { email, password });
}

export async function fetchCurrentUser(token) {
  return apiGet("/api/auth/me", token);
}

export async function updateAvatar(imageDataUrl, token) {
  return apiJson("PATCH", "/api/auth/me/avatar", { image: imageDataUrl }, token);
}

export async function updateProfile({ bio }, token) {
  return apiJson("PATCH", "/api/auth/me", { bio }, token);
}
