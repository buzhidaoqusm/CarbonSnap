import { asResponse } from "../helpers/fetch.js";
import { defineComponent, h, nextTick } from "vue";
import { mount } from "@vue/test-utils";
import { afterEach, describe, expect, it, vi } from "vitest";

vi.mock("../../src/api/market/market.js", () => ({
  createMarketItem: vi.fn(),
  fetchMarketItems: vi.fn(),
  fetchMyOrders: vi.fn(),
  parseMarketImageUrls: vi.fn(() => []),
}));

vi.mock("../../src/api/forum/forum.js", () => ({
  uploadForumImage: vi.fn(),
}));

vi.mock("../../src/composables/useAuth.js", () => ({
  useAuth: () => ({
    token: { value: "token-123" },
    user: { value: { username: "Alice", avatar_url: "", id: 1, current_points: 1240 } },
    isLoggedIn: { value: true },
  }),
}));

vi.mock("vue-router", async () => {
  const actual = await vi.importActual("vue-router");
  return {
    ...actual,
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

describe("MarketExploreView", () => {
  afterEach(() => {
    vi.clearAllMocks();
  });

  it("loads the zip-style market page with token-aware fetches", async () => {
    const { fetchMarketItems, fetchMyOrders } = await import("../../src/api/market/market.js");
    const MarketExploreView = (await import("../../src/views/market/MarketExploreView.vue")).default;

    fetchMarketItems.mockResolvedValue(asResponse({
      items: [
        {
          id: 1,
          title: "Bottle lamp",
          description: "Made from reused plastic.",
          price_points: 42.5,
          seller_id: 3,
          image_urls_json: "[]",
        },
      ],
      total: 1,
      page: 1,
      per_page: 24,
    }));
    fetchMyOrders.mockResolvedValue(asResponse({
      items: [],
      total: 0,
    }));

    const wrapper = mount(MarketExploreView, {
      global: {
        stubs: {
          RouterLink: RouterLinkStub,
        },
      },
    });

    await flushPromises();
    await flushPromises();

    expect(fetchMarketItems).toHaveBeenCalledWith(
      expect.objectContaining({
        page: 1,
        perPage: 12,
        token: "token-123",
      }),
    );
    expect(fetchMyOrders).toHaveBeenCalledWith(
      expect.objectContaining({
        page: 1,
        perPage: 3,
        role: "all",
        token: "token-123",
      }),
    );
    expect(wrapper.find("[data-market-explore-page]").exists()).toBe(true);
    expect(wrapper.find("[data-market-grid]").exists()).toBe(true);
    expect(wrapper.text()).toContain("Green Market");
    expect(wrapper.text()).toContain("Trending Recycled Assets");
    expect(wrapper.text()).toContain("Transfer History");
    expect(wrapper.text()).toContain("Bottle lamp");
    expect(wrapper.text()).toContain("Acquire Asset");
  });

  it("falls back to the public market feed when the token-aware request fails", async () => {
    const { fetchMarketItems, fetchMyOrders } = await import("../../src/api/market/market.js");
    const MarketExploreView = (await import("../../src/views/market/MarketExploreView.vue")).default;

    fetchMarketItems
      .mockRejectedValueOnce(new Error("Request failed (500)"))
      .mockResolvedValueOnce(asResponse({
        items: [
          {
            id: 9,
            title: "Recovered alloy frame",
            description: "Public fallback listing",
            price_points: 18,
            seller_id: 4,
            image_urls_json: "[]",
          },
        ],
        total: 1,
        page: 1,
        per_page: 24,
      }));
    fetchMyOrders.mockResolvedValue(asResponse({
      items: [],
      total: 0,
    }));

    const wrapper = mount(MarketExploreView, {
      global: {
        stubs: {
          RouterLink: RouterLinkStub,
        },
      },
    });

    await flushPromises();
    await flushPromises();

    expect(fetchMarketItems).toHaveBeenNthCalledWith(
      1,
      expect.objectContaining({
        page: 1,
        perPage: 12,
        token: "token-123",
      }),
    );
    expect(fetchMarketItems).toHaveBeenNthCalledWith(
      2,
      expect.objectContaining({
        page: 1,
        perPage: 12,
      }),
    );
    expect(wrapper.text()).toContain("Recovered alloy frame");
    expect(wrapper.text()).not.toContain("Request failed (500)");
  });
});
