import { asResponse } from "../helpers/fetch.js";
import { defineComponent, h, nextTick } from "vue";
import { mount } from "@vue/test-utils";
import { afterEach, describe, expect, it, vi } from "vitest";

vi.mock("../../src/api/project/project.js", () => ({
  createProject: vi.fn(),
  fetchProjects: vi.fn(),
  uploadProjectImage: vi.fn(),
}));

vi.mock("../../src/composables/useAuth.js", () => ({
  useAuth: () => ({
    token: { value: "token-123" },
    user: { value: { username: "Alice", avatar_url: "", current_points: 240 } },
    isLoggedIn: { value: true },
  }),
}));

vi.mock("vue-router", async () => {
  const actual = await vi.importActual("vue-router");
  return {
    ...actual,
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

describe("ProjectListView", () => {
  afterEach(() => {
    vi.clearAllMocks();
  });

  it("loads project list and renders project cards", async () => {
    const { fetchProjects } = await import("../../src/api/project/project.js");
    const ProjectListView = (await import("../../src/views/project/ProjectListView.vue")).default;

    fetchProjects.mockResolvedValue(asResponse({
      items: [
        {
          id: 1,
          title: "Repair Cafe",
          description: "Fix broken household items together.",
          creator_username: "Alice",
          points_target: 200,
          points_raised: 80,
          points_remaining: 120,
          progress_ratio: 0.4,
          status: "fundraising",
          is_expired: false,
          days_left: 12,
          cover_image_url: "https://example.com/repair.jpg",
          contribution_count: 2,
          contributor_count: 2,
        },
      ],
      total: 1,
      page: 1,
      per_page: 12,
      summary: {
        fundraising_count: 1,
        completed_count: 0,
        points_raised_total: 80,
      },
    }));

    const wrapper = mount(ProjectListView, {
      global: {
        stubs: {
          AppLayout: AppLayoutStub,
          RouterLink: RouterLinkStub,
        },
      },
    });

    await flushPromises();
    await flushPromises();

    expect(fetchProjects).toHaveBeenCalledWith({ page: 1, perPage: 12, token: "token-123" });
    expect(wrapper.text()).toContain("Repair Cafe");
    expect(wrapper.text()).toContain("80 / 200 pts");

    await wrapper.find("[data-project-cover-preview-trigger]").trigger("click");
    await flushPromises();

    expect(wrapper.find("[data-image-preview-modal]").exists()).toBe(true);
    expect(wrapper.find("[data-image-preview-active]").attributes("src")).toBe("https://example.com/repair.jpg");
  });

  it("opens start project in a modal and creates a project from the list page", async () => {
    window.scrollTo = vi.fn();

    const { createProject, fetchProjects } = await import("../../src/api/project/project.js");
    const ProjectListView = (await import("../../src/views/project/ProjectListView.vue")).default;

    fetchProjects.mockResolvedValue(asResponse({
      items: [],
      total: 0,
      page: 1,
      per_page: 12,
      summary: {
        fundraising_count: 0,
        completed_count: 0,
        points_raised_total: 0,
      },
    }));
    createProject.mockResolvedValue(asResponse({ id: 9, title: "Compost Hub" }));

    const wrapper = mount(ProjectListView, {
      global: {
        stubs: {
          AppLayout: AppLayoutStub,
          RouterLink: RouterLinkStub,
        },
      },
    });

    await flushPromises();
    await flushPromises();

    await wrapper.findAll("button").find((button) => button.text() === "Start a project").trigger("click");
    await flushPromises();

    expect(wrapper.find("[data-project-composer]").exists()).toBe(true);
    expect(wrapper.find("[data-project-composer] input[type='date']").exists()).toBe(true);
    expect(wrapper.find("[data-project-composer] input[type='time']").exists()).toBe(true);

    await wrapper.find("[data-project-composer] input[type='text']").setValue("Compost Hub");
    await wrapper.find("[data-project-composer] textarea").setValue("Neighborhood compost collection.");
    await wrapper.find("[data-project-composer] form").trigger("submit.prevent");
    await flushPromises();
    await flushPromises();

    expect(createProject).toHaveBeenCalledWith(
      expect.objectContaining({
        title: "Compost Hub",
        description: "Neighborhood compost collection.",
        coverImageUrl: null,
        pointsTarget: 200,
        deadlineAt: expect.any(String),
      }),
      "token-123",
    );
    expect(wrapper.find("[data-project-composer]").exists()).toBe(false);
    expect(fetchProjects).toHaveBeenCalledTimes(2);
  });
});
