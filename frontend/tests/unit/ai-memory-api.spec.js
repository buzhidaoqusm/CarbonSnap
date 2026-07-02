import { afterEach, describe, expect, it, vi } from "vitest";

import {
  createAiMemoryItem,
  deleteAiMemoryItem,
  fetchAiMemory,
  updateAiMemoryItem,
} from "../../src/api/ai/memory.js";


describe("AI memory API", () => {
  afterEach(() => {
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
  });

  it("fetches ai memory summary and items", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        json: async () => ({
          code: 0,
          data: {
            summary: {
              action_preferences: { response_style: "concise" },
              content_interest_preferences: { topics: [], confidence_score: 0 },
            },
            items: [],
          },
        }),
      }),
    );

    const result = await fetchAiMemory();

    expect(result.summary.action_preferences.response_style).toBe("concise");
    expect(fetch).toHaveBeenCalledWith(expect.stringContaining("/api/ai/memory"), expect.any(Object));
  });

  it("sends delete and patch requests to the expected endpoints", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        json: async () => ({
          code: 0,
          data: { summary: {}, item: {} },
        }),
      }),
    );

    await createAiMemoryItem({
      memory_type: "response_style",
      memory_key: "response_style",
      value: { value: "concise" },
    });
    await updateAiMemoryItem(5, {
      value: { value: "detailed" },
    });
    await deleteAiMemoryItem(5);

    expect(fetch).toHaveBeenNthCalledWith(
      1,
      expect.stringContaining("/api/ai/memory"),
      expect.objectContaining({ method: "POST" }),
    );
    expect(fetch).toHaveBeenNthCalledWith(
      2,
      expect.stringContaining("/api/ai/memory/5"),
      expect.objectContaining({ method: "PATCH" }),
    );
    expect(fetch).toHaveBeenNthCalledWith(
      3,
      expect.stringContaining("/api/ai/memory/5"),
      expect.objectContaining({ method: "DELETE" }),
    );
  });
});
