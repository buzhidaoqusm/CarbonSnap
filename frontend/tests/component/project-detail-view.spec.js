import { asResponse } from "../helpers/fetch.js";
import { defineComponent, h, nextTick } from "vue";
import { mount } from "@vue/test-utils";
import { afterEach, describe, expect, it, vi } from "vitest";

vi.mock("../../src/api/project/project.js", () => ({
  fetchProject: vi.fn(),
  contributeToProject: vi.fn(),
}));

vi.mock("../../src/api/auth/auth.js", () => ({
  fetchCurrentUser: vi.fn(),
}));

vi.mock("../../src/composables/useAuth.js", () => ({
  useAuth: () => ({
    token: { value: "token-123" },
    user: { value: { username: "Alice", avatar_url: "", current_points: 180 } },
    isLoggedIn: { value: true },
  }),
}));

vi.mock("vue-router", async () => {
  const actual = await vi.importActual("vue-router");
  return {
    ...actual,
    useRoute: () => ({
      params: { id: "4" },
    }),
    useRouter: () => ({
      push: vi.fn(),
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

describe("ProjectDetailView", () => {
  afterEach(() => {
    vi.clearAllMocks();
  });

  it("loads project detail and submits a contribution", async () => {
    const { fetchProject, contributeToProject } = await import("../../src/api/project/project.js");
    const ProjectDetailView = (await import("../../src/views/project/ProjectDetailView.vue")).default;

    fetchProject.mockResolvedValue(asResponse({
      id: 4,
      title: "Tool Library",
      description: "Shared neighborhood tools.",
      creator_username: "Nina",
      points_target: 120,
      points_raised: 40,
      points_remaining: 80,
      progress_ratio: 0.3333,
      status: "fundraising",
      is_expired: false,
      days_left: 6,
      cover_image_url: "https://example.com/tool-library.jpg",
      contribution_count: 1,
      contributor_count: 1,
      recent_contributions: [],
    }));
    contributeToProject.mockResolvedValue(asResponse({
      project: {
        id: 4,
        title: "Tool Library",
        description: "Shared neighborhood tools.",
        creator_username: "Nina",
        points_target: 120,
        points_raised: 65,
        points_remaining: 55,
        progress_ratio: 0.5417,
        status: "fundraising",
        is_expired: false,
        days_left: 6,
        cover_image_url: "https://example.com/tool-library.jpg",
        contribution_count: 2,
        contributor_count: 2,
        recent_contributions: [
          {
            id: 9,
            contributor_username: "Alice",
            points: 25,
            created_at: "2026-03-30T08:00:00",
          },
        ],
      },
      contribution: { id: 9, points: 25 },
      viewer_current_points: 155,
    }));

    const wrapper = mount(ProjectDetailView, {
      global: {
        stubs: {
          AppLayout: AppLayoutStub,
          RouterLink: RouterLinkStub,
        },
      },
    });

    await flushPromises();
    await flushPromises();

    expect(fetchProject).toHaveBeenCalledWith("4", "token-123");
    expect(wrapper.text()).toContain("Tool Library");

    await wrapper.find("[data-project-detail-cover-preview]").trigger("click");
    await flushPromises();

    expect(wrapper.find("[data-image-preview-modal]").exists()).toBe(true);
    expect(wrapper.find("[data-image-preview-active]").attributes("src")).toBe("https://example.com/tool-library.jpg");
    await wrapper.find("[data-image-preview-modal] button").trigger("click");
    await flushPromises();

    await wrapper.get('input[type="number"]').setValue("25");
    await wrapper.get(".project-btn--block").trigger("click");
    await flushPromises();
    await flushPromises();

    expect(contributeToProject).toHaveBeenCalledWith(4, { points: 25 }, "token-123");
    expect(wrapper.text()).toContain("Thanks for backing this project");
    expect(wrapper.text()).toContain("65 / 120 pts");
  });
});
