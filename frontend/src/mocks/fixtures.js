/** Static mock payloads for VITE_USE_MOCK development. */

export const mockUser = {
  id: 1,
  username: "mock_user",
  email: "mock@carbonsnap.local",
  avatar_url: null,
};

export const mockForumPostsPage = {
  items: [
    {
      id: 101,
      author_id: 1,
      title: "[Crowdfunding] Community solar-powered bins — phase 2",
      content:
        "We're raising funds to deploy more smart recycling bins. Discuss scope and budget. This is mock data when VITE_USE_MOCK is on.",
      image_urls_json: JSON.stringify([
        "https://images.unsplash.com/photo-1532996122724-e3c354a0b15b?w=600&q=80",
      ]),
      status: "published",
      created_at: new Date().toISOString(),
      co2_saved_kg: 2.4,
      reward_points: 25,
      like_count: 12,
      liked_by_user: false,
    },
    {
      id: 102,
      author_id: 2,
      title: "Upcycled parts workshop",
      content: "Weekend hands-on: small shelves from reclaimed materials.",
      image_urls_json: null,
      status: "published",
      created_at: new Date().toISOString(),
      co2_saved_kg: 1.8,
      reward_points: 20,
      like_count: 5,
      liked_by_user: false,
    },
  ],
  total: 2,
  page: 1,
  per_page: 20,
};

export const mockForumPost101 = {
  id: 101,
  author_id: 1,
  title: "[Crowdfunding] Community solar-powered bins — phase 2",
  content:
    "We're raising funds to deploy more smart recycling bins. Discuss scope and budget.\n\n(Mock data)",
  image_urls_json: JSON.stringify([
    "https://images.unsplash.com/photo-1532996122724-e3c354a0b15b?w=800&q=80",
  ]),
  status: "published",
  created_at: new Date().toISOString(),
  co2_saved_kg: 2.4,
  reward_points: 25,
  like_count: 12,
  liked_by_user: false,
};

export const mockForumComments = {
  items: [
    {
      id: 501,
      post_id: 101,
      user_id: 2,
      parent_comment_id: null,
      content: "Can you share a rough budget breakdown?",
      status: "published",
      created_at: new Date().toISOString(),
      like_count: 2,
      liked_by_user: false,
    },
  ],
  total: 1,
  page: 1,
  per_page: 50,
};

export const mockMarketItemsPage = {
  items: [
    {
      id: 201,
      seller_id: 3,
      title: "Recycled plastic organizer",
      description: "Lightweight, gently used.",
      image_urls_json: JSON.stringify([
        "https://images.unsplash.com/photo-1581578731548-c64695cc6952?w=600&q=80",
      ]),
      price_points: 80,
      status: "active",
      created_at: new Date().toISOString(),
    },
    {
      id: 202,
      seller_id: 4,
      title: "Bamboo utensil set",
      description: "From a local maker.",
      image_urls_json: JSON.stringify([
        "https://images.unsplash.com/photo-1556910103-1c02745aae4d?w=600&q=80",
      ]),
      price_points: 120,
      status: "active",
      created_at: new Date().toISOString(),
    },
    {
      id: 203,
      seller_id: 2,
      title: "Used book — sustainable design",
      description: "English edition, no missing pages.",
      image_urls_json: null,
      price_points: 45,
      status: "active",
      created_at: new Date().toISOString(),
    },
  ],
  total: 3,
  page: 1,
  per_page: 20,
};

export const mockMarketItem = (id) => {
  const found = mockMarketItemsPage.items.find((i) => i.id === Number(id));
  if (found) {
    return { ...found };
  }
  return mockMarketItemsPage.items[0];
};

export const mockOrdersPage = {
  items: [
    {
      id: 901,
      item_id: 201,
      buyer_id: 1,
      seller_id: 3,
      price_points: 80,
      status: "paid",
      created_at: new Date().toISOString(),
    },
  ],
  total: 1,
  page: 1,
  per_page: 20,
};

export const mockLedgerSummary = {
  total_carbon_amount: 12.5,
  current_points: 340,
};

export const mockLedgerGamification = {
  level: 4,
  level_title: "Green walker",
  xp_in_level: 40,
  xp_to_next: 100,
  total_carbon_amount: 12.5,
  current_points: 340,
  score: 465,
  badges: [
    { id: "first_step", name: "First step", description: "Logged your first carbon-saving record" },
    { id: "forum_voice", name: "Forum voice", description: "Posted in the crowdfunding forum" },
  ],
};
