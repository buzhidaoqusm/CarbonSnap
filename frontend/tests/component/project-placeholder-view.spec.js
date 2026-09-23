import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";
import ProjectPlaceholderView from "../../src/views/project/ProjectPlaceholderView.vue";

const RouterLinkStub = {
  props: ["to"],
  template: '<a :href="typeof to === \'string\' ? to : \'#\'" :data-to="to"><slot /></a>',
};

describe("ProjectPlaceholderView", () => {
  it("renders the zip-inspired projects page structure and links", () => {
    const wrapper = mount(ProjectPlaceholderView, {
      global: {
        stubs: {
          RouterLink: RouterLinkStub,
        },
      },
    });

    // The sidebar and bottom nav moved into the shared AppHeader shell.
    expect(wrapper.find("[data-project-main]").exists()).toBe(true);
    expect(wrapper.find("[data-project-header]").exists()).toBe(true);
    expect(wrapper.find("[data-project-grid]").exists()).toBe(true);
    expect(wrapper.find("[data-project-featured]").exists()).toBe(true);
    expect(wrapper.find("[data-project-secondary]").exists()).toBe(true);
    expect(wrapper.find("[data-project-timeline]").exists()).toBe(true);

    expect(wrapper.text()).toContain("Community Projects");
    expect(wrapper.text()).toContain("Local Reforestation: Amazon Edge");
    expect(wrapper.text()).toContain("Ocean Plastic Cleanup: Great Pacific");
    expect(wrapper.text()).toContain("Project Updates");
    expect(wrapper.text()).toContain("Upcoming Projects");
    expect(wrapper.text()).toContain("Contribute Carbon Credits");
    expect(wrapper.text()).toContain("Join Project");

    expect(wrapper.find('[data-to="/project"]').exists()).toBe(true);
    expect(wrapper.find('[data-to="/ai"]').exists()).toBe(true);
    // /notification and /ledger now live in the avatar menu, not the top bar.
    expect(wrapper.find('[data-to="/forum"]').exists()).toBe(true);
    expect(wrapper.find('[data-to="/market"]').exists()).toBe(true);
    expect(wrapper.find("[data-app-shell-avatar-link]").exists()).toBe(true);
  });
});
