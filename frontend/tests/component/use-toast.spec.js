import { describe, expect, it, vi, afterEach } from "vitest";

async function loadToast() {
  vi.resetModules();
  return import("../../src/composables/useToast.js");
}

describe("useToast", () => {
  afterEach(() => {
    vi.useRealTimers();
  });

  it("shows, dismisses, and clears global toasts by kind", async () => {
    vi.useFakeTimers();
    const {
      clearAllToasts,
      dismissToast,
      dismissToastsByKind,
      showSuccessToast,
      showToast,
      toasts,
    } = await loadToast();

    const successId = showSuccessToast("Saved", "Your changes are live.");
    showToast({ id: 7, kind: "notification", title: "New notification", body: "Arrived" });

    expect(toasts.value).toHaveLength(2);
    expect(toasts.value[0]).toMatchObject({ id: 7, kind: "notification" });
    expect(toasts.value[1]).toMatchObject({ id: successId, type: "success" });

    dismissToast(successId);
    expect(toasts.value).toHaveLength(1);

    dismissToastsByKind("notification");
    expect(toasts.value).toHaveLength(0);

    showSuccessToast("Auto dismiss");
    await vi.advanceTimersByTimeAsync(6000);
    expect(toasts.value).toHaveLength(0);

    clearAllToasts();
  });
});
