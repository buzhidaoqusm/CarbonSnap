import { ref } from "vue";
import { mount } from "@vue/test-utils";
import { afterEach, describe, expect, it, vi } from "vitest";

vi.mock("../../src/composables/useAuth.js", () => ({
  useAuth: () => ({
    logout: vi.fn(),
    isLoggedIn: ref(false),
    user: ref(null),
  }),
}));

vi.mock("../../src/composables/useNotifications.js", () => ({
  useNotifications: () => ({
    unreadCount: ref(0),
  }),
}));

vi.mock("../../src/composables/home/useHomeLandingMotion.js", () => ({
  useHomeLandingMotion: () => ref(null),
}));

const RouterLinkStub = {
  props: ["to"],
  template: '<a :href="typeof to === \'string\' ? to : \'#\'" :data-to="to"><slot /></a>',
};

describe("HomeView", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("renders the Apple-inspired CarbonSnap landing flow", async () => {
    const HomeView = (await import("../../src/views/HomeView.vue")).default;

    const wrapper = mount(HomeView, {
      global: {
        stubs: {
          RouterLink: RouterLinkStub,
        },
      },
    });

    expect(wrapper.find("[data-carbon-landing]").exists()).toBe(true);
    expect(wrapper.find("[data-home-hero]").exists()).toBe(true);
    expect(wrapper.find("[data-scene-one]").exists()).toBe(true);
    expect(wrapper.find("[data-scene-two]").exists()).toBe(true);
    expect(wrapper.find("[data-scene-three]").exists()).toBe(true);

    expect(wrapper.text()).toContain("Snap Waste.");
    expect(wrapper.text()).toContain("Measure Impact.");
    expect(wrapper.text()).not.toContain("AI-powered recycling");
    expect(wrapper.text()).toContain("Single item analysis");
    expect(wrapper.text()).toContain("One bottle becomes a complete recycling decision.");
    expect(wrapper.text()).toContain("AI Audit");
    expect(wrapper.text()).toContain("Identification is only the beginning.");

    expect(wrapper.find("[data-app-shell-topbar]").exists()).toBe(true);
    expect(wrapper.text()).toContain("CarbonSnap");
    expect(wrapper.text()).toContain("Forum");
    expect(wrapper.text()).toContain("Project");
    expect(wrapper.find("[data-home-get-started]").attributes("data-to")).toBe("/login");
    expect(wrapper.find('[data-to="/forum"]').exists()).toBe(true);
    expect(wrapper.find('[data-to="/project"]').exists()).toBe(true);
    expect(wrapper.find(".landing-nav").exists()).toBe(false);
  });

  it("plays the homepage demo by auto-scrolling instead of jumping to an anchor", async () => {
    const HomeView = (await import("../../src/views/HomeView.vue")).default;

    Object.defineProperty(window, "innerHeight", {
      configurable: true,
      value: 500,
    });
    Object.defineProperty(window, "scrollY", {
      configurable: true,
      value: 0,
    });
    Object.defineProperty(document.documentElement, "scrollHeight", {
      configurable: true,
      value: 1500,
    });
    Object.defineProperty(document.body, "scrollHeight", {
      configurable: true,
      value: 1500,
    });

    window.matchMedia = vi.fn(() => ({ matches: false }));
    document.documentElement.style.scrollBehavior = "smooth";
    document.body.style.scrollBehavior = "smooth";

    const scrollTo = vi.spyOn(window, "scrollTo").mockImplementation(() => {});
    let animationStep;
    const startTime = performance.now();
    vi.spyOn(performance, "now").mockReturnValue(startTime);
    vi.spyOn(window, "requestAnimationFrame").mockImplementation((callback) => {
      animationStep = callback;
      return 1;
    });
    vi.spyOn(window, "cancelAnimationFrame").mockImplementation(() => {});

    const wrapper = mount(HomeView, {
      global: {
        stubs: {
          RouterLink: RouterLinkStub,
        },
      },
    });

    const demoTrigger = wrapper.find("[data-home-demo-trigger]");
    expect(demoTrigger.element.tagName).toBe("BUTTON");
    expect(demoTrigger.attributes("href")).toBeUndefined();

    await demoTrigger.trigger("click");
    expect(window.requestAnimationFrame).toHaveBeenCalled();
    expect(document.documentElement.style.scrollBehavior).toBe("auto");
    expect(document.body.style.scrollBehavior).toBe("auto");

    animationStep(startTime + 5000);
    expect(scrollTo.mock.calls.at(-1)?.[0]).toMatchObject({
      left: 0,
      behavior: "auto",
    });
    expect(scrollTo.mock.calls.at(-1)?.[0].top).toBeCloseTo(500);

    animationStep(startTime + 10000);
    expect(scrollTo).toHaveBeenCalledWith({
      top: 1000,
      left: 0,
      behavior: "auto",
    });
    expect(document.documentElement.style.scrollBehavior).toBe("smooth");
    expect(document.body.style.scrollBehavior).toBe("smooth");
  });

  it("shows four item-level impact cards and the plastic bottle analysis content", async () => {
    const HomeView = (await import("../../src/views/HomeView.vue")).default;

    const wrapper = mount(HomeView, {
      global: {
        stubs: {
          RouterLink: RouterLinkStub,
        },
      },
    });

    expect(wrapper.findAll("[data-impact-card]").length).toBe(4);
    expect(wrapper.text()).toContain("Plastic Bottle");
    expect(wrapper.text()).toContain("Aluminum Can");
    expect(wrapper.text()).toContain("Cardboard Box");
    expect(wrapper.text()).toContain("Glass Bottle");
    expect(wrapper.text()).toContain("-0.08 kg CO2e");
    expect(wrapper.text()).toContain("Estimated Weight");
    expect(wrapper.text()).toContain("Carbon Reduction");
    expect(wrapper.text()).toContain("Carbon Points");
    expect(wrapper.find("[data-map-card]").exists()).toBe(true);
    expect(wrapper.text()).toContain("Campus Green Hub");
  });

  it("renders the recycling bin audit sequence and audit trust points", async () => {
    const HomeView = (await import("../../src/views/HomeView.vue")).default;

    const wrapper = mount(HomeView, {
      global: {
        stubs: {
          RouterLink: RouterLinkStub,
        },
      },
    });

    expect(wrapper.find("[data-shared-bottle]").exists()).toBe(true);
    expect(wrapper.find("[data-audit-bin]").exists()).toBe(true);
    expect(wrapper.find("[data-audit-panel]").exists()).toBe(true);
    expect(wrapper.find("[data-audit-verified]").exists()).toBe(true);
    expect(wrapper.find("[data-audit-leaves]").exists()).toBe(true);
    expect(wrapper.text()).toContain("Verifies the item is sorted into the correct recycling stream.");
    expect(wrapper.text()).toContain("Records verified impact into the user carbon ledger.");
    expect(wrapper.text()).toContain("Recycle");
  });
});
