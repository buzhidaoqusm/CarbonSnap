import { asResponse } from "../helpers/fetch.js";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const authApi = vi.hoisted(() => ({
  fetchCurrentUser: vi.fn(),
  loginUser: vi.fn(),
  registerUser: vi.fn(),
}));

vi.mock("../../src/api/auth/auth.js", () => authApi);

let clearCurrentToasts = null;

async function loadAuthAndToast() {
  vi.resetModules();
  const [authModule, toastModule] = await Promise.all([
    import("../../src/composables/useAuth.js"),
    import("../../src/composables/useToast.js"),
  ]);
  return {
    useAuth: authModule.useAuth,
    toasts: toastModule.toasts,
    clearAllToasts: toastModule.clearAllToasts,
  };
}

describe("useAuth", () => {
  beforeEach(() => {
    localStorage.clear();
    authApi.loginUser.mockResolvedValue(asResponse({
      access_token: "token-123",
      user: { id: 1, username: "Alice" },
    }));
    authApi.registerUser.mockResolvedValue(asResponse({
      access_token: "token-456",
      user: { id: 2, username: "Bob" },
    }));
    authApi.fetchCurrentUser.mockResolvedValue(asResponse({ user: { id: 1, username: "Alice" } }));
  });

  afterEach(() => {
    clearCurrentToasts?.();
    clearCurrentToasts = null;
    localStorage.clear();
    vi.clearAllMocks();
  });

  it("shows global toasts for login, register, and logout", async () => {
    const { useAuth, toasts } = await loadAuthAndToast();
    const toastModule = await import("../../src/composables/useToast.js");
    clearCurrentToasts = toastModule.clearAllToasts;
    const auth = useAuth();

    await auth.login("alice@example.com", "Password1!");
    expect(toasts.value[0]).toMatchObject({ type: "success", title: "Signed in" });

    auth.logout();
    expect(toasts.value[0]).toMatchObject({ type: "success", title: "Signed out" });

    await auth.register("Bob", "bob@example.com", "Password1!");
    expect(toasts.value[0]).toMatchObject({ type: "success", title: "Account created" });
  });
});
