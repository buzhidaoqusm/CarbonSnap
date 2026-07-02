import { afterEach, describe, expect, it, vi } from "vitest";

import {
  fetchMarketItem,
  fetchMarketItems,
  parseMarketImageUrls,
  recordMarketLongView,
} from "../../src/api/market/market.js";

describe("market API", () => {
  afterEach(() => {
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
  });

  it("passes bearer auth when fetching market items for a logged-in user", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        json: async () => ({
          code: 0,
          data: {
            items: [{ id: 1, title: "Bottle lamp" }],
            total: 1,
            page: 1,
            per_page: 20,
          },
        }),
      }),
    );

    const result = await fetchMarketItems({ page: 1, perPage: 20, token: "token-123" });

    expect(result.items).toHaveLength(1);
    expect(fetch).toHaveBeenCalledWith(
      expect.stringContaining("/api/market/items?page=1&per_page=20"),
      expect.objectContaining({
        method: "GET",
        headers: expect.objectContaining({
          Authorization: "Bearer token-123",
        }),
      }),
    );
  });

  it("passes bearer auth when fetching market item detail", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        json: async () => ({
          code: 0,
          data: { id: 8, title: "Detail item" },
        }),
      }),
    );

    const item = await fetchMarketItem(8, "token-123");

    expect(item.id).toBe(8);
    expect(fetch).toHaveBeenCalledWith(
      expect.stringContaining("/api/market/items/8"),
      expect.objectContaining({
        method: "GET",
        headers: expect.objectContaining({
          Authorization: "Bearer token-123",
        }),
      }),
    );
  });

  it("posts market long-view tracking", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        json: async () => ({
          code: 0,
          data: { tracked: true },
        }),
      }),
    );

    const result = await recordMarketLongView(12, "token-123");

    expect(result.tracked).toBe(true);
    expect(fetch).toHaveBeenCalledWith(
      expect.stringContaining("/api/market/items/12/long-view"),
      expect.objectContaining({
        method: "POST",
        headers: expect.objectContaining({
          Authorization: "Bearer token-123",
        }),
      }),
    );
  });

  it("parses image url arrays safely", () => {
    expect(parseMarketImageUrls('["https://example.com/a.jpg"]')).toEqual([
      "https://example.com/a.jpg",
    ]);
    expect(parseMarketImageUrls("not-json")).toEqual([]);
  });
});
