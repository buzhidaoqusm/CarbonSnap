import { asResponse } from "../helpers/fetch.js";
import { computed, defineComponent, nextTick, ref } from "vue";
import { mount } from "@vue/test-utils";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const notificationApi = {
  fetchNotifications: vi.fn(),
  fetchUnreadNotificationCount: vi.fn(),
  markNotificationRead: vi.fn(),
};

let authState;

vi.mock("../../src/api/notification/notification.js", () => notificationApi);
vi.mock("../../src/composables/useAuth.js", () => ({
  useAuth: () => authState,
}));

const flushPromises = async () => {
  await Promise.resolve();
  await nextTick();
};

async function loadComposable() {
  vi.resetModules();
  const module = await import("../../src/composables/useNotifications.js");
  return module.useNotifications;
}

function createHarness(useNotifications) {
  return defineComponent({
    name: "NotificationsHarness",
    setup() {
      return useNotifications();
    },
    template: '<div data-notifications-harness />',
  });
}

describe("useNotifications", () => {
  let addEventListenerSpy;
  let removeEventListenerSpy;
  let setIntervalSpy;
  let clearIntervalSpy;

  beforeEach(() => {
    const token = ref("token-123");
    const isLoggedIn = computed(() => Boolean(token.value));
    authState = {
      token,
      isLoggedIn,
    };

    notificationApi.fetchNotifications.mockResolvedValue(asResponse({
      items: [],
      total: 0,
      unread_count: 0,
    }));
    notificationApi.fetchUnreadNotificationCount.mockResolvedValue(asResponse({ unread_count: 0 }));
    notificationApi.markNotificationRead.mockResolvedValue(asResponse({ ok: true }));

    addEventListenerSpy = vi.spyOn(window, "addEventListener");
    removeEventListenerSpy = vi.spyOn(window, "removeEventListener");
    setIntervalSpy = vi.spyOn(window, "setInterval");
    clearIntervalSpy = vi.spyOn(window, "clearInterval");
  });

  afterEach(() => {
    vi.clearAllMocks();
    vi.restoreAllMocks();
    vi.useRealTimers();
  });

  it("boots with a baseline fetch, suppresses historical toasts, and uses the fixed recent window", async () => {
    notificationApi.fetchNotifications
      .mockResolvedValueOnce(asResponse({
        items: [
          {
            id: 1,
            title: "Existing",
            body: "Seed",
            source_url: "/notification",
            is_read: false,
            created_at: "2026-04-09T10:00:00Z",
          },
        ],
        total: 1,
        unread_count: 1,
      }))
      .mockResolvedValueOnce(asResponse({
        items: [
          {
            id: 2,
            title: "New",
            body: "Arrived",
            source_url: "/notification",
            is_read: false,
            created_at: "2026-04-09T10:01:00Z",
          },
          {
            id: 1,
            title: "Existing",
            body: "Seed",
            source_url: "/notification",
            is_read: false,
            created_at: "2026-04-09T10:00:00Z",
          },
        ],
        total: 2,
        unread_count: 2,
      }));
    notificationApi.fetchUnreadNotificationCount
      .mockResolvedValueOnce(asResponse({ unread_count: 1 }))
      .mockResolvedValueOnce(asResponse({ unread_count: 2 }));

    const useNotifications = await loadComposable();
    const Harness = createHarness(useNotifications);
    const wrapper = mount(Harness);

    const state = wrapper.vm;
    await state.start();
    await flushPromises();

    expect(notificationApi.fetchUnreadNotificationCount).toHaveBeenCalledWith("token-123");
    expect(notificationApi.fetchNotifications).toHaveBeenCalledWith({
      page: 1,
      perPage: 50,
      unreadOnly: false,
      token: "token-123",
    });
    expect(state.unreadCount).toBe(1);
    expect(state.notifications).toHaveLength(1);
    expect(state.toasts).toHaveLength(0);
    expect(addEventListenerSpy).toHaveBeenCalledWith("focus", expect.any(Function));
    expect(setIntervalSpy).toHaveBeenCalledWith(expect.any(Function), 20000);

    await state.refresh();
    await flushPromises();

    expect(state.notifications).toHaveLength(2);
    expect(state.toasts).toHaveLength(1);
    expect(state.toasts[0].id).toBe(2);
  });

  it("updates local read state and cleans up polling listeners", async () => {
    notificationApi.fetchNotifications.mockResolvedValue(asResponse({
      items: [
        {
          id: 7,
          title: "Project complete",
          body: "Done",
          source_url: "/project",
          is_read: false,
          created_at: "2026-04-09T10:02:00Z",
        },
      ],
      total: 1,
      unread_count: 1,
    }));
    notificationApi.fetchUnreadNotificationCount.mockResolvedValue(asResponse({ unread_count: 1 }));
    notificationApi.markNotificationRead.mockResolvedValue(asResponse({ ok: true }));

    const useNotifications = await loadComposable();
    const Harness = createHarness(useNotifications);
    const wrapper = mount(Harness);
    const state = wrapper.vm;

    await state.start();
    await flushPromises();

    const target = await state.openNotification(state.notifications[0]);
    await flushPromises();

    expect(target).toBe("/project");
    expect(notificationApi.markNotificationRead).toHaveBeenCalledWith(7, "token-123");
    expect(state.unreadCount).toBe(0);
    expect(state.notifications[0].is_read).toBe(true);

    state.stop();

    expect(clearIntervalSpy).toHaveBeenCalled();
    expect(removeEventListenerSpy).toHaveBeenCalledWith("focus", expect.any(Function));
    expect(state.notifications).toHaveLength(0);
    expect(state.toasts).toHaveLength(0);
  });
});
