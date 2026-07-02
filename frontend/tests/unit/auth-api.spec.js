import { afterEach, describe, expect, it, vi } from "vitest";

import { updateAvatar } from "../../src/api/auth/auth.js";

describe("auth API", () => {
  afterEach(() => {
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
  });

  it("updates the current user's avatar with PATCH and bearer auth", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        text: async () =>
          JSON.stringify({
            code: 0,
            data: { avatar_url: "/api/uploads/avatars/demo.png" },
          }),
      }),
    );

    const result = await updateAvatar("data:image/png;base64,abc", "token-123");

    expect(result.avatar_url).toBe("/api/uploads/avatars/demo.png");
    expect(fetch).toHaveBeenCalledWith(
      expect.stringContaining("/api/auth/me/avatar"),
      expect.objectContaining({
        method: "PATCH",
        headers: expect.objectContaining({
          Authorization: "Bearer token-123",
          "Content-Type": "application/json",
        }),
      }),
    );
  });
});
