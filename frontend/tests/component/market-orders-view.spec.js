import { defineComponent, h, nextTick, ref } from "vue";
import { mount } from "@vue/test-utils";
import { afterEach, describe, expect, it, vi } from "vitest";

vi.mock("../../src/api/market/market.js", () => ({
  cancelMarketOrder: vi.fn(),
  confirmMarketOrder: vi.fn(),
  fetchMyOrders: vi.fn(),
  shipMarketOrder: vi.fn(),
}));

vi.mock("../../src/composables/useAuth.js", () => ({
  useAuth: () => ({
    token: ref("token-123"),
    user: ref({ username: "Alice", avatar_url: "", id: 7 }),
    isLoggedIn: ref(true),
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

describe("MarketOrdersView", () => {
  afterEach(() => {
    vi.clearAllMocks();
  });

  it("loads orders and keeps the transfer actions available", async () => {
    const { cancelMarketOrder, confirmMarketOrder, fetchMyOrders, shipMarketOrder } = await import("../../src/api/market/market.js");
    const MarketOrdersView = (await import("../../src/views/market/MarketOrdersView.vue")).default;

    fetchMyOrders.mockResolvedValue({
      items: [
        {
          id: 1,
          item_id: 10,
          buyer_id: 7,
          seller_id: 99,
          price_points: 42,
          status: "shipped",
          created_at: "2024-01-01T10:00:00.000Z",
        },
        {
          id: 2,
          item_id: 11,
          buyer_id: 7,
          seller_id: 99,
          price_points: 28,
          status: "paid",
          created_at: "2024-01-02T10:00:00.000Z",
        },
        {
          id: 3,
          item_id: 12,
          buyer_id: 99,
          seller_id: 7,
          price_points: 18,
          status: "paid",
          created_at: "2024-01-03T10:00:00.000Z",
        },
      ],
      total: 3,
    });
    shipMarketOrder.mockResolvedValue({ ok: true });
    confirmMarketOrder.mockResolvedValue({ ok: true });
    cancelMarketOrder.mockResolvedValue({ ok: true });

    const wrapper = mount(MarketOrdersView, {
      global: {
        stubs: {
          RouterLink: RouterLinkStub,
        },
      },
    });

    await flushPromises();
    await flushPromises();

    expect(fetchMyOrders).toHaveBeenCalledWith(
      expect.objectContaining({
        page: 1,
        perPage: 50,
        role: "all",
        token: "token-123",
      }),
    );
    expect(wrapper.find("[data-market-orders-overview]").exists()).toBe(true);
    expect(wrapper.find("[data-market-orders-tabs]").exists()).toBe(true);
    expect(wrapper.find("[data-market-order-row]").exists()).toBe(true);
    expect(wrapper.text()).toContain("Transfer History");
    expect(wrapper.text()).toContain("Mark shipped");
    expect(wrapper.text()).toContain("Confirm receipt");
    expect(wrapper.text()).toContain("Cancel order");

    const shipButton = wrapper.findAll("button").find((button) => button.text() === "Mark shipped");
    expect(shipButton).toBeTruthy();
    await shipButton.trigger("click");
    await flushPromises();

    expect(shipMarketOrder).toHaveBeenCalledWith(3, "token-123");
  });
});
