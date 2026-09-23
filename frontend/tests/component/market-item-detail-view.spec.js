import { asResponse } from "../helpers/fetch.js";
import { defineComponent, h, nextTick } from "vue";
import { mount } from "@vue/test-utils";
import { afterEach, describe, expect, it, vi } from "vitest";

vi.mock("../../src/api/market/market.js", () => ({
  fetchMarketItem: vi.fn(),
  fetchMyOrders: vi.fn(),
  placeMarketOrder: vi.fn(),
  parseMarketImageUrls: vi.fn((value) => {
    try {
      return JSON.parse(value || "[]");
    } catch {
      return [];
    }
  }),
  recordMarketLongView: vi.fn(),
}));

vi.mock("../../src/composables/useAuth.js", () => ({
  useAuth: () => ({
    token: { value: "token-123" },
    user: { value: { username: "Alice", avatar_url: "", id: 99 } },
    isLoggedIn: { value: true },
  }),
}));

vi.mock("vue-router", async () => {
  const actual = await vi.importActual("vue-router");
  return {
    ...actual,
    useRoute: () => ({
      params: { id: "8" },
    }),
    useRouter: () => ({
      push: vi.fn(),
    }),
  };
});

const RouterLinkStub = defineComponent({
  name: "RouterLinkStub",
  props: {
    to: {
      type: [String, Object],
      required: true,
    },
  },
  setup(props, { slots, attrs }) {
    return () => h("a", { ...attrs, href: typeof props.to === "string" ? props.to : "#" }, slots.default?.());
  },
});

const flushPromises = async () => {
  await Promise.resolve();
  await nextTick();
};

describe("MarketItemDetailView", () => {
  afterEach(() => {
    vi.useRealTimers();
    vi.clearAllMocks();
  });

  it("loads market detail with token-aware fetch", async () => {
    const { fetchMarketItem, fetchMyOrders } = await import("../../src/api/market/market.js");
    const MarketItemDetailView = (await import("../../src/views/market/MarketItemDetailView.vue")).default;

    fetchMarketItem.mockResolvedValue(asResponse({
      id: 8,
      seller_id: 3,
      title: "Bottle lamp",
      description: "Made from reused plastic.",
      status: "active",
      price_points: 25,
      image_urls_json: "[]",
    }));
    fetchMyOrders.mockResolvedValue(asResponse({
      items: [],
      total: 0,
    }));

    const wrapper = mount(MarketItemDetailView, {
      global: {
        stubs: {
          RouterLink: RouterLinkStub,
        },
      },
    });

    await flushPromises();
    await flushPromises();

    expect(fetchMarketItem).toHaveBeenCalledWith("8", "token-123");
    expect(fetchMyOrders).toHaveBeenCalledWith(
      expect.objectContaining({
        page: 1,
        perPage: 50,
        role: "all",
        token: "token-123",
      }),
    );
    expect(wrapper.find("[data-market-detail-layout]").exists()).toBe(true);
    expect(wrapper.find("[data-market-detail-summary]").exists()).toBe(true);
    expect(wrapper.text()).toContain("Acquire Asset");
    expect(wrapper.text()).toContain("View orders");
    expect(wrapper.text()).toContain("Bottle lamp");

    const acquireButton = wrapper.findAll("button").find((button) => button.text() === "Acquire Asset");
    expect(acquireButton).toBeTruthy();
    await acquireButton.trigger("click");
    await flushPromises();

    const { placeMarketOrder } = await import("../../src/api/market/market.js");
    expect(placeMarketOrder).toHaveBeenCalledWith({ itemId: 8 }, "token-123");
  });

  it("records a market long-view once after the dwell threshold", async () => {
    vi.useFakeTimers();

    const { fetchMarketItem, fetchMyOrders, recordMarketLongView } = await import("../../src/api/market/market.js");
    const MarketItemDetailView = (await import("../../src/views/market/MarketItemDetailView.vue")).default;

    fetchMarketItem.mockResolvedValue(asResponse({
      id: 8,
      seller_id: 3,
      title: "Bottle lamp",
      description: "Made from reused plastic.",
      status: "active",
      price_points: 25,
      image_urls_json: "[]",
    }));
    fetchMyOrders.mockResolvedValue(asResponse({
      items: [],
      total: 0,
    }));
    recordMarketLongView.mockResolvedValue(asResponse({ tracked: true }));

    mount(MarketItemDetailView, {
      global: {
        stubs: {
          RouterLink: RouterLinkStub,
        },
      },
    });

    await flushPromises();
    await flushPromises();

    expect(recordMarketLongView).not.toHaveBeenCalled();

    await vi.advanceTimersByTimeAsync(15000);
    await flushPromises();

    expect(recordMarketLongView).toHaveBeenCalledTimes(1);
    expect(recordMarketLongView).toHaveBeenCalledWith(8, "token-123");
  });
});
