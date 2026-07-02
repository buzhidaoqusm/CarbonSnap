import { defineComponent, h, nextTick } from "vue";
import { mount } from "@vue/test-utils";
import { afterAll, afterEach, describe, expect, it, vi } from "vitest";

const routerPush = vi.fn();

vi.mock("../../src/api/forum/forum.js", () => ({
  createForumPostWithImages: vi.fn(),
  fetchForumPosts: vi.fn(),
  parseForumImageUrls: vi.fn(() => []),
  toggleForumLike: vi.fn(),
  uploadForumImage: vi.fn(),
}));

vi.mock("../../src/composables/useAuth.js", () => ({
  useAuth: () => ({
    token: { value: "token-123" },
    user: { value: { username: "Alice", avatar_url: "" } },
    isLoggedIn: { value: true },
  }),
}));

vi.mock("vue-router", async () => {
  const actual = await vi.importActual("vue-router");
  return {
    ...actual,
    useRouter: () => ({
      push: routerPush,
    }),
  };
});

const AppLayoutStub = defineComponent({
  name: "AppLayoutStub",
  setup(_, { slots }) {
    return () =>
      h("div", { class: "app-layout-stub" }, [
        h("div", { "data-app-shell-topbar": "" }),
        slots.default?.(),
      ]);
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

const previewImageAlts = (wrapper) =>
  wrapper.findAll("[data-forum-image-preview] img").map((node) => node.attributes("alt"));

describe("ForumListView", () => {
  const originalFileReader = globalThis.FileReader;
  const originalCreateObjectUrl = globalThis.URL.createObjectURL;
  const originalRevokeObjectUrl = globalThis.URL.revokeObjectURL;

  class MockFileReader {
    constructor() {
      this.result = null;
      this.onload = null;
      this.onerror = null;
    }

    readAsDataURL(file) {
      this.result = `data:${file.type};name=${file.name};base64,ZmFrZQ==`;
      this.onload?.();
    }
  }

  globalThis.FileReader = MockFileReader;
  globalThis.URL.createObjectURL = vi.fn((file) => `blob:preview-${file.name}`);
  globalThis.URL.revokeObjectURL = vi.fn();

  afterEach(() => {
    vi.clearAllMocks();
  });

  afterAll(() => {
    globalThis.FileReader = originalFileReader;
    globalThis.URL.createObjectURL = originalCreateObjectUrl;
    globalThis.URL.revokeObjectURL = originalRevokeObjectUrl;
  });

  it("loads posts and creates a new post from the composer window", async () => {
    const {
      createForumPostWithImages,
      fetchForumPosts,
      uploadForumImage,
    } = await import("../../src/api/forum/forum.js");
    const ForumListView = (await import("../../src/views/forum/ForumListView.vue")).default;

    fetchForumPosts
      .mockResolvedValueOnce({
        items: [{ id: 1, title: "Existing post", content: "Existing content", author_id: 9, created_at: "2026-03-26T10:00:00" }],
      })
      .mockResolvedValueOnce({
        items: [
          { id: 2, title: "New post", content: "Testing content", author_id: 9, created_at: "2026-03-26T11:00:00" },
          { id: 1, title: "Existing post", content: "Existing content", author_id: 9, created_at: "2026-03-26T10:00:00" },
        ],
    });
    createForumPostWithImages.mockResolvedValue({ id: 2, title: "New post" });
    uploadForumImage.mockImplementation((imageDataUrl) => {
      const fileName = imageDataUrl.match(/name=([^;]+)/)?.[1] || "image.jpg";
      return Promise.resolve({ url: `/api/uploads/forum/${fileName}` });
    });

    const wrapper = mount(ForumListView, {
      global: {
        stubs: {
          AppLayout: AppLayoutStub,
          RouterLink: RouterLinkStub,
        },
      },
    });

    await flushPromises();
    await flushPromises();

    expect(wrapper.find("[data-app-shell-topbar]").exists()).toBe(true);
    expect(wrapper.find("[data-forum-feed]").exists()).toBe(true);
    expect(wrapper.find("[data-forum-featured-post]").exists()).toBe(true);
    expect(wrapper.find("[data-forum-right-rail]").exists()).toBe(true);
    expect(wrapper.text()).toContain("Community Feed");
    expect(wrapper.text()).toContain("Top Contributors");
    expect(wrapper.text()).toContain("Existing post");

    await wrapper.find("[data-forum-compose-toggle]").trigger("click");
    await flushPromises();
    expect(wrapper.find("[data-forum-composer-window]").exists()).toBe(true);
    expect(wrapper.find("[data-forum-composer]").exists()).toBe(true);
    expect(wrapper.find('[role="dialog"][aria-modal="true"]').exists()).toBe(true);

    await wrapper.find('input[placeholder="What are you sharing today?"]').setValue("New post");
    await wrapper.find('textarea[placeholder="Add the context, result, or question behind your post."]').setValue("Testing content");
    const firstImageFile = new File(["first"], "first.jpg", { type: "image/jpeg" });
    const secondImageFile = new File(["second"], "second.jpg", { type: "image/jpeg" });
    const thirdImageFile = new File(["third"], "third.jpg", { type: "image/jpeg" });
    const fileInput = wrapper.find('input[type="file"]');
    Object.defineProperty(fileInput.element, "files", {
      configurable: true,
      value: [firstImageFile, secondImageFile, thirdImageFile],
    });
    await fileInput.trigger("change");

    expect(wrapper.findAll("[data-forum-image-preview]")).toHaveLength(3);
    expect(wrapper.find('img[alt="first.jpg preview"]').attributes("src")).toBe("blob:preview-first.jpg");

    await wrapper.find('button[aria-label="Remove second.jpg"]').trigger("click");
    await flushPromises();
    expect(wrapper.findAll("[data-forum-image-preview]")).toHaveLength(2);
    expect(wrapper.text()).not.toContain("second.jpg");

    const previewsBeforeDrag = wrapper.findAll("[data-forum-image-preview]");
    await previewsBeforeDrag.at(1).trigger("dragstart");
    await previewsBeforeDrag.at(0).trigger("dragover");
    await flushPromises();
    expect(previewImageAlts(wrapper)).toEqual(["third.jpg preview", "first.jpg preview"]);

    await wrapper.findAll("[data-forum-image-preview]").at(0).trigger("drop");
    await flushPromises();

    await wrapper.find("form").trigger("submit.prevent");

    await flushPromises();
    await flushPromises();

    expect(uploadForumImage).toHaveBeenCalledTimes(2);
    expect(uploadForumImage.mock.calls[0][0]).toContain("third.jpg");
    expect(uploadForumImage.mock.calls[1][0]).toContain("first.jpg");
    expect(createForumPostWithImages).toHaveBeenCalledWith(
      {
        title: "New post",
        content: "Testing content",
        imageUrls: ["/api/uploads/forum/third.jpg", "/api/uploads/forum/first.jpg"],
      },
      "token-123",
    );
    expect(fetchForumPosts).toHaveBeenCalledTimes(2);
    expect(wrapper.text()).toContain("Post #2 created successfully.");
  });

  it("keeps the current feed order stable while rendering post cards", async () => {
    const { fetchForumPosts } = await import("../../src/api/forum/forum.js");
    const ForumListView = (await import("../../src/views/forum/ForumListView.vue")).default;

    fetchForumPosts.mockResolvedValue({
      items: [
        { id: 11, title: "First post", content: "Alpha", author_id: 9, like_count: 0, created_at: "2026-03-26T10:00:00" },
        { id: 12, title: "Second post", content: "Beta", author_id: 8, like_count: 10, created_at: "2026-03-26T11:00:00" },
        { id: 13, title: "Third post", content: "Gamma", author_id: 7, like_count: 3, created_at: "2026-03-26T12:00:00" },
      ],
    });
    const wrapper = mount(ForumListView, {
      global: {
        stubs: {
          AppLayout: AppLayoutStub,
          RouterLink: RouterLinkStub,
        },
      },
    });

    await flushPromises();
    await flushPromises();

    const beforeTitles = wrapper
      .findAll("[data-forum-post-card] h4")
      .map((node) => node.text());

    expect(beforeTitles).toEqual(["First post", "Third post"]);

    const afterTitles = wrapper
      .findAll("[data-forum-post-card] h4")
      .map((node) => node.text());

    expect(afterTitles).toEqual(beforeTitles);
    expect(wrapper.text()).toContain("10");
  });
});
