import {
  mockForumComments,
  mockForumPost101,
  mockForumPostsPage,
  mockLedgerGamification,
  mockLedgerSummary,
  mockMarketItem,
  mockMarketItemsPage,
  mockOrdersPage,
  mockUser,
} from "./fixtures.js";

function clone(data) {
  return JSON.parse(JSON.stringify(data));
}

/**
 * Minimal mock router: supports happy-path responses for forum, market, ledger, auth.
 */
export async function resolveMock({ path, method, body }) {
  const p = path.split("?")[0];

  // Auth
  if (method === "POST" && p === "/api/auth/login") {
    return {
      access_token: "mock-jwt-token",
      user: clone(mockUser),
    };
  }
  if (method === "POST" && p === "/api/auth/register") {
    return {
      access_token: "mock-jwt-token",
      user: { ...clone(mockUser), username: body?.username || mockUser.username },
    };
  }
  if (method === "GET" && p === "/api/auth/me") {
    return clone(mockUser);
  }

  // Forum
  if (method === "GET" && p === "/api/forum/posts") {
    return clone(mockForumPostsPage);
  }
  if (method === "GET" && /^\/api\/forum\/posts\/\d+$/.test(p)) {
    const id = Number(p.split("/").pop());
    return id === 101 ? clone(mockForumPost101) : { ...clone(mockForumPost101), id };
  }
  if (method === "POST" && p === "/api/forum/posts") {
    return {
      id: 999,
      author_id: mockUser.id,
      title: body?.title || "New",
      content: body?.content || "",
      image_urls_json: body?.image_urls_json || null,
      status: "published",
      created_at: new Date().toISOString(),
      like_count: 0,
      liked_by_user: false,
    };
  }
  if (method === "PUT" && /^\/api\/forum\/posts\/\d+$/.test(p)) {
    return {
      ...clone(mockForumPost101),
      id: Number(p.split("/").pop()),
      title: body?.title ?? mockForumPost101.title,
      content: body?.content ?? mockForumPost101.content,
    };
  }
  if (method === "DELETE" && /^\/api\/forum\/posts\/\d+$/.test(p)) {
    return {};
  }
  if (method === "GET" && /^\/api\/forum\/posts\/\d+\/comments$/.test(p)) {
    return clone(mockForumComments);
  }
  if (method === "POST" && /^\/api\/forum\/posts\/\d+\/comments$/.test(p)) {
    return {
      id: 888,
      post_id: Number(p.split("/")[4]),
      user_id: mockUser.id,
      parent_comment_id: body?.parent_comment_id ?? null,
      content: body?.content || "",
      status: "published",
      created_at: new Date().toISOString(),
      like_count: 0,
      liked_by_user: false,
    };
  }
  if (method === "DELETE" && /^\/api\/forum\/comments\/\d+$/.test(p)) {
    return {};
  }
  if (method === "POST" && p === "/api/forum/uploads") {
    return { url: "https://images.unsplash.com/photo-1501004318641-b39e6451bec6?w=400&q=80" };
  }
  if (method === "POST" && p === "/api/forum/likes") {
    return { liked: true, like_count: 13 };
  }

  // Market
  if (method === "POST" && p === "/api/market/items") {
    return {
      id: 888,
      seller_id: mockUser.id,
      title: body?.title || "New listing",
      description: body?.description || null,
      image_urls_json: body?.image_urls_json || null,
      price_points: Number(body?.price_points) || 1,
      status: "active",
      created_at: new Date().toISOString(),
    };
  }
  if (method === "DELETE" && /^\/api\/market\/items\/\d+$/.test(p)) {
    return {};
  }
  if (method === "GET" && p === "/api/market/items") {
    return clone(mockMarketItemsPage);
  }
  if (method === "GET" && p === "/api/market/items/mine") {
    return clone(mockMarketItemsPage);
  }
  if (method === "GET" && /^\/api\/market\/items\/\d+$/.test(p)) {
    const id = Number(p.split("/").pop());
    return clone(mockMarketItem(id));
  }
  if (method === "POST" && p === "/api/market/orders") {
    const item = mockMarketItem(body?.item_id);
    return {
      id: 777,
      item_id: item.id,
      buyer_id: mockUser.id,
      seller_id: item.seller_id,
      price_points: item.price_points,
      status: "paid",
      created_at: new Date().toISOString(),
    };
  }
  if (method === "GET" && p === "/api/market/orders") {
    return clone(mockOrdersPage);
  }
  if (method === "PATCH" && /\/api\/market\/orders\/\d+\/(ship|confirm|cancel)$/.test(p)) {
    return { id: 901, status: "shipped" };
  }

  // Ledger
  if (method === "GET" && p === "/api/ledger/summary") {
    return clone(mockLedgerSummary);
  }
  if (method === "GET" && p === "/api/ledger/gamification") {
    return clone(mockLedgerGamification);
  }
  if (method === "GET" && p === "/api/ledger/transactions") {
    return { items: [], total: 0, page: 1, per_page: 20 };
  }
  if (method === "GET" && p === "/api/ledger/records") {
    return { items: [], total: 0, page: 1, per_page: 20 };
  }

  throw new Error(`[mock] Unhandled ${method} ${p}`);
}
