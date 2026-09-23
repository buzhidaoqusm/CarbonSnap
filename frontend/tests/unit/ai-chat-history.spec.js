import { asResponse } from "../helpers/fetch.js";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { fetchAiConversationMessages, fetchAiConversations } from "../../src/api/ai/history.js";

describe("ai history api", () => {
  beforeEach(() => {
    vi.stubGlobal("fetch", vi.fn());
    localStorage.clear();
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
  });

  it("requests conversations with auth header and pagination", async () => {
    localStorage.setItem("cs_token", "token-123");
    fetch.mockResolvedValue(asResponse({
      ok: true,
      json: async () => ({
        code: 0,
        message: "ok",
        data: {
          items: [],
          total: 0,
          page: 2,
          per_page: 5,
        },
      }),
    }));

    const data = await fetchAiConversations({ page: 2, perPage: 5 });

    expect(fetch).toHaveBeenCalledWith(
      expect.stringContaining("/api/ai/conversations?page=2&per_page=5"),
      expect.objectContaining({
        headers: {
          Authorization: "Bearer token-123",
        },
      }),
    );
    expect(data.page).toBe(2);
    expect(data.per_page).toBe(5);
  });

  it("requests one conversation message history", async () => {
    fetch.mockResolvedValue(asResponse({
      ok: true,
      json: async () => ({
        code: 0,
        message: "ok",
        data: {
          conversation: { id: 9, title: "Stored chat" },
          items: [],
          total: 0,
        },
      }),
    }));

    const data = await fetchAiConversationMessages(9);

    expect(fetch).toHaveBeenCalledWith(
      expect.stringContaining("/api/ai/conversations/9/messages"),
      expect.any(Object),
    );
    expect(data.conversation.id).toBe(9);
  });

  it("rejects missing conversation id before fetching", async () => {
    await expect(fetchAiConversationMessages("")).rejects.toThrow("Conversation id is required.");
    expect(fetch).not.toHaveBeenCalled();
  });
});
