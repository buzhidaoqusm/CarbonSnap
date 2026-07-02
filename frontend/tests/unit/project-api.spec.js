import { afterEach, describe, expect, it, vi } from "vitest";

import {
  contributeToProject,
  createProject,
  fetchProject,
  fetchProjects,
} from "../../src/api/project/project.js";

describe("project API", () => {
  afterEach(() => {
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
  });

  it("fetches project list", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        json: async () => ({
          code: 0,
          data: { items: [{ id: 1, title: "Repair Cafe" }], total: 1, page: 1, per_page: 12 },
        }),
      }),
    );

    const result = await fetchProjects({ page: 1, perPage: 12, token: "token-123" });

    expect(result.items).toHaveLength(1);
    expect(fetch).toHaveBeenCalledWith(
      expect.stringContaining("/api/projects?page=1&per_page=12"),
      expect.objectContaining({
        method: "GET",
        headers: expect.objectContaining({
          Authorization: "Bearer token-123",
        }),
      }),
    );
  });

  it("creates a project with bearer auth", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        json: async () => ({
          code: 0,
          data: { id: 3, title: "Tool Library" },
        }),
      }),
    );

    const result = await createProject(
      {
        title: "Tool Library",
        description: "Shared tools.",
        pointsTarget: 180,
        deadlineAt: "2026-04-01T10:00:00.000Z",
      },
      "token-123",
    );

    expect(result.id).toBe(3);
    expect(fetch).toHaveBeenCalledWith(
      expect.stringContaining("/api/projects"),
      expect.objectContaining({
        method: "POST",
        headers: expect.objectContaining({
          Authorization: "Bearer token-123",
        }),
      }),
    );
  });

  it("fetches detail and posts contributions", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn()
        .mockResolvedValueOnce({
          ok: true,
          json: async () => ({
            code: 0,
            data: { id: 7, title: "Detail project" },
          }),
        })
        .mockResolvedValueOnce({
          ok: true,
          json: async () => ({
            code: 0,
            data: { project: { id: 7 }, viewer_current_points: 90 },
          }),
        }),
    );

    const detail = await fetchProject(7, "token-123");
    const contribution = await contributeToProject(7, { points: 10 }, "token-123");

    expect(detail.id).toBe(7);
    expect(contribution.viewer_current_points).toBe(90);
    expect(fetch).toHaveBeenNthCalledWith(
      2,
      expect.stringContaining("/api/projects/7/contributions"),
      expect.objectContaining({
        method: "POST",
        headers: expect.objectContaining({
          Authorization: "Bearer token-123",
        }),
      }),
    );
  });
});
