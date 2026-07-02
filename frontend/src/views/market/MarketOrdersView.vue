<template>
  <div class="market-shell min-h-screen bg-[#f3f7f5] font-body text-[#2b302f]" data-market-orders-page>
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
              Transfer History
            </h1>
            <p class="max-w-2xl text-on-surface-variant">
              Recent ledger movements in your circular flow
            </p>
          </header>

          <section
            class="mb-8 flex gap-3 overflow-x-auto pb-2"
            data-market-orders-overview
            data-market-orders-tabs
          >
            <button
              v-for="tab in tabs"
              :key="tab.role"
              type="button"
              class="whitespace-nowrap rounded-full px-6 py-2 text-sm font-bold transition-colors"
              :class="role === tab.role ? activeTabClass : tabClass"
              @click="changeRole(tab.role)"
            >
              {{ tab.label }}
            </button>
          </section>

          <p v-if="!isLoggedIn" class="rounded-3xl bg-surface-container-lowest p-8 shadow-[0_8px_32px_rgba(43,48,47,0.04)]">
            <RouterLink class="font-bold text-primary" to="/login">Sign in</RouterLink>
            to view your orders.
          </p>

          <template v-else>
            <div
              v-if="loading"
              class="rounded-3xl bg-surface-container-lowest p-8 shadow-[0_8px_32px_rgba(43,48,47,0.04)]"
            >
              Loading orders...
            </div>
            <p v-else-if="error" class="rounded-3xl bg-surface-container-lowest p-8 text-error shadow-[0_8px_32px_rgba(43,48,47,0.04)]">
              {{ error }}
            </p>

            <div v-else class="space-y-4">
              <div
                v-if="orderRows.length === 0"
                class="rounded-3xl bg-surface-container-lowest p-8 shadow-[0_8px_32px_rgba(43,48,47,0.04)]"
              >
                No matching orders yet.
              </div>

              <article
                v-for="row in orderRows"
                :key="row.key"
                class="rounded-3xl bg-surface-container-lowest p-4 shadow-[0_8px_32px_rgba(43,48,47,0.04)] transition-transform hover:translate-x-1"
                data-market-order-row
              >
                <div class="flex items-start justify-between gap-4">
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

                <div class="mt-4 flex flex-wrap gap-3">
                  <button
                    v-if="row.canShip"
                    type="button"
                    class="rounded-xl border border-outline-variant px-4 py-3 text-sm font-bold transition-colors hover:bg-surface-container-highest disabled:cursor-not-allowed disabled:opacity-60"
                    :disabled="busyId === row.id"
                    @click="doShip(row.id)"
                  >
                    Mark shipped
                  </button>
                  <button
                    v-if="row.canConfirm"
                    type="button"
                    class="rounded-xl bg-primary px-4 py-3 text-sm font-bold text-on-primary transition-colors hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-60"
                    :disabled="busyId === row.id"
                    @click="doConfirm(row.id)"
                  >
                    Confirm receipt
                  </button>
                  <button
                    v-if="row.canCancel"
                    type="button"
                    class="rounded-xl border border-outline-variant px-4 py-3 text-sm font-bold transition-colors hover:bg-surface-container-highest disabled:cursor-not-allowed disabled:opacity-60"
                    :disabled="busyId === row.id"
                    @click="doCancel(row.id)"
                  >
                    Cancel order
                  </button>
                </div>

                <p v-if="row.error" class="mt-4 text-sm font-bold text-error">{{ row.error }}</p>
              </article>

              <button
                v-if="hasMore"
                class="w-full rounded-xl bg-surface-container-high py-3 text-sm font-bold transition-colors hover:bg-surface-container-highest disabled:cursor-not-allowed disabled:opacity-60"
                type="button"
                :disabled="loadingMore"
                @click="loadMore"
              >
                {{ loadingMore ? "Loading..." : "Load More History" }}
              </button>
            </div>
          </template>
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
import { computed, onMounted, ref, watch } from "vue";
import { RouterLink, useRouter } from "vue-router";

import { cancelMarketOrder, confirmMarketOrder, fetchMyOrders, shipMarketOrder } from "../../api/market/market.js";
import AppHeader from "../../components/common/AppHeader.vue";
import { useAuth } from "../../composables/useAuth.js";
import { showErrorToast, showSuccessToast } from "../../composables/useToast.js";

const { isLoggedIn, token, user } = useAuth();
const router = useRouter();

const role = ref("all");
const orders = ref([]);
const loading = ref(false);
const loadingMore = ref(false);
const error = ref("");
const busyId = ref(null);
const rowError = ref(null);
const rowMessage = ref("");
const page = ref(1);
const total = ref(0);

const tabs = [
  { role: "all", label: "All" },
  { role: "buyer", label: "Purchases" },
  { role: "seller", label: "Sales" },
];

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
const uid = computed(() => (user.value?.id != null ? Number(user.value.id) : null));
const activeTabClass = "bg-secondary-fixed text-on-secondary-fixed";
const tabClass = "bg-surface-container hover:bg-surface-container-high";
const hasMore = computed(() => orders.value.length < total.value);
const orderRows = computed(() => orders.value.map((order) => mapOrder(order)));

function formatWhole(value) {
  return Number(value).toLocaleString("en-US", {
    maximumFractionDigits: 0,
  });
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

function goTo(to) {
  router.push(to);
}

function goToAiSnap() {
  goTo("/ai");
}

function goToMarket() {
  goTo("/market");
}

async function load({ append = false } = {}) {
  if (!isLoggedIn.value) {
    return;
  }
  loading.value = !append;
  loadingMore.value = append;
  error.value = "";
  try {
    const data = await fetchMyOrders({ page: page.value, perPage: 50, role: role.value, token: token.value });
    const next = data.items || [];
    orders.value = append ? orders.value.concat(next) : next;
    total.value = Number.isFinite(Number(data.total)) ? Number(data.total) : orders.value.length;
  } catch (err) {
    error.value = err instanceof Error ? err.message : "Failed to load.";
  } finally {
    loading.value = false;
    loadingMore.value = false;
  }
}

function changeRole(nextRole) {
  role.value = nextRole;
}

function resetAndLoad() {
  page.value = 1;
  orders.value = [];
  load();
}

async function loadMore() {
  if (!hasMore.value || loadingMore.value) {
    return;
  }
  page.value += 1;
  await load({ append: true });
}

function mapOrder(order) {
  const buyerId = Number(order.buyer_id);
  const sellerId = Number(order.seller_id);
  const signedAmount = Number(order.price_points || 0);
  const isBuyer = uid.value != null && uid.value === buyerId;
  const isSeller = uid.value != null && uid.value === sellerId;
  const status = String(order.status || "").toLowerCase();

  let title = `Order #${order.id}`;
  let icon = "shopping_bag";
  let iconClass = "bg-primary-container/30 text-primary";
  let amountClass = "text-primary";
  let amount = `+ ${signedAmount.toFixed(2)} CO2`;
  let canShip = false;
  let canConfirm = false;
  let canCancel = false;

  if (status === "paid") {
    title = `Asset Acquisition: Item #${order.item_id}`;
    icon = "shopping_bag";
    iconClass = "bg-primary-container/30 text-primary";
    amountClass = "text-error";
    amount = `- ${signedAmount.toFixed(2)} CO2`;
    canShip = isSeller;
    canCancel = isBuyer;
  } else if (status === "shipped") {
    title = `Warehouse Transfer: Item #${order.item_id}`;
    icon = "move_up";
    iconClass = "bg-tertiary-container/30 text-tertiary";
    amountClass = isBuyer ? "text-error" : "text-primary";
    amount = `${isBuyer ? "-" : "+"} ${signedAmount.toFixed(2)} CO2`;
    canConfirm = isBuyer;
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

  return {
    id: order.id,
    key: `order-${order.id}`,
    icon,
    iconClass,
    title,
    subtitle: `${formatHistoryDate(order.created_at)} • Buyer #${buyerId} • Seller #${sellerId}`,
    amount,
    amountClass,
    status: status ? status.charAt(0).toUpperCase() + status.slice(1) : "Completed",
    canShip,
    canConfirm,
    canCancel,
    error: rowError.value === order.id ? rowMessage.value : "",
  };
}

async function doShip(id) {
  await runAction(id, () => shipMarketOrder(id, token.value), "Order shipped", `Order #${id} was marked as shipped.`);
}

async function doConfirm(id) {
  await runAction(id, () => confirmMarketOrder(id, token.value), "Order confirmed", `Order #${id} was confirmed.`);
}

async function doCancel(id) {
  await runAction(id, () => cancelMarketOrder(id, token.value), "Order cancelled", `Order #${id} was cancelled.`);
}

async function runAction(id, fn, successTitle, successBody) {
  rowError.value = null;
  rowMessage.value = "";
  busyId.value = id;
  try {
    await fn();
    await load();
    showSuccessToast(successTitle, successBody);
  } catch (err) {
    rowError.value = id;
    rowMessage.value = err instanceof Error ? err.message : "Action failed.";
    showErrorToast("Order action failed", rowMessage.value);
  } finally {
    busyId.value = null;
  }
}

watch([role, isLoggedIn], () => {
  if (isLoggedIn.value) {
    resetAndLoad();
  }
});

onMounted(() => {
  load();
});
</script>

<style scoped src="../../styles/views/market-view.css"></style>
