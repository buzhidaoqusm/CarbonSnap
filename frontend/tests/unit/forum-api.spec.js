import { asResponse } from "../helpers/fetch.js";
import { afterEach, describe, expect, it, vi } from "vitest";

import {
  createForumComment,
  createForumPostWithImages,
  fetchForumComments,
  fetchForumPost,
  fetchForumPosts,
  parseForumImageUrls,
  trackForumPostLongView,
  toggleForumLike,
  uploadForumImage,
} from "../../src/api/forum/forum.js";

describe("forum API", () => {
  afterEach(() => {
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
  });

  it("fetches the forum list with pagination params", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(asResponse({
        ok: true,
        json: async () => ({
          code: 0,
          data: {
            items: [{ id: 1, title: "Hello" }],
            total: 1,
            page: 1,
            per_page: 20,
          },
        }),
      })),
    );

    const result = await fetchForumPosts({ page: 1, perPage: 20 });

    expect(result.items).toHaveLength(1);
    expect(fetch).toHaveBeenCalledWith(
      expect.stringContaining("/api/forum/posts?page=1&per_page=20"),
      expect.objectContaining({ method: "GET" }),
    );
  });

  it("fetches a single post and its comments", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn()
        .mockResolvedValueOnce(asResponse({
          ok: true,
          json: async () => ({
            code: 0,
            data: { id: 8, title: "Detail post", content: "Body" },
          }),
        }))
        .mockResolvedValueOnce(asResponse({
          ok: true,
          json: async () => ({
            code: 0,
            data: { items: [{ id: 3, content: "Nice" }], total: 1 },
          }),
        })),
    );

    const post = await fetchForumPost(8);
    const comments = await fetchForumComments(8);

    expect(post.id).toBe(8);
    expect(comments.items[0].id).toBe(3);
    expect(fetch).toHaveBeenNthCalledWith(
      1,
      expect.stringContaining("/api/forum/posts/8"),
      expect.any(Object),
    );
    expect(fetch).toHaveBeenNthCalledWith(
      2,
      expect.stringContaining("/api/forum/posts/8/comments"),
      expect.any(Object),
    );
  });

  it("records a forum long-view with bearer auth", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(asResponse({
        ok: true,
        json: async () => ({
          code: 0,
          data: { tracked: true },
        }),
      })),
    );

    const result = await trackForumPostLongView(8, "token-123");

    expect(result.tracked).toBe(true);
    expect(fetch).toHaveBeenCalledWith(
      expect.stringContaining("/api/forum/posts/8/long-view"),
      expect.objectContaining({
        method: "POST",
        headers: expect.objectContaining({
          Authorization: "Bearer token-123",
        }),
      }),
    );
  });

  it("creates a post with image urls and bearer auth", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(asResponse({
        ok: true,
        json: async () => ({
          code: 0,
          data: { id: 12, title: "New post" },
        }),
      })),
    );

    const result = await createForumPostWithImages(
      {
        title: "New post",
        content: "Testing create",
        imageUrls: ["https://example.com/a.jpg", "https://example.com/b.jpg"],
      },
      "token-123",
    );

    expect(result.id).toBe(12);
    expect(fetch).toHaveBeenCalledWith(
      expect.stringContaining("/api/forum/posts"),
      expect.objectContaining({
        method: "POST",
        headers: expect.objectContaining({
          Authorization: "Bearer token-123",
          "Content-Type": "application/json",
        }),
      }),
    );
  });

  it("creates comments and toggles likes against the expected endpoints", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn()
        .mockResolvedValueOnce(asResponse({
          ok: true,
          json: async () => ({
            code: 0,
            data: { id: 4, content: "Nice post" },
          }),
        }))
        .mockResolvedValueOnce(asResponse({
          ok: true,
          json: async () => ({
            code: 0,
            data: { liked: true, like_count: 2 },
          }),
        })),
    );

    const comment = await createForumComment(
      { postId: 8, content: "Nice post" },
      "token-123",
    );
    const likeResult = await toggleForumLike(
      { targetType: "comment", targetId: 4 },
      "token-123",
    );

    expect(comment.id).toBe(4);
    expect(likeResult.like_count).toBe(2);
    expect(fetch).toHaveBeenNthCalledWith(
      1,
      expect.stringContaining("/api/forum/posts/8/comments"),
      expect.objectContaining({ method: "POST" }),
    );
    expect(fetch).toHaveBeenNthCalledWith(
      2,
      expect.stringContaining("/api/forum/likes"),
      expect.objectContaining({ method: "POST" }),
    );
  });

  it("uploads a forum image to the dedicated upload endpoint", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(asResponse({
        ok: true,
        json: async () => ({
          code: 0,
          data: { url: "/api/uploads/forum/demo.png" },
        }),
      })),
    );

    const result = await uploadForumImage("data:image/png;base64,abc", "token-123");

    expect(result.url).toBe("/api/uploads/forum/demo.png");
    expect(fetch).toHaveBeenCalledWith(
      expect.stringContaining("/api/forum/uploads"),
      expect.objectContaining({
        method: "POST",
        headers: expect.objectContaining({
          Authorization: "Bearer token-123",
        }),
      }),
    );
  });

  it("parses image url arrays safely", () => {
    expect(parseForumImageUrls('["https://example.com/a.jpg"]')).toEqual([
      "https://example.com/a.jpg",
    ]);
    expect(parseForumImageUrls("not-json")).toEqual([]);
  });
});
