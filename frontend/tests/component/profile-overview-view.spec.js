import { asResponse } from "../helpers/fetch.js";
import { computed, ref, nextTick } from "vue";
import { mount } from "@vue/test-utils";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

let authState;

vi.mock("../../src/composables/useAuth.js", () => ({
  useAuth: () => authState,
}));

vi.mock("../../src/api/auth/auth.js", () => ({
  updateAvatar: vi.fn(),
  updateProfile: vi.fn(),
}));

vi.mock("../../src/api/ledger/ledger.js", () => ({
  fetchLedgerSummary: vi.fn(),
}));

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

describe("ProfileOverviewView", () => {
  beforeEach(() => {
    const token = ref("token-123");
    authState = {
      isLoggedIn: computed(() => !!token.value),
      token,
      user: ref({
        username: "Ava",
        email: "ava@example.com",
        bio: "Testing the stitched profile view.",
        avatar_url: "",
        current_points: 48,
        total_carbon_amount: 12.5,
        created_at: "2024-01-20T10:00:00Z",
        id: 9,
      }),
      refreshCurrentUser: vi.fn().mockResolvedValue(null),
      updateUser: vi.fn(),
    };
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  it("renders the lightweight stitched account overview for signed-in users", async () => {
    const { fetchLedgerSummary } = await import("../../src/api/ledger/ledger.js");
    fetchLedgerSummary.mockResolvedValue(asResponse({
      current_points: 48,
      total_carbon_amount: 12.5,
    }));
    const ProfileOverviewView = (await import("../../src/views/profile/ProfileOverviewView.vue")).default;

    const wrapper = mount(ProfileOverviewView, {
      global: {
        stubs: {
          RouterLink: RouterLinkStub,
        },
      },
    });

    await flushPromises();

    expect(wrapper.find("[data-profile-hero]").exists()).toBe(true);
    expect(wrapper.text()).toContain("Account Overview");
    expect(wrapper.text()).toContain("Ava");
    expect(wrapper.text()).toContain("ava@example.com");
    expect(wrapper.text()).toContain("Testing the stitched profile view.");
    expect(wrapper.text()).toContain("Verified Account Data");
    expect(wrapper.text()).toContain("Username");
    expect(wrapper.text()).toContain("Email");
    expect(wrapper.text()).toContain("Joined");
    expect(wrapper.text()).not.toContain("User ID");
    expect(wrapper.text()).not.toContain("Avatar");
    expect(wrapper.find("[data-profile-bio-summary]").exists()).toBe(true);
    expect(wrapper.find("[data-profile-bio-form]").exists()).toBe(false);
    expect(wrapper.text()).toContain("Edit Bio");
    await wrapper.find("[data-profile-edit-bio]").trigger("click");
    await flushPromises();
    expect(wrapper.find("[data-profile-bio-modal]").exists()).toBe(true);
    expect(wrapper.find("[data-profile-bio-form]").exists()).toBe(true);
    expect(wrapper.text()).toContain("Save Bio");
    expect(wrapper.text()).toContain("Current Points");
    expect(wrapper.text()).toContain("Total Carbon");
    expect(wrapper.find('a[href="/ledger"]').exists()).toBe(true);
    expect(wrapper.find('a[href="/notification"]').exists()).toBe(true);
    expect(wrapper.find("[data-app-shell-avatar-link]").exists()).toBe(true);
  });

  it("shows a signed-out prompt when account data is unavailable", async () => {
    authState = {
      isLoggedIn: computed(() => false),
      token: ref(null),
      user: ref(null),
      refreshCurrentUser: vi.fn().mockResolvedValue(null),
      updateUser: vi.fn(),
    };

    const ProfileOverviewView = (await import("../../src/views/profile/ProfileOverviewView.vue")).default;

    const wrapper = mount(ProfileOverviewView, {
      global: {
        stubs: {
          RouterLink: RouterLinkStub,
        },
      },
    });

    await flushPromises();

    expect(wrapper.text()).toContain("Sign in");
    expect(wrapper.text()).toContain("account summary");
    expect(wrapper.find('a[href="/login"]').exists()).toBe(true);
  });
});
