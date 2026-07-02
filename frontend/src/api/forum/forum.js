import { apiRequest } from "../http.js";
function getApiBaseUrl() {
  const configured = import.meta.env.VITE_API_BASE_URL;
  const runtime =
    configured !== undefined
      ? configured
      : import.meta.env.DEV
        ? "http://127.0.0.1:5000"
        : "";
  return runtime.replace(/\/$/, "");
}

function buildEndpoint(path) {
  const base = getApiBaseUrl();
  return base ? `${base}${path}` : path;
}

export function parseForumImageUrls(imageUrlsJson) {
  if (!imageUrlsJson) {
    return [];
  }

  if (Array.isArray(imageUrlsJson)) {
    return imageUrlsJson.filter((value) => typeof value === "string" && value.trim());
  }

  try {
    const parsed = JSON.parse(imageUrlsJson);
    return Array.isArray(parsed)
      ? parsed.filter((value) => typeof value === "string" && value.trim())
      : [];
  } catch {
    return [];
  }
}

export async function fetchForumPosts({ page = 1, perPage = 20, token = null } = {}) {
  const params = new URLSearchParams({
    page: String(page),
    per_page: String(perPage),
  });
  return apiRequest(`/api/forum/posts?${params.toString()}`, { token });
}

export async function fetchForumPost(postId, token = null) {
  return apiRequest(`/api/forum/posts/${postId}`, { token });
}

export async function trackForumPostLongView(postId, token) {
  return apiRequest(`/api/forum/posts/${postId}/long-view`, {
    method: "POST",
    token,
  });
}

export async function createForumPost({ title, content }, token) {
  return apiRequest("/api/forum/posts", {
    method: "POST",
    body: { title, content },
    token,
  });
}

export async function updateForumPost({ postId, title, content, imageUrlsJson = null }, token) {
  const body = {};
  if (title !== undefined) {
    body.title = title;
  }
  if (content !== undefined) {
    body.content = content;
  }
  if (imageUrlsJson !== undefined) {
    body.image_urls_json = imageUrlsJson;
  }
  return apiRequest(`/api/forum/posts/${postId}`, {
    method: "PUT",
    body,
    token,
  });
}

export async function deleteForumPost(postId, token) {
  return apiRequest(`/api/forum/posts/${postId}`, {
    method: "DELETE",
    token,
  });
}

export async function fetchForumComments(postId, token = null) {
  return apiRequest(`/api/forum/posts/${postId}/comments`, { token });
}

export async function uploadForumImage(imageDataUrl, token) {
  return apiRequest("/api/forum/uploads", {
    method: "POST",
    body: {
      image: imageDataUrl,
    },
    token,
  });
}

export async function createForumPostWithImages({ title, content, imageUrls = [] }, token) {
  const normalizedImageUrls = imageUrls
    .map((value) => String(value || "").trim())
    .filter(Boolean);

  return apiRequest("/api/forum/posts", {
    method: "POST",
    body: {
      title,
      content,
      image_urls_json: normalizedImageUrls.length > 0 ? JSON.stringify(normalizedImageUrls) : null,
    },
    token,
  });
}

export async function createForumComment({ postId, content, parentCommentId = null }, token) {
  const body = { content };
  if (parentCommentId !== null) {
    body.parent_comment_id = parentCommentId;
  }

  return apiRequest(`/api/forum/posts/${postId}/comments`, {
    method: "POST",
    body,
    token,
  });
}

export async function deleteForumComment(commentId, token) {
  return apiRequest(`/api/forum/comments/${commentId}`, {
    method: "DELETE",
    token,
  });
}

export async function toggleForumLike({ targetType, targetId }, token) {
  return apiRequest("/api/forum/likes", {
    method: "POST",
    body: {
      target_type: targetType,
      target_id: targetId,
    },
    token,
  });
}
