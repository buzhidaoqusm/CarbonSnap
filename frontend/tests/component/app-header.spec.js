import { mount } from "@vue/test-utils";
import { computed, ref } from "vue";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { routeLocationKey, routerKey } from "vue-router";

let authState;
let notificationsState;

vi.mock("../../src/composables/useAuth.js", () => ({
  useAuth: () => authState,
}));
vi.mock("../../src/composables/useNotifications.js", () => ({
  useNotifications: () => notificationsState,
}));

const RouterLinkStub = {
  name: "RouterLinkStub",
  props: {
    to: {
      type: [String, Object],
      required: true,
    },
  },
  template: '<a :href="typeof to === \'string\' ? to : \'#\'" :data-to="to"><slot /></a>',
};

describe("AppHeader", () => {
  let routerPush;

  beforeEach(() => {
    window.localStorage.clear();
    routerPush = vi.fn();
    authState = {
      logout: vi.fn(),
    };
    notificationsState = {
      unreadCount: computed(() => 0),
    };
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  it("opens the avatar menu for signed-in users and removes hidden top-level nav items", async () => {
    const AppHeader = (await import("../../src/components/common/AppHeader.vue")).default;

    const wrapper = mount(AppHeader, {
      props: {
        isAuthenticated: true,
        avatarAlt: "Ava",
      },
      global: {
        provide: {
          [routeLocationKey]: ref({ path: "/forum" }),
          [routerKey]: { push: routerPush },
        },
        stubs: {
          RouterLink: RouterLinkStub,
        },
      },
    });

    expect(wrapper.find('[data-app-shell-nav-item="ledger"]').exists()).toBe(false);
    expect(wrapper.find('[data-app-shell-nav-item="market"]').exists()).toBe(false);
    expect(wrapper.find('[data-app-shell-nav-item="project"]').text()).toContain("Project");

    await wrapper.find("[data-app-shell-avatar-link] button").trigger("click");

    const menuItems = wrapper.findAll("[data-app-shell-avatar-action]");
    expect(menuItems).toHaveLength(4);
    expect(wrapper.find('[data-app-shell-avatar-action="profile"]').text()).toContain("Profile");
    expect(wrapper.find('[data-app-shell-avatar-action="ledger"]').text()).toContain("Ledger");
    expect(wrapper.find('[data-app-shell-avatar-action="notification"]').text()).toContain("Notifications");
    expect(wrapper.find('[data-app-shell-avatar-action="logout"]').text()).toContain("Log out");

    await wrapper.find('[data-app-shell-avatar-action="profile"]').trigger("click");
    expect(routerPush).toHaveBeenCalledWith("/profile");
  });

  it("logs out and redirects to login from the avatar menu", async () => {
    const AppHeader = (await import("../../src/components/common/AppHeader.vue")).default;

    const wrapper = mount(AppHeader, {
      props: {
        isAuthenticated: computed(() => true),
        avatarAlt: "Ava",
      },
      global: {
        provide: {
          [routeLocationKey]: ref({ path: "/profile" }),
          [routerKey]: { push: routerPush },
        },
        stubs: {
          RouterLink: RouterLinkStub,
        },
      },
    });

    await wrapper.find("[data-app-shell-avatar-link] button").trigger("click");
    await wrapper.find('[data-app-shell-avatar-action="logout"]').trigger("click");

    expect(authState.logout).toHaveBeenCalledTimes(1);
    expect(routerPush).toHaveBeenCalledWith("/login");
  });

  it("shows an unread badge on the notifications menu item", async () => {
    notificationsState = {
      unreadCount: computed(() => 3),
    };

    const AppHeader = (await import("../../src/components/common/AppHeader.vue")).default;

    const wrapper = mount(AppHeader, {
      props: {
        isAuthenticated: true,
        avatarAlt: "Ava",
      },
      global: {
        provide: {
          [routeLocationKey]: ref({ path: "/forum" }),
          [routerKey]: { push: routerPush },
        },
        stubs: {
          RouterLink: RouterLinkStub,
        },
      },
    });

    await wrapper.find("[data-app-shell-avatar-link] button").trigger("click");

    const notificationAction = wrapper.find('[data-app-shell-avatar-action="notification"]');
    expect(notificationAction.exists()).toBe(true);
    expect(notificationAction.text()).toContain("Notifications");
    expect(wrapper.find("[data-app-shell-notification-badge]").text()).toBe("3");
  });

  it("switches header navigation labels between English and Chinese", async () => {
    const AppHeader = (await import("../../src/components/common/AppHeader.vue")).default;

    const wrapper = mount(AppHeader, {
      props: {
        isAuthenticated: true,
        avatarAlt: "Ava",
      },
      global: {
        provide: {
          [routeLocationKey]: ref({ path: "/forum" }),
          [routerKey]: { push: routerPush },
        },
        stubs: {
          RouterLink: RouterLinkStub,
        },
      },
    });

    expect(wrapper.find('[data-app-shell-nav-item="forum"]').text()).toContain("Forum");
    expect(wrapper.find('[data-app-shell-nav-item="project"]').text()).toContain("Project");

    await wrapper.find("[data-app-shell-language-toggle]").trigger("click");

    expect(wrapper.find('[data-app-shell-nav-item="forum"]').text()).toContain("论坛");
    expect(window.localStorage.getItem("cs_locale")).toBe("zh");
  });
});
