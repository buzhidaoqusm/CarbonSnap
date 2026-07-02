import { mount } from "@vue/test-utils";
import { afterEach, describe, expect, it, vi } from "vitest";

describe("NotificationToastStack", () => {
  afterEach(() => {
    vi.clearAllMocks();
  });

  it("renders newest toasts first and emits open and dismiss actions", async () => {
    const NotificationToastStack = (await import("../../src/components/common/NotificationToastStack.vue")).default;

    const wrapper = mount(NotificationToastStack, {
      props: {
        toasts: [
          {
            id: "toast-1",
            title: "Post published",
            body: "Your post is now live.",
            created_at: "2026-04-09T10:04:00Z",
            type: "success",
            icon: "check_circle",
          },
          {
            id: 2,
            title: "New project notification",
            body: "A project finished.",
            created_at: "2026-04-09T10:03:00Z",
            event_type: "project_completed",
          },
          {
            id: 1,
            title: "Older notification",
            body: "Something else happened.",
            created_at: "2026-04-09T10:00:00Z",
            event_type: "post_liked",
          },
        ],
      },
    });

    const cards = wrapper.findAll("[data-notification-toast]");
    expect(cards).toHaveLength(3);
    expect(cards[0].text()).toContain("Post published");
    expect(cards[0].text()).toContain("Your post is now live.");
    expect(cards[1].text()).toContain("New project notification");
    expect(cards[1].text()).toContain("A project finished.");
    expect(cards[2].text()).toContain("Older notification");

    await wrapper.find('[data-notification-toast-open="2"]').trigger("click");
    expect(wrapper.emitted("open")?.[0]?.[0]).toMatchObject({ id: 2, title: "New project notification" });

    await wrapper.find('[data-notification-toast-dismiss="1"]').trigger("click");
    expect(wrapper.emitted("dismiss")?.[0]?.[0]).toBe(1);
  });
});
