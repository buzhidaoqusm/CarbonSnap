import { apiRequest } from "../http.js";

export async function fetchProjects({ page = 1, perPage = 12, token } = {}) {
  const params = new URLSearchParams({
    page: String(page),
    per_page: String(perPage),
  });
  return apiRequest(`/api/projects?${params.toString()}`, token ? { token } : {});
}

export async function fetchProject(projectId, token) {
  return apiRequest(`/api/projects/${projectId}`, token ? { token } : {});
}

export async function uploadProjectImage(imageDataUrl, token) {
  return apiRequest("/api/projects/uploads", {
    method: "POST",
    body: { image: imageDataUrl },
    token,
  });
}

export async function createProject(
  { title, description = "", coverImageUrl = null, pointsTarget, deadlineAt },
  token,
) {
  return apiRequest("/api/projects", {
    method: "POST",
    body: {
      title,
      description: description || null,
      cover_image_url: coverImageUrl || null,
      points_target: pointsTarget,
      deadline_at: deadlineAt,
    },
    token,
  });
}

export async function contributeToProject(projectId, { points }, token) {
  return apiRequest(`/api/projects/${projectId}/contributions`, {
    method: "POST",
    body: { points },
    token,
  });
}
