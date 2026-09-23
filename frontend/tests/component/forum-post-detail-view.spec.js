import { asResponse } from "../helpers/fetch.js";
import { defineComponent, h, nextTick } from "vue";
import { mount } from "@vue/test-utils";
import { afterEach, describe, expect, it, vi } from "vitest";

const routerPush = vi.fn();
const authState = vi.hoisted(() => ({
  token: { value: "token-123" },
  user: { value: { username: "Alice", avatar_url: "" } },
  isLoggedIn: { value: true },
}));

vi.mock("../../src/api/forum/forum.js", () => ({
  createForumComment: vi.fn(),
  deleteForumComment: vi.fn(),
  deleteForumPost: vi.fn(),
  fetchForumComments: vi.fn(),
  fetchForumPost: vi.fn(),
  parseForumImageUrls: vi.fn((value) => {
    try {
      return JSON.parse(value || "[]");
    } catch {
      return [];
    }
  }),
  trackForumPostLongView: vi.fn(),
  toggleForumLike: vi.fn(),
  updateForumPost: vi.fn(),
  uploadForumImage: vi.fn(),
}));

vi.mock("../../src/composables/useAuth.js", () => ({
  useAuth: () => authState,
}));

vi.mock("vue-router", async () => {
  const actual = await vi.importActual("vue-router");
  return {
    ...actual,
    useRoute: () => ({
      params: { id: "8" },
    }),
    useRouter: () => ({
      push: routerPush,
    }),
  };
});

const AppLayoutStub = defineComponent({
  name: "AppLayoutStub",
  setup(_, { slots }) {
    return () => h("div", { class: "app-layout-stub" }, slots.default?.());
  },
});

const RouterLinkStub = defineComponent({
  name: "RouterLinkStub",
  props: {
    to: {
      type: [String, Object],
      required: true,
    },
  },
  setup(props, { slots, attrs }) {
    return () => h("a", { ...attrs, href: typeof props.to === "string" ? props.to : "#" }, slots.default?.());
  },
});

const flushPromises = async () => {
  await Promise.resolve();
  await nextTick();
};

describe("ForumPostDetailView", () => {
  afterEach(() => {
    vi.useRealTimers();
    vi.clearAllMocks();
    authState.token.value = "token-123";
    authState.user.value = { username: "Alice", avatar_url: "" };
    authState.isLoggedIn.value = true;
  });

  it("loads post data, allows creating comments and replies, and toggles likes", async () => {
    const {
      createForumComment,
      fetchForumComments,
      fetchForumPost,
      trackForumPostLongView,
      toggleForumLike,
    } = await import("../../src/api/forum/forum.js");
    const ForumPostDetailView =
      (await import("../../src/views/forum/ForumPostDetailView.vue")).default;

    fetchForumPost.mockResolvedValue(asResponse({
      id: 8,
      author_id: 3,
      title: "Detail post",
      content: "Post body",
      status: "published",
      like_count: 1,
      liked_by_user: false,
      created_at: "2026-03-26T12:00:00",
      image_urls_json: '["https://example.com/image.jpg"]',
    }));
    fetchForumComments
      .mockResolvedValueOnce(asResponse({
        items: [
          {
            id: 4,
            user_id: 9,
            content: "Existing comment",
            created_at: "2026-03-26T12:30:00",
            like_count: 0,
            liked_by_user: false,
            parent_comment_id: null,
          },
        ],
      }))
      .mockResolvedValueOnce(asResponse({
        items: [
          {
            id: 4,
            user_id: 9,
            content: "Existing comment",
            created_at: "2026-03-26T12:30:00",
            like_count: 1,
            liked_by_user: true,
            parent_comment_id: null,
          },
          {
            id: 5,
            user_id: 7,
            content: "New comment",
            created_at: "2026-03-26T12:45:00",
            like_count: 0,
            liked_by_user: false,
            parent_comment_id: null,
          },
          {
            id: 6,
            user_id: 5,
            content: "Reply comment",
            created_at: "2026-03-26T12:50:00",
            like_count: 0,
            liked_by_user: false,
            parent_comment_id: 4,
          },
        ],
      }))
      .mockResolvedValueOnce(asResponse({
        items: [
          {
            id: 4,
            user_id: 9,
            content: "Existing comment",
            created_at: "2026-03-26T12:30:00",
            like_count: 1,
            liked_by_user: true,
            parent_comment_id: null,
          },
          {
            id: 5,
            user_id: 7,
            content: "New comment",
            created_at: "2026-03-26T12:45:00",
            like_count: 1,
            liked_by_user: true,
            parent_comment_id: null,
          },
          {
            id: 6,
            user_id: 5,
            content: "Reply comment",
            created_at: "2026-03-26T12:50:00",
            like_count: 0,
            liked_by_user: false,
            parent_comment_id: 4,
          },
          {
            id: 7,
            user_id: 6,
            content: "Nested reply",
            created_at: "2026-03-26T12:55:00",
            like_count: 0,
            liked_by_user: false,
            parent_comment_id: 4,
          },
        ],
      }));
    createForumComment
      .mockResolvedValueOnce(asResponse({ id: 5, content: "New comment" }))
      .mockResolvedValueOnce(asResponse({ id: 7, content: "Nested reply", parent_comment_id: 4 }));
    trackForumPostLongView.mockResolvedValue(asResponse({ recorded: true, post_id: 8, action_type: "long_view" }));
    toggleForumLike
      .mockResolvedValueOnce(asResponse({ liked: true, like_count: 2 }))
      .mockResolvedValueOnce(asResponse({ liked: true, like_count: 1 }));

    const wrapper = mount(ForumPostDetailView, {
      global: {
        stubs: {
          AppLayout: AppLayoutStub,
          RouterLink: RouterLinkStub,
        },
      },
    });

    await flushPromises();
    await flushPromises();

    expect(wrapper.find("[data-forum-detail-layout]").exists()).toBe(true);
    expect(wrapper.text()).toContain("Comments");
    expect(wrapper.text()).toContain("Detail post");
    expect(wrapper.text()).toContain("Existing comment");
    expect(wrapper.findAll("img")).toHaveLength(1);

    await wrapper.find("[data-forum-detail-like]").trigger("click");
    await flushPromises();

    await wrapper.find('textarea[placeholder="Share your thoughts with the community"]').setValue("New comment");
    await wrapper.find("form").trigger("submit.prevent");
    await flushPromises();
    await flushPromises();

    await wrapper.find("[data-forum-comment-reply]").trigger("click");
    await flushPromises();
    await wrapper.find('textarea[placeholder="Reply to the discussion"]').setValue("Nested reply");
    await wrapper.findAll("form")[1].trigger("submit.prevent");
    await flushPromises();
    await flushPromises();

    const commentSixLike = wrapper
      .findAll("[data-forum-comment-like]")
      .find((button) => button.attributes("aria-label") === "Like comment 6");
    await commentSixLike.trigger("click");
    await flushPromises();

    expect(createForumComment).toHaveBeenCalledWith(
      { postId: "8", content: "New comment" },
      "token-123",
    );
    expect(createForumComment).toHaveBeenNthCalledWith(
      2,
      { postId: "8", content: "Nested reply", parentCommentId: 4 },
      "token-123",
    );
    expect(toggleForumLike).toHaveBeenNthCalledWith(
      1,
      { targetType: "post", targetId: 8 },
      "token-123",
    );
    expect(toggleForumLike).toHaveBeenNthCalledWith(
      2,
      { targetType: "comment", targetId: 6 },
      "token-123",
    );
    expect(trackForumPostLongView).not.toHaveBeenCalled();
    expect(fetchForumComments).toHaveBeenCalledTimes(3);
    expect(wrapper.text()).toContain("Reply to comment #4");
  });

  it("records a long-view event after the dwell threshold", async () => {
    vi.useFakeTimers();

    const {
      fetchForumComments,
      fetchForumPost,
      trackForumPostLongView,
    } = await import("../../src/api/forum/forum.js");
    const ForumPostDetailView =
      (await import("../../src/views/forum/ForumPostDetailView.vue")).default;

    fetchForumPost.mockResolvedValue(asResponse({
      id: 8,
      author_id: 3,
      title: "Detail post",
      content: "Post body",
      status: "published",
      like_count: 1,
      liked_by_user: false,
      created_at: "2026-03-26T12:00:00",
      image_urls_json: "[]",
    }));
    fetchForumComments.mockResolvedValue(asResponse({ items: [] }));
    trackForumPostLongView.mockResolvedValue(asResponse({ recorded: true, post_id: 8, action_type: "long_view" }));

    mount(ForumPostDetailView, {
      global: {
        stubs: {
          AppLayout: AppLayoutStub,
          RouterLink: RouterLinkStub,
        },
      },
    });

    await flushPromises();
    await flushPromises();

    expect(trackForumPostLongView).not.toHaveBeenCalled();

    await vi.advanceTimersByTimeAsync(15000);
    await flushPromises();

    expect(trackForumPostLongView).toHaveBeenCalledWith(8, "token-123");
  });

  it("lets readers switch between multiple post images", async () => {
    const { fetchForumComments, fetchForumPost } = await import("../../src/api/forum/forum.js");
    const ForumPostDetailView =
      (await import("../../src/views/forum/ForumPostDetailView.vue")).default;

    fetchForumPost.mockResolvedValue(asResponse({
      id: 8,
      author_id: 3,
      title: "Gallery post",
      content: "Post body",
      status: "published",
      like_count: 1,
      liked_by_user: false,
      created_at: "2026-03-26T12:00:00",
      image_urls_json: '["https://example.com/one.jpg","https://example.com/two.jpg"]',
    }));
    fetchForumComments.mockResolvedValue(asResponse({ items: [] }));

    const wrapper = mount(ForumPostDetailView, {
      global: {
        stubs: {
          AppLayout: AppLayoutStub,
          RouterLink: RouterLinkStub,
        },
      },
    });

    await flushPromises();
    await flushPromises();

    expect(wrapper.find("[data-forum-detail-gallery] img").attributes("src")).toBe("https://example.com/one.jpg");
    expect(wrapper.findAll("[data-forum-gallery-thumb]")).toHaveLength(2);

    await wrapper.find("[data-forum-gallery-next]").trigger("click");
    await flushPromises();

    expect(wrapper.find("[data-forum-detail-gallery] img").attributes("src")).toBe("https://example.com/two.jpg");

    await wrapper.find("[data-forum-gallery-preview-trigger]").trigger("click");
    await flushPromises();

    expect(wrapper.find("[data-image-preview-modal]").exists()).toBe(true);
    expect(wrapper.find("[data-image-preview-active]").attributes("src")).toBe("https://example.com/two.jpg");
  });

  it("opens edit post in a modal and saves title, content, and image order", async () => {
    authState.user.value = { id: 3, username: "Alice", avatar_url: "" };

    const {
      fetchForumComments,
      fetchForumPost,
      updateForumPost,
    } = await import("../../src/api/forum/forum.js");
    const ForumPostDetailView =
      (await import("../../src/views/forum/ForumPostDetailView.vue")).default;

    fetchForumPost.mockResolvedValue(asResponse({
      id: 8,
      author_id: 3,
      title: "Original post",
      content: "Original body",
      status: "published",
      like_count: 1,
      liked_by_user: false,
      created_at: "2026-03-26T12:00:00",
      image_urls_json: '["/api/uploads/forum/old.jpg"]',
    }));
    fetchForumComments.mockResolvedValue(asResponse({ items: [] }));
    updateForumPost.mockResolvedValue(asResponse({
      id: 8,
      title: "Updated post",
      content: "Updated body",
      image_urls_json: '["/api/uploads/forum/old.jpg"]',
    }));

    const wrapper = mount(ForumPostDetailView, {
      global: {
        stubs: {
          AppLayout: AppLayoutStub,
          RouterLink: RouterLinkStub,
        },
      },
    });

    await flushPromises();
    await flushPromises();

    await wrapper.findAll("button").find((button) => button.text() === "Edit post").trigger("click");
    await flushPromises();

    expect(wrapper.find("[data-forum-edit-composer]").exists()).toBe(true);
    expect(wrapper.findAll("[data-forum-edit-image-preview]")).toHaveLength(1);

    await wrapper.find("[data-forum-edit-composer] input[type='text']").setValue("Updated post");
    await wrapper.find("[data-forum-edit-composer] textarea").setValue("Updated body");
    await wrapper.find("[data-forum-edit-composer] form").trigger("submit.prevent");
    await flushPromises();

    expect(updateForumPost).toHaveBeenCalledWith(
      {
        postId: 8,
        title: "Updated post",
        content: "Updated body",
        imageUrlsJson: '["/api/uploads/forum/old.jpg"]',
      },
      "token-123",
    );
    expect(wrapper.find("[data-forum-edit-composer]").exists()).toBe(false);
    expect(wrapper.text()).toContain("Updated post");
  });
});
