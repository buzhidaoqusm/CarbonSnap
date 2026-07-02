import { computed, nextTick, ref } from "vue";
import { mount } from "@vue/test-utils";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

let authState;
let notificationsState;
const routerPush = vi.fn();

vi.mock("../../src/composables/useAuth.js", () => ({
  useAuth: () => authState,
}));
vi.mock("../../src/composables/useNotifications.js", () => ({
  useNotifications: () => notificationsState,
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

const RouterLinkStub = {
  name: "RouterLinkStub",
  props: {
    to: {
      type: [String, Object],
      required: true,
    },
  },
  template: '<a :href="typeof to === \'string\' ? to : \'#\'"><slot /></a>',
};

const flushPromises = async () => {
  await Promise.resolve();
  await nextTick();
};

describe("NotificationCenterView", () => {
  beforeEach(() => {
    const token = ref("token-123");
    authState = {
      isLoggedIn: computed(() => !!token.value),
      token,
      user: ref({
        username: "Mina",
        avatar_url: "",
        current_points: 1240,
      }),
    };

    notificationsState = {
      notifications: ref([
        {
          id: 1,
          title: "Forum reply",
          body: "A discussion moved forward.",
          event_type: "comment_replied",
          source_type: "forum_comment",
          source_id: 8,
          source_url: "/forum/posts/8#comment-8",
          created_at: "2026-03-31T09:00:00Z",
          is_read: false,
        },
        {
          id: 2,
          title: "Order shipped",
          body: "A buyer order is on the way.",
          event_type: "order_shipped",
          source_type: "order",
          source_id: 44,
          source_url: "/market/orders",
          created_at: "2026-03-31T10:00:00Z",
          is_read: true,
        },
      ]),
      unreadCount: computed(() => 1),
      openNotification: vi.fn(async (notification) => notification.source_url || "/notification"),
    };
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  it("renders the stitched notification stream and keeps targets actionable", async () => {
    const NotificationCenterView = (await import("../../src/views/notification/NotificationCenterView.vue")).default;

    const wrapper = mount(NotificationCenterView, {
      global: {
        stubs: {
          RouterLink: RouterLinkStub,
        },
      },
    });

    await flushPromises();
    await flushPromises();

    expect(wrapper.find("[data-notification-hero]").exists()).toBe(true);
    expect(wrapper.find("[data-notification-list]").exists()).toBe(true);
    expect(wrapper.text()).toContain("Activity Stream");
    expect(wrapper.text()).toContain("Live Updates");
    expect(wrapper.text()).toContain("Preferences");
    expect(wrapper.text()).toContain("Forum reply");
    expect(wrapper.text()).toContain("Order shipped");
    const cards = wrapper.findAll("[data-notification-card]");
    expect(cards).toHaveLength(2);

    const firstCard = cards.find((node) => node.text().includes("Forum reply"));
    expect(firstCard?.exists()).toBe(true);
    await firstCard.trigger("click");
    await flushPromises();

    expect(notificationsState.openNotification).toHaveBeenCalledWith(
      expect.objectContaining({
        id: 1,
        source_url: "/forum/posts/8#comment-8",
      }),
    );
    expect(routerPush).toHaveBeenCalledWith("/forum/posts/8#comment-8");

    const secondCard = cards.find((node) => node.text().includes("Order shipped"));
    expect(secondCard?.exists()).toBe(true);
    await secondCard.trigger("click");
    await flushPromises();

    expect(routerPush).toHaveBeenCalledWith("/market/orders");
  });

  it("shows the stitched preferences column for signed-in users", async () => {
    const NotificationCenterView = (await import("../../src/views/notification/NotificationCenterView.vue")).default;

    const wrapper = mount(NotificationCenterView, {
      global: {
        stubs: {
          RouterLink: RouterLinkStub,
        },
      },
    });

    await flushPromises();
    await flushPromises();

    expect(wrapper.text()).toContain("Push Notifications");
    expect(wrapper.text()).toContain("Email Digest");
    expect(wrapper.text()).toContain("Alert Types");
    expect(wrapper.text()).not.toContain("Manage All Alerts");
    expect(wrapper.text()).not.toContain("Instant Verification");
    expect(wrapper.text()).not.toContain("Ultra-Fast Snap");
  });
});
