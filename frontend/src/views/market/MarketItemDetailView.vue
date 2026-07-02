<template>
  <div class="market-shell min-h-screen bg-[#f3f7f5] font-body text-[#2b302f]" data-market-detail-page>
    <AppHeader
      :is-authenticated="isLoggedIn"
      :avatar-alt="avatarAlt"
      :avatar-url="avatarUrl"
      :points-label="`${walletLabel} pts`"
    />

    <div class="flex min-h-screen pt-6">
      <main class="flex-1 px-6 pb-32 md:px-8 md:pb-16 lg:px-10 xl:px-12">
        <div class="mx-auto w-full max-w-7xl">
          <header class="mb-10">
            <RouterLink class="mb-3 inline-flex items-center gap-1 text-sm font-bold text-primary" to="/market">
              <span class="material-symbols-outlined text-sm">arrow_back</span>
              Back to market
            </RouterLink>
            <h1 class="mb-2 font-headline text-4xl font-extrabold tracking-tight text-on-background md:text-5xl">
              {{ item?.title || "Green Market" }}
            </h1>
            <p class="max-w-2xl text-on-surface-variant">
              Trade recycled assets, manage your circular warehouse, and track the environmental provenance of every item in the ecosystem.
            </p>
          </header>

          <div v-if="loading" class="rounded-3xl bg-surface-container-lowest p-8 shadow-[0_8px_32px_rgba(43,48,47,0.04)]">
            Loading item...
          </div>
          <p v-else-if="error" class="rounded-3xl bg-surface-container-lowest p-8 text-error shadow-[0_8px_32px_rgba(43,48,47,0.04)]">
            {{ error }}
          </p>

          <div
            v-else-if="item"
            class="grid grid-cols-1 gap-6 xl:grid-cols-[minmax(0,1.2fr)_minmax(320px,0.8fr)]"
            data-market-detail-layout
            data-market-detail-summary
          >
            <div class="space-y-6">
              <article class="group overflow-hidden rounded-3xl bg-surface-container-lowest shadow-[0_8px_32px_rgba(43,48,47,0.04)]">
                <div class="relative aspect-square overflow-hidden bg-surface-container-low">
                  <img
                    v-if="images[0]"
                    :alt="item.title"
                    class="h-full w-full object-cover transition-transform duration-500 group-hover:scale-105"
                    :src="images[0]"
                  />
                  <div v-else class="flex h-full w-full items-center justify-center text-sm text-on-surface-variant">
                    No image
                  </div>
                  <div class="absolute left-4 top-4">
                    <span class="rounded-full bg-secondary-fixed px-3 py-1 text-[10px] font-black uppercase tracking-tighter text-on-secondary-fixed">
                      {{ badgeLabel }}
                    </span>
                  </div>
                </div>
                <div class="p-6">
                  <div class="mb-2 flex items-start justify-between gap-4">
                    <div>
                      <p class="mb-1 text-xs font-bold uppercase tracking-wider text-on-surface-variant">
                        {{ categoryLabel }}
                      </p>
                      <h2 class="font-bold text-lg">{{ item.title }}</h2>
                    </div>
                    <button
                      class="text-primary transition-transform hover:scale-110"
                      type="button"
                      aria-label="Favorite item"
                    >
                      <span class="material-symbols-outlined">favorite</span>
                    </button>
                  </div>

                  <div class="mb-4 flex items-baseline gap-2">
                    <span class="font-headline text-2xl font-bold">{{ priceLabel }}</span>
                    <span class="text-sm font-bold text-primary">CO2 Credits</span>
                    <span class="ml-auto text-xs text-on-surface-variant">{{ usdLabel }}</span>
                  </div>

                  <p class="text-sm text-on-surface-variant">
                    {{ item.description || "No description." }}
                  </p>
                </div>
              </article>

              <section class="rounded-3xl bg-surface-container-low p-8">
                <div class="mb-8 flex items-center justify-between gap-4">
                  <div>
                    <h3 class="font-headline text-2xl font-bold">Ownership Transfer History</h3>
                    <p class="text-sm text-on-surface-variant">Recent ledger movements in your circular flow</p>
                  </div>
                  <button
                    class="rounded-full p-2 transition-colors hover:bg-surface-container"
                    type="button"
                    @click="reloadRelatedOrders"
                    aria-label="Refresh related orders"
                  >
                    <span class="material-symbols-outlined">filter_list</span>
                  </button>
                </div>

                <div class="space-y-4">
                  <div
                    v-if="relatedHistoryLoading"
                    class="rounded-2xl bg-surface-container-lowest p-4 text-sm text-on-surface-variant"
                  >
                    Loading history...
                  </div>
                  <div
                    v-else-if="relatedHistoryRows.length === 0"
                    class="rounded-2xl bg-surface-container-lowest p-4 text-sm text-on-surface-variant"
                  >
                    No transfer history yet.
                  </div>
                  <div
                    v-for="row in relatedHistoryRows"
                    :key="row.key"
                    class="flex items-center justify-between rounded-2xl bg-surface-container-lowest p-4 transition-transform hover:translate-x-1"
                  >
                    <div class="flex items-center gap-4">
                      <div class="flex h-12 w-12 items-center justify-center rounded-xl" :class="row.iconClass">
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
                  class="mt-8 w-full rounded-xl bg-surface-container-high py-3 text-sm font-bold transition-colors hover:bg-surface-container-highest"
                  type="button"
                  @click="goToOrders"
                >
                  View All Orders
                </button>
              </section>
            </div>

            <aside class="space-y-6">
              <article
                class="relative flex min-h-[240px] flex-col justify-between overflow-hidden rounded-3xl bg-primary p-8 text-on-primary shadow-[0_8px_32px_rgba(43,48,47,0.08)]"
              >
                <div class="relative z-10">
                  <p class="mb-2 text-xs font-bold uppercase tracking-widest text-on-primary/70">
                    Acquisition Price
                  </p>
                  <h2 class="font-headline text-5xl font-bold">
                    {{ priceLabel }}
                    <span class="font-body text-2xl font-normal opacity-80">CO2e</span>
                  </h2>
                  <div class="mt-4 flex flex-wrap gap-4">
                    <span class="flex items-center gap-1 rounded-full border border-on-primary/30 bg-on-primary/20 px-3 py-1 text-xs font-bold">
                      <span class="material-symbols-outlined text-sm">trending_up</span>
                      {{ usdLabel }}
                    </span>
                    <span class="flex items-center gap-1 rounded-full bg-on-primary/20 px-3 py-1 text-xs font-bold">
                      <span class="material-symbols-outlined text-sm">shield</span>
                      {{ item.status || "active" }}
                    </span>
                  </div>
                </div>

                <div class="relative z-10 mt-8 flex flex-wrap gap-4">
                  <button
                    class="rounded-xl bg-on-primary px-4 py-3 text-sm font-bold text-primary transition-all hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-60"
                    type="button"
                    :disabled="buying || !canBuy"
                    @click="buy"
                  >
                    {{ buying ? "Placing order..." : canBuy ? "Acquire Asset" : "Unavailable" }}
                  </button>
                  <RouterLink
                    class="rounded-xl border border-on-primary/30 px-4 py-3 text-sm font-bold text-on-primary transition-all hover:bg-on-primary/10"
                    to="/market/orders"
                  >
                    View orders
                  </RouterLink>
                </div>

                <p v-if="actionError" class="mt-4 text-sm font-bold text-[#ffefee]">{{ actionError }}</p>
                <p v-if="actionOk" class="mt-4 text-sm font-bold text-[#d1ffc8]">{{ actionOk }}</p>

                <div class="absolute bottom-0 right-0 h-48 w-48 rounded-full bg-secondary-fixed/20 blur-3xl" />
                <div class="absolute right-6 top-6 rounded-full bg-secondary-fixed p-4 text-[#324600]">
                  <span class="material-symbols-outlined text-4xl">inventory_2</span>
                </div>
              </article>

              <article class="rounded-3xl bg-surface-container p-8">
                <p class="mb-6 text-xs font-bold uppercase tracking-widest text-on-surface-variant">
                  Item Snapshot
                </p>
                <div class="space-y-4">
                  <div class="flex items-end justify-between gap-4">
                    <span class="text-sm font-medium">Storage Used</span>
                    <span class="text-sm font-bold">64%</span>
                  </div>
                  <div class="h-3 w-full overflow-hidden rounded-full bg-surface-container-high">
                    <div class="h-full w-[64%] rounded-full bg-primary" />
                  </div>
                  <p class="text-sm text-on-surface-variant">{{ images.length }} images currently attached</p>
                  <p class="text-sm text-on-surface-variant">Seller #{{ item.seller_id }}</p>
                </div>
                <div class="mt-8 flex flex-wrap gap-3">
                  <span class="rounded-full bg-surface-container-lowest px-4 py-2 text-xs font-bold">{{ categoryLabel }}</span>
                  <span class="rounded-full bg-surface-container-lowest px-4 py-2 text-xs font-bold">{{ item.status || "active" }}</span>
                </div>
              </article>
            </aside>
          </div>

          <div v-if="images.length > 1" class="mt-6 grid grid-cols-2 gap-4 md:grid-cols-3">
            <img
              v-for="(url, idx) in images.slice(1)"
              :key="`${url}-${idx}`"
              :alt="item.title"
              class="h-40 w-full rounded-3xl object-cover"
              :src="url"
            />
          </div>
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
import { computed, onBeforeUnmount, onMounted, ref } from "vue";
import { RouterLink, useRoute, useRouter } from "vue-router";

import { fetchMarketItem, fetchMyOrders, parseMarketImageUrls, placeMarketOrder, recordMarketLongView } from "../../api/market/market.js";
import AppHeader from "../../components/common/AppHeader.vue";
import { useAuth } from "../../composables/useAuth.js";
import { showErrorToast, showSuccessToast } from "../../composables/useToast.js";

const route = useRoute();
const router = useRouter();
const { isLoggedIn, token, user } = useAuth();

const item = ref(null);
const loading = ref(false);
const error = ref("");
const buying = ref(false);
const actionError = ref("");
const actionOk = ref("");
const longViewTracked = ref(false);
const relatedHistoryRows = ref([]);
const relatedHistoryLoading = ref(false);
let longViewTimer = null;

const mobileNavEntries = computed(() => [
  { label: "Ledger", icon: "receipt_long", to: "/ledger", active: false },
  { label: "Projects", icon: "assignment", to: "/project", active: false },
  { label: "Snap", icon: "photo_camera", to: "/ai", active: false },
  { label: "Market", icon: "storefront", to: "/market", active: true },
  { label: "Forum", icon: "groups", to: "/forum", active: false },
]);

const avatarAlt = computed(() => user.value?.username || "User");
const avatarUrl = computed(() => user.value?.avatar_url || "");
const walletLabel = computed(() => formatWhole(Number(user.value?.current_points ?? 1240)));
const images = computed(() => (item.value ? parseMarketImageUrls(item.value.image_urls_json) : []));
const priceLabel = computed(() => formatCurrency(item.value?.price_points ?? 0));
const usdLabel = computed(() => `Est. $${(Number(item.value?.price_points || 0) * 3.65).toFixed(2)}`);
const categoryLabel = computed(() => inferCategory(item.value));
const badgeLabel = computed(() => inferBadge(item.value));
const canBuy = computed(() => {
  if (!item.value || !isLoggedIn.value) {
    return false;
  }
  if (item.value.status !== "active") {
    return false;
  }
  if (user.value?.id && Number(user.value.id) === Number(item.value.seller_id)) {
    return false;
  }
  return true;
});

function formatCurrency(value) {
  const number = Number(value);
  return number.toLocaleString("en-US", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
}

function formatWhole(value) {
  return Number(value).toLocaleString("en-US", {
    maximumFractionDigits: 0,
  });
}

function inferCategory(currentItem) {
  const text = `${currentItem?.title || ""} ${currentItem?.description || ""}`.toLowerCase();
  if (text.includes("solar") || text.includes("panel")) return "Refurbished Solar";
  if (text.includes("textile") || text.includes("fabric") || text.includes("clothing")) return "Sustainable Textiles";
  if (text.includes("processor") || text.includes("circuit") || text.includes("tech") || text.includes("laptop") || text.includes("hardware")) return "Tech Hardware";
  if (text.includes("fiber") || text.includes("part") || text.includes("scrap") || text.includes("industrial") || text.includes("metal")) return "Industrial Parts";
  return "All Circular Items";
}

function inferBadge(currentItem) {
  const category = inferCategory(currentItem);
  if (category === "Refurbished Solar") return "Certified Refurb";
  if (category === "Industrial Parts") return "B-Stock Bulk";
  return "Excellent Condition";
}

function goTo(to) {
  router.push(to);
}

function goToAiSnap() {
  goTo("/ai");
}

function goToOrders() {
  goTo("/market/orders");
}

async function load() {
  loading.value = true;
  error.value = "";
  clearPendingLongView();
  try {
    item.value = await fetchMarketItem(route.params.id, token.value || undefined);
    await Promise.all([scheduleLongView(), loadRelatedOrders()]);
  } catch (err) {
    error.value = err instanceof Error ? err.message : "Failed to load.";
    item.value = null;
  } finally {
    loading.value = false;
  }
}

function clearPendingLongView() {
  if (longViewTimer !== null) {
    window.clearTimeout(longViewTimer);
    longViewTimer = null;
  }
}

async function scheduleLongView() {
  longViewTracked.value = false;
  if (!isLoggedIn.value || !item.value || Number(user.value?.id) === Number(item.value?.seller_id)) {
    return;
  }
  clearPendingLongView();
  longViewTimer = window.setTimeout(async () => {
    if (!item.value || longViewTracked.value) {
      return;
    }
    try {
      await recordMarketLongView(item.value.id, token.value);
      longViewTracked.value = true;
    } catch {
      // silent analytics failure
    } finally {
      longViewTimer = null;
    }
  }, 15000);
}

async function loadRelatedOrders() {
  relatedHistoryLoading.value = true;
  try {
    if (!isLoggedIn.value || !item.value) {
      relatedHistoryRows.value = [];
      return;
    }
    const data = await fetchMyOrders({ page: 1, perPage: 50, role: "all", token: token.value });
    const orders = (data.items || []).filter((order) => Number(order.item_id) === Number(item.value.id));
    relatedHistoryRows.value = orders.map(mapHistoryOrder);
  } catch {
    relatedHistoryRows.value = [];
  } finally {
    relatedHistoryLoading.value = false;
  }
}

async function reloadRelatedOrders() {
  await loadRelatedOrders();
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

async function buy() {
  actionError.value = "";
  actionOk.value = "";
  if (!isLoggedIn.value) {
    router.push("/login");
    return;
  }
  if (!item.value || !canBuy.value) {
    return;
  }
  buying.value = true;
  try {
    const order = await placeMarketOrder({ itemId: item.value.id }, token.value);
    actionOk.value = `Order #${order.id} placed successfully.`;
    showSuccessToast("Order placed", `Order #${order.id} was created successfully.`);
  } catch (err) {
    actionError.value = err instanceof Error ? err.message : "Order failed.";
    showErrorToast("Order failed", actionError.value);
  } finally {
    buying.value = false;
  }
}

onMounted(load);
onBeforeUnmount(() => {
  clearPendingLongView();
});
</script>

<style scoped src="../../styles/views/market-view.css"></style>
