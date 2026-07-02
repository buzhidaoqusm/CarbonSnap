import { computed, ref, nextTick } from "vue";
import { mount } from "@vue/test-utils";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const authState = {
  isLoggedIn: computed(() => true),
  token: ref("token-123"),
  user: ref({
    username: "Alice",
    avatar_url: "",
    current_points: 124,
    id: 7,
  }),
  updateUser: vi.fn(),
};

vi.mock("../../src/api/ledger/ledger.js", () => ({
  fetchLedgerGamification: vi.fn(),
  fetchLedgerRecords: vi.fn(),
  fetchLedgerSummary: vi.fn(),
  fetchLedgerTransactions: vi.fn(),
}));

vi.mock("../../src/composables/useAuth.js", () => ({
  useAuth: () => authState,
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

describe("LedgerView", () => {
  beforeEach(() => {
    HTMLCanvasElement.prototype.getContext = vi.fn(() => ({
      beginPath: vi.fn(),
      arc: vi.fn(),
      closePath: vi.fn(),
      createLinearGradient: vi.fn(() => ({
        addColorStop: vi.fn(),
      })),
      fill: vi.fn(),
      fillRect: vi.fn(),
      fillText: vi.fn(),
      lineTo: vi.fn(),
      moveTo: vi.fn(),
      quadraticCurveTo: vi.fn(),
    }));
    HTMLCanvasElement.prototype.toDataURL = vi.fn(() => "data:image/png;base64,ledger-card");
  });

  afterEach(() => {
    vi.clearAllMocks();
    authState.isLoggedIn = computed(() => true);
    authState.token.value = "token-123";
    authState.user.value = {
      username: "Alice",
      avatar_url: "",
      current_points: 124,
      id: 7,
    };
    authState.updateUser = vi.fn();
  });

  it("renders the stitched ledger dashboard for signed-in users", async () => {
    const {
      fetchLedgerGamification,
      fetchLedgerRecords,
      fetchLedgerSummary,
      fetchLedgerTransactions,
    } = await import("../../src/api/ledger/ledger.js");
    const LedgerView = (await import("../../src/views/ledger/LedgerView.vue")).default;

    fetchLedgerSummary.mockResolvedValue({
      current_points: 124,
      total_points_earned: 320,
      total_co2_saved_kg: 48.67,
    });
    fetchLedgerGamification.mockResolvedValue({
      level: 6,
      level_title: "Ocean Protector",
      xp_in_level: 40,
      xp_to_next: 80,
      current_points: 124,
      total_points_earned: 320,
      total_carbon_amount: 48.67,
      badges: [
        {
          id: 1,
          name: "Certified Ocean Protector",
          description: "Earned by keeping valuable material out of waste streams.",
        },
        {
          id: 2,
          name: "Green Habit Streak",
          description: "Awarded for sustained, repeatable circular actions.",
        },
      ],
    });
    fetchLedgerTransactions.mockResolvedValue({
      items: [
        {
          id: 9,
          created_at: "2024-01-01T10:00:00.000Z",
          source_type: "forum_post",
          points_delta: 12,
          co2_delta_kg: 1.5,
        },
      ],
    });
    fetchLedgerRecords.mockResolvedValue({
      items: [
        {
          id: 22,
          created_at: "2024-01-03T10:00:00.000Z",
          waste_type: "plastic",
          co2_saved_kg: 2.34,
          carbon_points: 8,
        },
      ],
    });

    const wrapper = mount(LedgerView, {
      global: {
        stubs: {
          RouterLink: RouterLinkStub,
        },
      },
    });

    await flushPromises();
    await flushPromises();

    expect(fetchLedgerSummary).toHaveBeenCalledWith("token-123");
    expect(fetchLedgerGamification).toHaveBeenCalledWith("token-123");
    expect(fetchLedgerTransactions).toHaveBeenCalledWith(
      expect.objectContaining({ page: 1, perPage: 15, token: "token-123" }),
    );
    expect(fetchLedgerRecords).toHaveBeenCalledWith(
      expect.objectContaining({ page: 1, perPage: 15, token: "token-123" }),
    );
    expect(wrapper.find("[data-ledger-hero]").exists()).toBe(true);
    expect(wrapper.find("[data-ledger-categories]").exists()).toBe(true);
    expect(wrapper.find("[data-ledger-badges]").exists()).toBe(true);
    expect(wrapper.find("[data-ledger-transactions]").exists()).toBe(true);
    expect(wrapper.text()).toContain("Personal Green Capital");
    expect(wrapper.text()).toContain("Lifetime Points Earned");
    expect(wrapper.text()).toContain("320");
    expect(wrapper.text()).toContain("60 / 60 trees planted");
    expect(wrapper.text()).toContain("Lifetime Carbon Reduced");
    expect(wrapper.text()).toContain("Impact Categories");
    expect(wrapper.text()).toContain("Current Goal");
    expect(wrapper.text()).toContain("Verified Achievements");
    expect(wrapper.text()).toContain("Ledger Activity");
    expect(wrapper.text()).toContain("Certified Ocean Protector");
    expect(wrapper.text()).toContain("Forum Post");
    expect(wrapper.text()).toContain("12 pts");
    expect(wrapper.text()).not.toContain("Redeem");

    await wrapper.find("[data-ledger-share-trigger]").trigger("click");
    await flushPromises();
    expect(wrapper.text()).toContain("Shareable Ledger Card");
    expect(wrapper.find("[data-ledger-share-modal]").exists()).toBe(true);
    expect(wrapper.find("[data-ledger-share-card] img").attributes("src")).toBe("data:image/png;base64,ledger-card");
  });

  it("shows the signed-out prompt without loading ledger data", async () => {
    authState.isLoggedIn = computed(() => false);
    authState.token.value = "";
    authState.user.value = null;

    const {
      fetchLedgerGamification,
      fetchLedgerRecords,
      fetchLedgerSummary,
      fetchLedgerTransactions,
    } = await import("../../src/api/ledger/ledger.js");
    const LedgerView = (await import("../../src/views/ledger/LedgerView.vue")).default;

    const wrapper = mount(LedgerView, {
      global: {
        stubs: {
          RouterLink: RouterLinkStub,
        },
      },
    });

    await flushPromises();

    expect(fetchLedgerSummary).not.toHaveBeenCalled();
    expect(fetchLedgerGamification).not.toHaveBeenCalled();
    expect(fetchLedgerTransactions).not.toHaveBeenCalled();
    expect(fetchLedgerRecords).not.toHaveBeenCalled();
    expect(wrapper.text()).toContain("Sign in");
    expect(wrapper.text()).toContain("personal green capital");
    expect(wrapper.find('a[href="/login"]').exists()).toBe(true);
  });
});
