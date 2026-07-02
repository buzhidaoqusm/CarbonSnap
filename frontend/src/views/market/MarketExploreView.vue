<template>
  <div class="market-shell min-h-screen bg-[#f3f7f5] font-body text-[#2b302f]" data-market-explore-page>
    <AppHeader
      :is-authenticated="isLoggedIn"
      :avatar-alt="avatarAlt"
      :avatar-url="avatarUrl"
      :points-label="`${walletLabel} pts`"
    />

    <div class="flex min-h-screen pt-6">
      <main class="flex-1 px-6 pb-32 md:px-8 md:pb-16 lg:px-10 xl:px-12">
        <div class="mx-auto w-full max-w-7xl">
          <header class="mb-12">
            <h1 class="mb-2 font-headline text-4xl font-extrabold tracking-tight text-on-background md:text-5xl">
              Green Market
            </h1>
            <p class="max-w-2xl text-on-surface-variant">
              Trade recycled assets, manage your circular warehouse, and track the environmental provenance of every item in the ecosystem.
            </p>
          </header>

          <section class="mb-12 grid grid-cols-1 gap-6 md:grid-cols-3">
            <div
              class="relative flex min-h-[240px] flex-col justify-between overflow-hidden rounded-3xl bg-primary p-8 text-on-primary shadow-[0_8px_32px_rgba(43,48,47,0.08)] md:col-span-2"
            >
              <div class="relative z-10">
                <p class="mb-2 text-xs font-bold uppercase tracking-widest text-on-primary/70">
                  Portfolio Balance
                </p>
                <h2 class="font-headline text-5xl font-bold">
                  {{ balanceNumber }}
                  <span class="font-body text-2xl font-normal opacity-80">CO2e</span>
                </h2>
                <div class="mt-4 flex flex-wrap gap-4">
                  <span
                    class="flex items-center gap-1 rounded-full border border-on-primary/30 bg-on-primary/20 px-3 py-1 text-xs font-bold"
                  >
                    <span class="material-symbols-outlined text-sm">trending_up</span>
                    {{ growthLabel }}
                  </span>
                  <span class="flex items-center gap-1 rounded-full bg-on-primary/20 px-3 py-1 text-xs font-bold">
                    <span class="material-symbols-outlined text-sm">savings</span>
                    {{ portfolioUsdEstimate }}
                  </span>
                </div>
              </div>
              <div class="relative z-10 mt-8 flex flex-wrap gap-4">
                <button
                  class="rounded-xl bg-on-primary px-4 py-3 text-sm font-bold text-primary transition-all hover:opacity-90"
                  type="button"
                  @click="goToLedger"
                >
                  Cash Out
                </button>
                <button
                  class="rounded-xl border border-on-primary/30 px-4 py-3 text-sm font-bold text-on-primary transition-all hover:bg-on-primary/10"
                  type="button"
                  @click="goToOrders"
                >
                  Transfer
                </button>
              </div>
              <div class="absolute bottom-0 right-0 h-48 w-48 rounded-full bg-secondary-fixed/20 blur-3xl" />
              <div class="absolute right-6 top-6 rounded-full bg-secondary-fixed p-4 text-[#324600]">
                <span class="material-symbols-outlined text-4xl">account_balance_wallet</span>
              </div>
            </div>

            <div class="flex flex-col justify-between rounded-3xl bg-surface-container p-8">
              <div>
                <p class="mb-6 text-xs font-bold uppercase tracking-widest text-on-surface-variant">
                  Warehouse Status
                </p>
                <div class="space-y-4">
                  <div class="flex items-end justify-between gap-4">
                    <span class="text-sm font-medium">Storage Used</span>
                    <span class="text-sm font-bold">{{ storageUsed }}%</span>
                  </div>
                  <div class="h-3 w-full overflow-hidden rounded-full bg-surface-container-high">
                    <div class="h-full rounded-full bg-primary" :style="{ width: `${storageUsed}%` }" />
                  </div>
                  <p class="text-sm text-on-surface-variant">
                    {{ managedItems }} items currently managed
                  </p>
                </div>
              </div>
              <button
                class="mt-8 flex w-full items-center justify-center gap-2 rounded-xl border border-outline-variant py-3 text-sm font-bold transition-colors hover:bg-surface-container-lowest"
                type="button"
                @click="goToOrders"
              >
                <span class="material-symbols-outlined text-lg">inventory_2</span>
                Open Warehouse
              </button>
            </div>
          </section>

          <div class="mb-8 flex gap-4 overflow-x-auto pb-2">
            <button
              v-for="category in categories"
              :key="category"
              class="whitespace-nowrap rounded-full px-6 py-2 text-sm font-bold transition-colors"
              :class="category === activeCategory ? activeCategoryClass : categoryClass"
              type="button"
              @click="activeCategory = category"
            >
              {{ category }}
            </button>
          </div>

          <section class="mb-16">
            <div class="mb-6 flex items-end justify-between gap-4">
              <h3 class="font-headline text-2xl font-bold">Trending Recycled Assets</h3>
              <RouterLink class="text-sm font-bold text-primary" to="/market/orders">
                View Full Market
                <span class="material-symbols-outlined text-sm">arrow_forward</span>
              </RouterLink>
            </div>

            <div v-if="loading" class="rounded-3xl bg-surface-container-lowest p-8 shadow-[0_8px_32px_rgba(43,48,47,0.04)]">
              Loading items...
            </div>
            <p v-else-if="error" class="rounded-3xl bg-surface-container-lowest p-8 text-error shadow-[0_8px_32px_rgba(43,48,47,0.04)]">
              {{ error }}
            </p>
            <div
              v-else-if="filteredItems.length === 0"
              class="rounded-3xl bg-surface-container-lowest p-8 shadow-[0_8px_32px_rgba(43,48,47,0.04)]"
            >
              No items matched your search.
            </div>
            <div v-else class="grid grid-cols-1 gap-8 sm:grid-cols-2 lg:grid-cols-3" data-market-grid>
              <article
                v-for="item in filteredItems"
                :key="item.id"
                class="group overflow-hidden rounded-3xl border border-transparent bg-surface-container-lowest shadow-[0_8px_32px_rgba(43,48,47,0.04)] transition-all hover:border-primary-container"
              >
                <div class="relative aspect-square overflow-hidden bg-surface-container-low">
                  <img
                    v-if="primaryImage(item)"
                    :alt="item.title"
                    class="h-full w-full object-cover transition-transform duration-500 group-hover:scale-105"
                    :src="primaryImage(item)"
                  />
                  <div v-else class="flex h-full w-full items-center justify-center text-sm text-on-surface-variant">
                    No image
                  </div>
                  <div class="absolute left-4 top-4">
                    <span
                      class="rounded-full px-3 py-1 text-[10px] font-black uppercase tracking-tighter"
                      :class="badgeClass(item)"
                    >
                      {{ badgeLabel(item) }}
                    </span>
                  </div>
                </div>

                <div class="p-6">
                  <div class="mb-2 flex items-start justify-between gap-4">
                    <div>
                      <p class="mb-1 text-xs font-bold uppercase tracking-wider text-on-surface-variant">
                        {{ categoryLabel(item) }}
                      </p>
                      <RouterLink class="block" :to="`/market/items/${item.id}`">
                        <h4 class="font-bold text-lg">{{ item.title }}</h4>
                      </RouterLink>
                    </div>
                    <button
                      class="text-primary transition-transform hover:scale-110"
                      type="button"
                      :aria-label="`Favorite ${item.title}`"
                    >
                      <span class="material-symbols-outlined">favorite</span>
                    </button>
                  </div>

                  <div class="mb-4 flex items-baseline gap-2">
                    <span class="font-headline text-2xl font-bold">{{ priceLabel(item) }}</span>
                    <span class="text-sm font-bold text-primary">CO2 Credits</span>
                    <span class="ml-auto text-xs text-on-surface-variant">{{ usdEstimateLabel(item) }}</span>
                  </div>

                  <div class="border-t border-surface-container-high pt-4">
                    <p class="mb-2 text-[10px] font-bold uppercase text-on-surface-variant">Provenance</p>
                    <div class="flex items-center gap-2">
                      <div class="flex -space-x-2">
                        <div
                          v-for="(tag, index) in provenanceTags(item)"
                          :key="`${item.id}-${tag}`"
                          class="flex h-6 w-6 items-center justify-center rounded-full border-2 border-surface-container-lowest text-[8px] font-bold"
                          :class="provenanceClasses[index]"
                        >
                          {{ tag }}
                        </div>
                      </div>
                      <span class="text-[10px] text-on-surface-variant">{{ provenanceLabel(item) }}</span>
                    </div>
                  </div>

                  <RouterLink
                    class="mt-6 block w-full rounded-xl bg-surface-container-high py-3 text-center text-sm font-bold transition-colors group-hover:bg-primary group-hover:text-on-primary"
                    :to="`/market/items/${item.id}`"
                  >
                    Acquire Asset
                  </RouterLink>
                </div>
              </article>
            </div>
          <!-- Market items pagination -->
          <div v-if="!loading && itemsTotalPages > 1" class="mb-8 flex items-center justify-center gap-2">
            <button
              class="flex h-9 w-9 items-center justify-center rounded-full bg-surface-container text-sm font-bold text-on-surface-variant transition-colors hover:bg-surface-container-high disabled:opacity-40"
              type="button"
              :disabled="!itemsHasPrev"
              @click="itemsPrevPage"
            >
              <span class="material-symbols-outlined text-lg">chevron_left</span>
            </button>
            <template v-for="item in itemsPageItems" :key="item.key">
              <span v-if="item.ellipsis" class="flex h-9 w-9 items-center justify-center text-sm text-on-surface-variant">…</span>
              <button
                v-else
                class="flex h-9 w-9 items-center justify-center rounded-full text-sm font-bold transition-colors"
                :class="item.p === itemsPage ? 'bg-primary text-on-primary shadow-md' : 'bg-surface-container text-on-surface-variant hover:bg-surface-container-high'"
                type="button"
                @click="goToItemsPage(item.p)"
              >
                {{ item.p }}
              </button>
            </template>
            <button
              class="flex h-9 w-9 items-center justify-center rounded-full bg-surface-container text-sm font-bold text-on-surface-variant transition-colors hover:bg-surface-container-high disabled:opacity-40"
              type="button"
              :disabled="!itemsHasNext"
              @click="itemsNextPage"
            >
              <span class="material-symbols-outlined text-lg">chevron_right</span>
            </button>
          </div>
          </section>

          <section class="mb-16">
            <div class="rounded-3xl bg-surface-container-low p-8">
              <div class="mb-8 flex items-center justify-between gap-4">
                <div>
                  <h3 class="font-headline text-2xl font-bold">Transfer History</h3>
                  <p class="text-sm text-on-surface-variant">Recent ledger movements in your circular flow</p>
                </div>
                <button
                  class="rounded-full p-2 transition-colors hover:bg-surface-container"
                  type="button"
                  @click="cycleHistoryRole"
                  aria-label="Filter history"
                >
                  <span class="material-symbols-outlined">filter_list</span>
                </button>
              </div>

              <div class="space-y-4">
                <div
                  v-if="historyLoading && historyRows.length === 0"
                  class="rounded-2xl bg-surface-container-lowest p-4 text-sm text-on-surface-variant"
                >
                  Loading history...
                </div>
                <div
                  v-else-if="historyRows.length === 0"
                  class="rounded-2xl bg-surface-container-lowest p-4 text-sm text-on-surface-variant"
                >
                  No transfer history yet.
                </div>
                <div
                  v-for="row in historyRows"
                  :key="row.key"
                  class="flex items-center justify-between rounded-2xl bg-surface-container-lowest p-4 transition-transform cursor-pointer hover:translate-x-1"
                >
                  <div class="flex items-center gap-4">
                    <div
                      class="flex h-12 w-12 items-center justify-center rounded-xl"
                      :class="row.iconClass"
                    >
                      <span class="material-symbols-outlined">{{ row.icon }}</span>
                    </div>
                    <div>
                      <p class="text-sm font-bold">{{ row.title }}</p>
                      <p class="text-xs text-on-surface-variant">{{ row.subtitle }}</p>
                    </div>
                  </div>
                  <div class="text-right">
                    <p class="font-bold" :class="row.amountClass">{{ row.amount }}</p>
                    <p class="text-[10px] font-bold uppercase tracking-wider text-on-surface-variant">
                      {{ row.status }}
                    </p>
                  </div>
                </div>
              </div>

              <button
                class="mt-8 w-full rounded-xl bg-surface-container-high py-3 text-sm font-bold transition-colors hover:bg-surface-container-highest disabled:cursor-not-allowed disabled:opacity-60"
                type="button"
                :disabled="historyButtonDisabled"
                @click="loadMoreHistory"
              >
                {{ historyLoading ? "Loading..." : "Load More History" }}
              </button>
            </div>
          </section>
        </div>
      </main>
    </div>

    <nav
      class="fixed bottom-0 left-0 z-50 flex w-full items-end justify-around bg-[#f3f7f5]/80 px-4 pb-4 backdrop-blur-lg md:hidden dark:bg-[#121212]/80"
    >
      <button
        v-for="entry in mobileNavEntries"
        :key="entry.label"
        class="flex flex-col items-center justify-center p-2"
        :class="entry.active ? 'text-[#266829] dark:text-[#b9f600]' : 'text-[#585c5b] dark:text-[#aaaeac]'"
        type="button"
        @click="goTo(entry.to)"
      >
        <span class="material-symbols-outlined">{{ entry.icon }}</span>
        <span class="mt-1 font-body text-[10px] font-bold uppercase tracking-widest">{{ entry.label }}</span>
      </button>
    </nav>

    <div class="fixed bottom-24 right-8 hidden md:block">
      <button
        class="flex h-14 w-14 items-center justify-center rounded-full bg-secondary-fixed text-on-secondary-fixed shadow-lg transition-all hover:scale-110 active:scale-90"
        type="button"
        @click="goToAiSnap"
      >
        <span class="material-symbols-outlined text-2xl">add</span>
      </button>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from "vue";
import { RouterLink, useRouter } from "vue-router";

import { fetchMarketItems, fetchMyOrders, parseMarketImageUrls } from "../../api/market/market.js";
import AppHeader from "../../components/common/AppHeader.vue";
import { useAuth } from "../../composables/useAuth.js";

const router = useRouter();
const { isLoggedIn, token, user } = useAuth();

const ITEMS_PER_PAGE = 12;

const items = ref([]);
const itemsTotal = ref(0);
const itemsPage = ref(1);
const loading = ref(false);
const error = ref("");
const searchQuery = ref("");
const activeCategory = ref("All Circular Items");
const historyRole = ref("all");
const historyPage = ref(1);
const historyItems = ref([]);
const historyTotal = ref(0);
const historyLoading = ref(false);
const historyError = ref("");

const categories = [
  "All Circular Items",
  "Industrial Parts",
  "Tech Hardware",
  "Sustainable Textiles",
  "Refurbished Solar",
];

const provenanceClasses = ["bg-primary-container text-[#054e12]", "bg-secondary-container text-[#324600]", "bg-tertiary-container text-[#003840]"];

const sideNavEntries = computed(() => [
  { label: "Ledger", icon: "receipt_long", to: "/ledger", active: false },
  { label: "Projects", icon: "assignment", to: "/project", active: false },
  { label: "Green Market", icon: "storefront", to: "/market", active: true },
  { label: "Notifications", icon: "notifications", to: "/notification", active: false },
  { label: "Settings", icon: "settings", to: "/profile", active: false },
]);

const mobileNavEntries = computed(() => [
  { label: "Ledger", icon: "receipt_long", to: "/ledger", active: false, filled: false },
  { label: "Projects", icon: "assignment", to: "/project", active: false, filled: false },
  { label: "Snap", icon: "photo_camera", to: "/ai", active: true, filled: true },
  { label: "Market", icon: "storefront", to: "/market", active: true, filled: true },
  { label: "Forum", icon: "groups", to: "/forum", active: false, filled: false },
]);

const itemsTotalPages = computed(() => Math.max(1, Math.ceil(itemsTotal.value / ITEMS_PER_PAGE)));
const itemsHasPrev = computed(() => itemsPage.value > 1);
const itemsHasNext = computed(() => itemsPage.value < itemsTotalPages.value);

const itemsPageItems = computed(() => {
  const tp = itemsTotalPages.value;
  const cur = itemsPage.value;
  const pageList = [];
  if (tp <= 7) {
    for (let i = 1; i <= tp; i++) pageList.push({ key: i, p: i, ellipsis: false });
    return pageList;
  }
  const pushPage = (p) => pageList.push({ key: p, p, ellipsis: false });
  const pushEllipsis = (key) => pageList.push({ key, p: null, ellipsis: true });
  pushPage(1);
  if (cur > 3) pushEllipsis("e1");
  const start = Math.max(2, cur - 1);
  const end = Math.min(tp - 1, cur + 1);
  for (let i = start; i <= end; i++) pushPage(i);
  if (cur < tp - 2) pushEllipsis("e2");
  pushPage(tp);
  return pageList;
});

const walletLabel = computed(() => {
  const raw = Number(user.value?.current_points);
  if (Number.isFinite(raw)) {
    return formatWhole(raw);
  }
  return "0";
});

const avatarAlt = computed(() => user.value?.username || "User");
const avatarUrl = computed(() => user.value?.avatar_url || "");
const avatarInitial = computed(() => {
  const source = String(user.value?.username || "U").trim();
  return source ? source.charAt(0).toUpperCase() : "U";
});
const balanceNumber = computed(() => formatCurrency(user.value?.current_points ?? 0));
const portfolioUsdEstimate = computed(() => {
  const points = Number(user.value?.current_points ?? 0);
  if (!Number.isFinite(points) || points <= 0) {
    return "Est. $0.00 USD";
  }
  return `Est. $${(points * 3.65).toFixed(2)} USD`;
});
const growthLabel = computed(() => {
  const rate = Number(user.value?.monthly_growth_rate);
  if (Number.isFinite(rate)) {
    return `${rate >= 0 ? "+" : ""}${rate.toFixed(1)}% this month`;
  }
  return "Growth unavailable";
});
const storageUsed = computed(() => {
  const used = items.value.length === 0 ? 0 : Math.min(100, Math.round((items.value.length / 20) * 100));
  return used;
});
const managedItems = computed(() => items.value.length);
const historyHasMore = computed(() => historyItems.value.length < historyTotal.value);
const historyButtonDisabled = computed(() => historyLoading.value || (!historyHasMore.value && historyItems.value.length > 0));
const activeSideNavClass = "bg-white text-[#266829] shadow-sm";
const sideNavClass = "text-[#585c5b] hover:bg-[#e4e9e7]";
const categoryClass = "bg-surface-container hover:bg-surface-container-high";
const activeCategoryClass = "bg-secondary-fixed text-on-secondary-fixed";

const historyFallback = [
  {
    key: "fallback-1",
    icon: "shopping_bag",
    iconClass: "bg-primary-container/30 text-primary",
    title: "Asset Acquisition: Solar Panel V2",
    subtitle: "Oct 24, 14:22 • From: SolarRenew Ltd.",
    amount: "- 215.10 CO2",
    amountClass: "text-error",
    status: "Completed",
  },
  {
    key: "fallback-2",
    icon: "recycling",
    iconClass: "bg-secondary-container/30 text-secondary",
    title: "Recycling Reward: Heavy Plastics",
    subtitle: "Oct 22, 09:15 • Verified by: EcoHub-4",
    amount: "+ 45.00 CO2",
    amountClass: "text-primary",
    status: "Verified",
  },
  {
    key: "fallback-3",
    icon: "move_up",
    iconClass: "bg-tertiary-container/30 text-tertiary",
    title: "Warehouse Transfer: Metal Scraps",
    subtitle: "Oct 21, 16:45 • To: Central Foundry",
    amount: "+ 128.50 CO2",
    amountClass: "text-primary",
    status: "Pending",
  },
];

const historyRows = computed(() => {
  if (historyItems.value.length === 0 && !historyLoading.value) {
    return historyFallback;
  }
  return historyItems.value.map(mapHistoryOrder);
});

const filteredItems = computed(() => {
  const query = searchQuery.value.toLowerCase();
  return items.value.filter((item) => {
    const label = categoryLabel(item);
    const matchesCategory = activeCategory.value === "All Circular Items" || label === activeCategory.value;
    const haystack = [item.title, item.description, label].filter(Boolean).join(" ").toLowerCase();
    const matchesQuery = !query || haystack.includes(query);
    return matchesCategory && matchesQuery;
  });
});

function formatCurrency(value) {
  const number = Number(value);
  if (!Number.isFinite(number)) {
    return "0.00";
  }
  return number.toLocaleString("en-US", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
}

function formatWhole(value) {
  const number = Number(value);
  if (!Number.isFinite(number)) {
    return "0";
  }
  return number.toLocaleString("en-US", {
    maximumFractionDigits: 0,
  });
}

function primaryImage(item) {
  const urls = parseMarketImageUrls(item.image_urls_json);
  return urls[0] || "";
}

function categoryLabel(item) {
  const text = `${item.title || ""} ${item.description || ""}`.toLowerCase();
  if (text.includes("solar") || text.includes("panel")) {
    return "Refurbished Solar";
  }
  if (text.includes("textile") || text.includes("fabric") || text.includes("clothing")) {
    return "Sustainable Textiles";
  }
  if (text.includes("processor") || text.includes("circuit") || text.includes("tech") || text.includes("laptop") || text.includes("hardware")) {
    return "Tech Hardware";
  }
  if (text.includes("fiber") || text.includes("part") || text.includes("scrap") || text.includes("industrial") || text.includes("metal")) {
    return "Industrial Parts";
  }
  return "All Circular Items";
}

function badgeLabel(item) {
  const category = categoryLabel(item);
  if (category === "Refurbished Solar") return "Certified Refurb";
  if (category === "Industrial Parts") return "B-Stock Bulk";
  return "Excellent Condition";
}

function badgeClass(item) {
  const category = categoryLabel(item);
  if (category === "Refurbished Solar") {
    return "bg-secondary-fixed text-on-secondary-fixed";
  }
  if (category === "Industrial Parts") {
    return "bg-surface-container-highest text-on-surface";
  }
  return "bg-secondary-fixed text-on-secondary-fixed";
}

function priceLabel(item) {
  return formatCurrency(item.price_points);
}

function usdEstimateLabel(item) {
  const price = Number(item.price_points || 0);

  if (!Number.isFinite(price) || price <= 0) {
    return "Est. $0.00";
  }
  return `Est. $${(price * 3.65).toFixed(2)}`;
}

function provenanceTags(item) {
  const sellerTag = `S${String(item.seller_id ?? "0").slice(-1)}`;
  const categoryTag = categoryLabel(item)
    .split(" ")
    .map((part) => part[0])
    .join("")
    .slice(0, 2)
    .toUpperCase();
  return [sellerTag, categoryTag || "CS", "CS"];
}

function provenanceLabel(item) {
  const tags = categoryLabel(item);
  if (tags === "Tech Hardware") {
    return "3 Previous Owners • 4y Lifecycle";
  }
  if (tags === "Refurbished Solar") {
    return "2 Previous Owners • 5y Lifecycle";
  }
  return "3 Previous Owners • 4y Lifecycle";
}

function goTo(to) {
  router.push(to);
}

function goToAiSnap() {
  goTo("/ai");
}

function goToProject() {
  goTo("/project");
}

function goToLedger() {
  goTo("/ledger");
}

function goToOrders() {
  goTo("/market/orders");
}

async function loadItems(targetPage = 1) {
  loading.value = true;
  error.value = "";
  try {
    let data = await fetchMarketItems({
      page: targetPage,
      perPage: ITEMS_PER_PAGE,
      token: token.value || undefined,
    });
    if ((!data || !Array.isArray(data.items)) && token.value) {
      data = await fetchMarketItems({
        page: targetPage,
        perPage: ITEMS_PER_PAGE,
      });
    }
    items.value = data.items || [];
    itemsTotal.value = data.total ?? items.value.length;
    itemsPage.value = targetPage;
  } catch (err) {
    if (token.value) {
      try {
        const fallbackData = await fetchMarketItems({
          page: targetPage,
          perPage: ITEMS_PER_PAGE,
        });
        items.value = fallbackData?.items || [];
        itemsTotal.value = fallbackData?.total ?? items.value.length;
        itemsPage.value = targetPage;
        error.value = "";
        return;
      } catch {
        // Fall through to the visible error state only if both requests fail.
      }
    }
    error.value = err instanceof Error ? err.message : "Failed to load.";
  } finally {
    loading.value = false;
  }
}

function goToItemsPage(targetPage) {
  if (targetPage < 1 || targetPage > itemsTotalPages.value) return;
  loadItems(targetPage);
  document.querySelector("[data-market-grid]")?.scrollIntoView({ behavior: "smooth", block: "start" });
}

function itemsPrevPage() {
  goToItemsPage(itemsPage.value - 1);
}

function itemsNextPage() {
  goToItemsPage(itemsPage.value + 1);
}

function mapHistoryOrder(order) {
  const currentUserId = Number(user.value?.id);
  const buyerId = Number(order.buyer_id);
  const sellerId = Number(order.seller_id);
  const signedAmount = Number(order.price_points || 0);
  const isBuyer = Number.isFinite(currentUserId) && currentUserId === buyerId;
  const isSeller = Number.isFinite(currentUserId) && currentUserId === sellerId;
  const status = String(order.status || "").toLowerCase();

  let title = `Order #${order.id}`;
  let icon = "shopping_bag";
  let iconClass = "bg-primary-container/30 text-primary";
  let amountClass = "text-primary";
  let amount = `+ ${signedAmount.toFixed(2)} CO2`;

  if (status === "paid") {
    title = `Asset Acquisition: Item #${order.item_id}`;
    icon = "shopping_bag";
    iconClass = "bg-primary-container/30 text-primary";
    amountClass = "text-error";
    amount = `- ${signedAmount.toFixed(2)} CO2`;
  } else if (status === "shipped") {
    title = `Warehouse Transfer: Item #${order.item_id}`;
    icon = "move_up";
    iconClass = "bg-tertiary-container/30 text-tertiary";
    amountClass = isBuyer ? "text-error" : "text-primary";
    amount = `${isBuyer ? "-" : "+"} ${signedAmount.toFixed(2)} CO2`;
  } else if (status === "completed") {
    title = `Ownership Transfer: Item #${order.item_id}`;
    icon = "inventory_2";
    iconClass = "bg-secondary-container/30 text-secondary";
    amountClass = "text-primary";
    amount = `+ ${signedAmount.toFixed(2)} CO2`;
  } else if (status === "cancelled") {
    title = `Cancelled Transfer: Item #${order.item_id}`;
    icon = "close";
    iconClass = "bg-surface-container-highest text-on-surface";
    amountClass = "text-on-surface-variant";
    amount = `0.00 CO2`;
  }

  const directionLabel = isBuyer
    ? `To: Seller #${sellerId}`
    : isSeller
      ? `From: Buyer #${buyerId}`
      : `Buyer #${buyerId} • Seller #${sellerId}`;

  return {
    key: `order-${order.id}`,
    icon,
    iconClass,
    title,
    subtitle: `${formatHistoryDate(order.created_at)} • ${directionLabel}`,
    amount,
    amountClass,
    status: status ? status.charAt(0).toUpperCase() + status.slice(1) : "Completed",
  };
}

function formatHistoryDate(value) {
  if (!value) return "";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return String(value);
  return new Intl.DateTimeFormat("en-US", {
    month: "short",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  }).format(date);
}

async function loadHistory({ append = false } = {}) {
  historyLoading.value = true;
  historyError.value = "";
  try {
    if (!isLoggedIn.value) {
      historyItems.value = [];
      historyTotal.value = 0;
      return;
    }
    const data = await fetchMyOrders({
      page: historyPage.value,
      perPage: 3,
      role: historyRole.value,
      token: token.value,
    });
    const next = data.items || [];
    historyItems.value = append ? historyItems.value.concat(next) : next;
    historyTotal.value = Number.isFinite(Number(data.total)) ? Number(data.total) : historyItems.value.length;
  } catch (err) {
    historyError.value = err instanceof Error ? err.message : "Failed to load history.";
    if (!append) {
      historyItems.value = [];
      historyTotal.value = 0;
    }
  } finally {
    historyLoading.value = false;
  }
}

async function loadMoreHistory() {
  if (!isLoggedIn.value || historyLoading.value || !historyHasMore.value) {
    return;
  }
  historyPage.value += 1;
  await loadHistory({ append: true });
}

async function cycleHistoryRole() {
  const order = ["all", "buyer", "seller"];
  const idx = order.indexOf(historyRole.value);
  historyRole.value = order[(idx + 1) % order.length];
  historyPage.value = 1;
  historyItems.value = [];
  await loadHistory();
}

onMounted(async () => {
  await Promise.all([loadItems(1), loadHistory()]);
});
</script>

<style scoped src="../../styles/views/market-view.css"></style>
