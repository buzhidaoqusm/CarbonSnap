<template>
  <div class="ledger-view bg-surface text-on-surface min-h-screen flex flex-col">
    <AppHeader
      :is-authenticated="isLoggedIn"
      :avatar-alt="avatarAlt"
      :avatar-href="avatarTarget"
      :avatar-url="avatarUrl"
      :points-label="`${headerPointsDisplay} pts`"
    />

    <div class="flex flex-1 flex-col">
      <main class="min-w-0 flex-1 overflow-y-auto p-6 md:p-10 pb-32">
        <div class="mx-auto w-full max-w-5xl">
          <p v-if="!isLoggedIn" class="rounded-[2rem] border border-surface-container-high bg-white/80 p-6 text-sm text-on-surface-variant shadow-sm">
            <RouterLink class="font-bold text-primary" to="/login">Sign in</RouterLink>
            to view your personal green capital, badges, and impact history.
          </p>

          <template v-else>
            <p v-if="loading" class="rounded-[2rem] border border-surface-container-high bg-white/80 p-6 text-sm text-on-surface-variant shadow-sm">
              Loading ledger...
            </p>
            <p v-else-if="error" class="rounded-[2rem] border border-error-container bg-error-container/10 p-6 text-sm text-error">
              {{ error }}
            </p>

            <template v-else>
              <header class="mb-12">
                <h1 class="text-4xl font-black font-headline text-on-surface tracking-tight mb-2">
                  Personal Green Capital
                </h1>
                <p class="text-on-surface-variant max-w-2xl">
                  Manage your environmental assets, monitor your global footprint reduction, and leverage your credits for impact projects.
                </p>
              </header>

              <!-- 3D Forest Section -->
              <section class="forest-section mb-6">
                <div ref="forestMountRef" class="forest-canvas-wrap"></div>
                <div class="forest-overlay">
                  <div class="forest-overlay__top">
                    <span class="forest-badge">
                      <span class="forest-badge__icon" aria-hidden="true">🌲</span>
                      {{ forestTreeCount }} / {{ FOREST_MAX_TREES }} trees planted
                    </span>
                    <span v-if="gamification?.level" class="forest-level">
                      Level {{ gamification.level }}
                      <span v-if="gamification.level_title"> · {{ gamification.level_title }}</span>
                    </span>
                  </div>
                  <div class="forest-overlay__bottom">
                    <p class="forest-hint">Your forest grows with every carbon action you take.</p>
                  </div>
                </div>
              </section>

              <div class="grid grid-cols-1 md:grid-cols-12 gap-6">
            <section
              class="md:col-span-4 bg-primary text-on-primary rounded-[2rem] p-8 flex flex-col justify-between shadow-2xl relative overflow-hidden group"
              data-ledger-hero
            >
              <div class="absolute -right-10 -top-10 w-40 h-40 bg-secondary-fixed/10 rounded-full blur-3xl group-hover:scale-150 transition-transform duration-700"></div>

              <div>
                <p class="font-headline font-bold uppercase tracking-widest text-xs opacity-70 mb-1">
                  Lifetime Points Earned
                </p>
                <h2 class="text-6xl font-headline font-black mb-4">{{ creditsDisplay }}</h2>
                <div class="flex items-center gap-2 bg-on-primary/10 w-fit px-3 py-1 rounded-full text-sm">
                  <span class="material-symbols-outlined text-sm" data-icon="trending_up">trending_up</span>
                  <span>{{ monthlyTrendLabel }}</span>
                </div>
              </div>

              <div class="mt-8 flex gap-2">
                <button
                  class="flex-1 inline-flex items-center justify-center gap-2 bg-white/10 text-on-primary py-3 rounded-xl font-bold hover:bg-white/20 transition-colors"
                  type="button"
                  data-ledger-share-trigger
                  @click="generateShareCard"
                >
                  <span class="material-symbols-outlined" data-icon="share">share</span>
                  <span>Share Ledger</span>
                </button>
              </div>
            </section>

            <section class="md:col-span-8 bg-surface-container-lowest rounded-[2rem] p-8 shadow-sm">
              <div class="flex justify-between items-center mb-8 gap-4 flex-wrap">
                <div>
                  <h3 class="font-headline font-bold text-xl">Lifetime Carbon Reduced</h3>
                  <p class="text-sm text-on-surface-variant">Your contribution to the net-zero goal</p>
                </div>

                <div class="flex gap-2">
                  <button
                    v-for="range in chartRanges"
                    :key="range"
                    class="px-3 py-1 text-xs font-bold rounded-lg"
                    :class="selectedChartRange === range ? 'bg-surface-container text-on-surface' : 'text-on-surface-variant'"
                    type="button"
                    @click="selectedChartRange = range"
                  >
                    {{ range }}
                  </button>
                </div>
              </div>

              <div class="relative h-48 w-full flex items-end gap-1 px-2">
                <div
                  v-for="(bar, index) in carbonBars"
                  :key="`${chartMonths[index]}-${bar}`"
                  class="flex-1 bg-surface-container-low rounded-t-lg transition-all hover:bg-primary/20"
                  :class="index === carbonBars.length - 1 ? 'bg-primary' : index === carbonBars.length - 2 ? 'bg-primary/40' : ''"
                  :style="{ height: `${bar}%` }"
                ></div>
              </div>

              <div class="flex justify-between mt-4 text-[10px] uppercase font-bold text-on-surface-variant tracking-widest">
                <span v-for="month in chartMonths" :key="month">{{ month }}</span>
              </div>
            </section>

            <section class="md:col-span-5 bg-surface-container rounded-[2rem] p-8" data-ledger-categories>
              <h3 class="font-headline font-bold text-xl mb-6">Impact Categories</h3>
              <div class="space-y-4">
                <div v-for="category in impactCategories" :key="category.title" class="flex items-center gap-4">
                  <div class="w-12 h-12 bg-surface-container-lowest rounded-2xl flex items-center justify-center text-primary">
                    <span class="material-symbols-outlined" :data-icon="category.icon">{{ category.icon }}</span>
                  </div>
                  <div class="flex-1">
                    <div class="flex justify-between mb-1">
                      <span class="font-bold text-sm">{{ category.title }}</span>
                      <span class="text-xs font-bold">{{ category.value }}</span>
                    </div>
                    <div class="w-full bg-white/50 h-2 rounded-full overflow-hidden">
                      <div class="bg-tertiary h-full" :style="{ width: `${category.progress}%` }"></div>
                    </div>
                  </div>
                </div>
              </div>
            </section>

            <section class="md:col-span-7 grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div class="bg-surface-container-lowest border-2 border-secondary-fixed/20 rounded-[2rem] p-6 flex flex-col justify-between">
                <div>
                  <span class="text-[10px] font-black uppercase tracking-widest text-secondary">Current Goal</span>
                  <h4 class="font-headline font-bold text-lg leading-tight mt-1">
                    {{ gamification?.level_title || "Untitled Goal" }}
                  </h4>
                </div>
                <div class="mt-4">
                  <p class="text-xs text-on-surface-variant mb-2">
                    Requirement: {{ goalRequirementLabel }}
                  </p>
                  <div class="flex items-center gap-2">
                    <div class="flex-1 bg-surface-container h-3 rounded-full overflow-hidden">
                      <div class="bg-secondary-fixed h-full" :style="{ width: `${xpPercent}%` }"></div>
                    </div>
                    <span class="text-xs font-bold">{{ xpPercent }}%</span>
                  </div>
                </div>
              </div>

              <div class="bg-tertiary text-on-tertiary rounded-[2rem] p-6 relative overflow-hidden">
                <div class="flex h-full w-full flex-col items-center justify-center p-6 relative overflow-hidden">
                  <span class="material-symbols-outlined absolute -right-4 -bottom-4 text-white/10 text-9xl" data-icon="auto_awesome">
                    auto_awesome
                  </span>

                  <div class="z-10 w-full">
                    <h4 class="font-headline font-bold text-lg mb-4 text-center">Verified Achievements</h4>
                    <div class="flex h-48 w-full flex-col items-center justify-center gap-2">
                      <div class="flex items-center justify-center">
                        <div
                          v-for="(badge, index) in badgeStack"
                          :key="badge.id || badge.name || index"
                          class="-ml-3 first:ml-0 h-20 w-20 rounded-full border border-white/20 bg-white/10 backdrop-blur-md shadow-lg overflow-hidden flex items-center justify-center text-center px-2"
                          :style="{ zIndex: badgeStack.length - index }"
                        >
                          <img
                            v-if="badge.image_url"
                            :alt="badge.name"
                            class="h-full w-full object-cover"
                            :src="badge.image_url"
                          />
                          <span v-else class="text-xs font-black uppercase leading-tight">
                            {{ badgeInitial(badge.name) }}
                          </span>
                        </div>
                      </div>
                      <p v-if="badgeStack.length" class="text-xs text-center text-on-tertiary/80">
                        {{ badgeStack[0].name }}
                      </p>
                      <p v-else class="text-xs text-center text-on-tertiary/80">
                        No badges unlocked yet
                      </p>
                    </div>
                  </div>
                </div>
              </div>
            </section>

              <section id="ledger-badges" class="md:col-span-12 bg-white rounded-[2rem] shadow-sm p-8 overflow-hidden" data-ledger-badges>
              <div class="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 mb-8">
                <h3 class="font-headline font-bold text-2xl">Ledger Activity</h3>
                <div class="flex p-1 bg-surface-container rounded-xl w-full sm:w-auto">
                  <button
                    v-for="filter in transactionFilters"
                    :key="filter"
                    class="flex-1 sm:flex-none px-6 py-2 rounded-lg font-bold text-sm"
                    :class="activeTransactionFilter === filter ? 'bg-white shadow-sm text-on-surface' : 'text-on-surface-variant'"
                    type="button"
                    @click="activeTransactionFilter = filter"
                  >
                    {{ filterLabel(filter) }}
                  </button>
                </div>
              </div>

              <div v-if="visibleTransactions.length" class="overflow-x-auto -mx-8" data-ledger-transactions>
                <table class="w-full text-left">
                  <thead class="bg-surface-container-low text-[10px] uppercase tracking-widest font-black text-on-surface-variant">
                    <tr>
                      <th class="px-8 py-4">Impact Action</th>
                      <th class="px-8 py-4">Category</th>
                      <th class="px-8 py-4">Date</th>
                      <th class="px-8 py-4 text-right">Value</th>
                    </tr>
                  </thead>
                  <tbody class="divide-y divide-outline-variant/5">
                    <tr v-for="txn in visibleTransactions" :key="txn.id" class="hover:bg-surface-container-low transition-colors group">
                      <td class="px-8 py-6">
                        <div class="flex items-center gap-4">
                          <div
                            class="w-10 h-10 rounded-full flex items-center justify-center transition-transform group-hover:scale-110"
                            :class="txn.points_delta >= 0 ? 'bg-primary-container text-primary' : 'bg-error-container/20 text-error'"
                          >
                            <span class="material-symbols-outlined" :data-icon="transactionIcon(txn)">
                              {{ transactionIcon(txn) }}
                            </span>
                          </div>
                          <div>
                            <p class="font-bold text-on-surface">{{ transactionTitle(txn) }}</p>
                            <p class="text-xs text-on-surface-variant">{{ transactionSubtitle(txn) }}</p>
                          </div>
                        </div>
                      </td>
                      <td class="px-8 py-6">
                        <span class="text-xs px-3 py-1 bg-surface-container rounded-full font-bold">
                          {{ txn.points_delta >= 0 ? "Earned" : "Spent" }}
                        </span>
                      </td>
                      <td class="px-8 py-6 text-sm text-on-surface-variant">
                        {{ formatDate(txn.created_at) }}
                      </td>
                      <td
                        class="px-8 py-6 text-right font-headline font-bold"
                        :class="txn.points_delta >= 0 ? 'text-primary' : 'text-on-surface-variant'"
                      >
                        {{ formatSignedPoints(txn.points_delta) }}
                      </td>
                    </tr>
                  </tbody>
                </table>
              </div>

              <p v-else class="text-sm text-on-surface-variant">
                No recent transactions yet.
              </p>
              </section>
              </div>
            </template>
          </template>
        </div>
      </main>
    </div>

    <div
      v-if="sharePanelOpen"
      class="fixed inset-0 z-50 flex items-center justify-center px-4 py-6"
      data-ledger-share-modal
    >
      <div
        aria-label="Close ledger share card"
        class="absolute inset-0 bg-black/50"
        role="button"
        tabindex="0"
        @click="sharePanelOpen = false"
        @keyup.enter="sharePanelOpen = false"
        @keyup.space.prevent="sharePanelOpen = false"
      ></div>
      <section
        aria-labelledby="ledger-share-title"
        aria-modal="true"
        class="relative z-10 max-h-[calc(100dvh-48px)] w-full max-w-2xl overflow-y-auto rounded-[2rem] border border-surface-container-high bg-white p-6 shadow-2xl"
        data-ledger-share-card
        role="dialog"
      >
        <div class="mb-4 flex flex-wrap items-start justify-between gap-3">
          <div>
            <h3 id="ledger-share-title" class="font-headline font-bold text-xl">Shareable Ledger Card</h3>
            <p class="text-sm text-on-surface-variant">A snapshot of your CarbonSnap progress, ready to copy or download.</p>
          </div>
          <button class="rounded-full bg-surface-container px-4 py-2 text-xs font-bold text-on-surface-variant" type="button" @click="sharePanelOpen = false">
            Close
          </button>
        </div>
        <img v-if="shareCardUrl" class="ledger-share-preview" :src="shareCardUrl" alt="Generated ledger sharing card" />
        <p v-if="shareStatus" class="mt-3 text-sm font-semibold text-primary">{{ shareStatus }}</p>
        <p v-if="shareError" class="mt-3 text-sm font-semibold text-error">{{ shareError }}</p>
        <div class="mt-4 flex flex-wrap gap-3">
          <button class="rounded-full bg-primary px-5 py-3 text-sm font-bold text-on-primary disabled:opacity-60" type="button" :disabled="!shareCardUrl" @click="copyShareCard">
            Copy Image
          </button>
          <button class="rounded-full border border-outline-variant/30 px-5 py-3 text-sm font-bold text-on-surface-variant hover:bg-surface-container disabled:opacity-60" type="button" :disabled="!shareCardUrl" @click="downloadShareCard">
            Download PNG
          </button>
        </div>
      </section>
    </div>

    <nav class="fixed bottom-0 left-0 w-full z-50 flex justify-around items-end px-4 pb-4 md:hidden bg-[#f3f7f5]/80 backdrop-blur-lg">
      <RouterLink class="flex flex-col items-center justify-center text-[#585c5b] p-2" to="/ledger">
        <span class="material-symbols-outlined">receipt_long</span>
        <span class="font-['Manrope'] text-[10px] font-bold uppercase tracking-widest mt-1">Ledger</span>
      </RouterLink>
      <RouterLink class="flex flex-col items-center justify-center text-[#585c5b] p-2" to="/project">
        <span class="material-symbols-outlined">assignment</span>
        <span class="font-['Manrope'] text-[10px] font-bold uppercase tracking-widest mt-1">Projects</span>
      </RouterLink>
      <RouterLink class="flex flex-col items-center justify-center bg-[#b9f600] text-[#324600] rounded-full p-3 mb-2 scale-110 shadow-lg" to="/ai">
        <span class="material-symbols-outlined">photo_camera</span>
      </RouterLink>
      <RouterLink class="flex flex-col items-center justify-center text-[#585c5b] p-2" to="/forum">
        <span class="material-symbols-outlined">groups</span>
        <span class="font-['Manrope'] text-[10px] font-bold uppercase tracking-widest mt-1">Forum</span>
      </RouterLink>
      <RouterLink class="flex flex-col items-center justify-center text-[#585c5b] p-2" to="/market">
        <span class="material-symbols-outlined">storefront</span>
        <span class="font-['Manrope'] text-[10px] font-bold uppercase tracking-widest mt-1">Market</span>
      </RouterLink>
    </nav>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from "vue";
import { RouterLink } from "vue-router";

import {
  fetchLedgerGamification,
  fetchLedgerRecords,
  fetchLedgerSummary,
  fetchLedgerTransactions,
} from "../../api/ledger/ledger.js";
import AppHeader from "../../components/common/AppHeader.vue";
import { useAuth } from "../../composables/useAuth.js";
import { useForestWebGL } from "../../composables/ledger/useForestWebGL.js";

const { isLoggedIn, token, user, updateUser } = useAuth();

const loading = ref(false);
const error = ref("");
const summary = ref(null);
const gamification = ref(null);
const transactions = ref([]);
const records = ref([]);
const selectedChartRange = ref("6M");
const activeTransactionFilter = ref("all");
const sharePanelOpen = ref(false);
const shareCardUrl = ref("");
const shareStatus = ref("");
const shareError = ref("");

const chartRanges = ["6M", "1Y", "ALL"];
const chartMonths = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul"];
const carbonBars = [40, 55, 45, 70, 85, 60, 95];
const transactionFilters = ["all", "earned", "spent"];

const avatarAlt = computed(() => user.value?.username || "User Profile");
const avatarUrl = computed(() => user.value?.avatar_url || "");
const avatarInitial = computed(() => (avatarAlt.value ? avatarAlt.value.charAt(0).toUpperCase() : "U"));
const avatarTarget = computed(() => (isLoggedIn.value ? "/profile" : "/login"));

const availablePoints = computed(() => summary.value?.current_points ?? gamification.value?.current_points ?? user.value?.current_points ?? 0);
const earnedPoints = computed(() =>
  summary.value?.total_points_earned ??
  gamification.value?.total_points_earned ??
  availablePoints.value,
);
const creditsDisplay = computed(() => formatNumber(earnedPoints.value));
const headerPointsDisplay = computed(() =>
  formatNumber(availablePoints.value),
);
const totalCarbonSavedDisplay = computed(() =>
  formatKg(summary.value?.total_co2_saved_kg ?? gamification.value?.total_carbon_amount ?? 0),
);
const xpPercent = computed(() => {
  const cap = Number(gamification.value?.xp_to_next ?? 0);
  if (!cap) {
    return 0;
  }
  return Math.min(100, Math.round((Number(gamification.value?.xp_in_level ?? 0) / cap) * 100));
});
const goalRequirementLabel = computed(() => `${formatNumber(gamification.value?.xp_to_next ?? 0)} XP to next level`);
const badgeStack = computed(() => gamification.value?.badges ?? []);

// ─── Forest 3D ───────────────────────────────────────────────────────────────
const FOREST_MAX_TREES = 60;
const FOREST_POINTS_PER_TREE = 2;

const forestMountRef = ref(null);
const forestTreeCount = computed(() =>
  Math.min(FOREST_MAX_TREES, Math.floor((earnedPoints.value || 0) / FOREST_POINTS_PER_TREE)),
);
const forestLevel = computed(() => gamification.value?.level ?? 1);
const forestXpProgress = computed(() => xpPercent.value / 100);

const isReducedMotion = ref(
  typeof window !== "undefined" &&
    typeof window.matchMedia === "function" &&
    window.matchMedia("(prefers-reduced-motion: reduce)").matches,
);

useForestWebGL({
  mountRef: forestMountRef,
  treeCount: forestTreeCount,
  level: forestLevel,
  xpProgress: forestXpProgress,
  isReducedMotion,
});

const monthlyTrendLabel = computed(() => {
  const cutoff = Date.now() - 1000 * 60 * 60 * 24 * 30;
  const delta = transactions.value.reduce((sum, txn) => {
    const time = Date.parse(txn.created_at || "");
    if (Number.isNaN(time) || time < cutoff) {
      return sum;
    }
    return sum + Number(txn.points_delta || 0);
  }, 0);

  if (!delta) {
    return "No recent movement";
  }

  return `${delta > 0 ? "+" : ""}${formatNumber(delta)} pts this month`;
});

const visibleTransactions = computed(() => {
  const items = [...transactions.value].sort((left, right) => {
    const leftTime = Date.parse(left.created_at || "");
    const rightTime = Date.parse(right.created_at || "");
    return rightTime - leftTime;
  });

  if (activeTransactionFilter.value === "earned") {
    return items.filter((txn) => Number(txn.points_delta || 0) > 0);
  }
  if (activeTransactionFilter.value === "spent") {
    return items.filter((txn) => Number(txn.points_delta || 0) < 0);
  }
  return items;
});

const impactCategories = computed(() => {
  const totals = {
    plastic: 0,
    paper: 0,
    metal: 0,
  };

  for (const record of records.value) {
    const value = Number(record.co2_saved_kg || 0);
    const key = wasteBucket(record.waste_type);
    if (key in totals) {
      totals[key] += value;
    }
  }

  const maxValue = Math.max(...Object.values(totals), 1);
  return [
    {
      icon: "liquor",
      title: "Plastic Reduction",
      value: formatKg(totals.plastic),
      progress: Math.round((totals.plastic / maxValue) * 100),
    },
    {
      icon: "description",
      title: "Paper & Fiber",
      value: formatKg(totals.paper),
      progress: Math.round((totals.paper / maxValue) * 100),
    },
    {
      icon: "precision_manufacturing",
      title: "Metal Scraps",
      value: formatKg(totals.metal),
      progress: Math.round((totals.metal / maxValue) * 100),
    },
  ];
});

function formatNumber(value) {
  const parsed = Number(value);
  if (Number.isNaN(parsed)) {
    return "0";
  }
  return parsed.toLocaleString();
}

function formatKg(value) {
  const parsed = Number(value);
  if (Number.isNaN(parsed)) {
    return "0.00 kg";
  }
  return `${parsed.toFixed(2)} kg`;
}

function formatSignedPoints(value) {
  const parsed = Number(value);
  if (Number.isNaN(parsed)) {
    return "0 pts";
  }
  return `${parsed > 0 ? "+" : ""}${formatNumber(parsed)} pts`;
}

function formatDate(value) {
  if (!value) {
    return "";
  }
  const parsed = new Date(value);
  return Number.isNaN(parsed.getTime()) ? value : parsed.toLocaleString();
}

function badgeInitial(name) {
  const text = String(name || "").trim();
  return text ? text.charAt(0).toUpperCase() : "B";
}

function wasteBucket(value) {
  const text = String(value || "").toLowerCase();
  if (text.includes("plastic") || text.includes("bottle") || text.includes("liquid")) {
    return "plastic";
  }
  if (text.includes("paper") || text.includes("fiber") || text.includes("card")) {
    return "paper";
  }
  if (text.includes("metal") || text.includes("scrap") || text.includes("aluminum")) {
    return "metal";
  }
  return "plastic";
}

function filterLabel(filter) {
  if (filter === "all") {
    return "All";
  }
  return filter.charAt(0).toUpperCase() + filter.slice(1);
}

function transactionTitle(txn) {
  const title = txn.title || txn.action || txn.name;
  if (title) {
    return title;
  }
  return formatActionLabel(txn.source_type);
}

function transactionSubtitle(txn) {
  return txn.description || txn.subtitle || formatActionLabel(txn.source_type) || "Carbon activity";
}

function formatActionLabel(value) {
  return String(value || "Activity")
    .replace(/_/g, " ")
    .replace(/\b\w/g, (character) => character.toUpperCase());
}

function transactionIcon(txn) {
  const source = String(txn.source_type || "").toLowerCase();
  if (source.includes("forum")) {
    return "groups";
  }
  if (source.includes("market") || source.includes("order")) {
    return "package_2";
  }
  if (source.includes("project")) {
    return "forest";
  }
  if (source.includes("record") || source.includes("analysis") || source.includes("waste")) {
    return "recycling";
  }
  return Number(txn.points_delta || 0) >= 0 ? "recycling" : "shopping_cart";
}

function drawShareCard(canvas) {
  const ctx = canvas.getContext("2d");
  const width = 1080;
  const height = 1350;
  canvas.width = width;
  canvas.height = height;

  const gradient = ctx.createLinearGradient(0, 0, width, height);
  gradient.addColorStop(0, "#0f766e");
  gradient.addColorStop(0.58, "#123f37");
  gradient.addColorStop(1, "#b9f600");
  ctx.fillStyle = gradient;
  ctx.fillRect(0, 0, width, height);

  ctx.fillStyle = "rgba(255, 255, 255, 0.12)";
  ctx.beginPath();
  ctx.arc(900, 160, 220, 0, Math.PI * 2);
  ctx.fill();
  ctx.beginPath();
  ctx.arc(140, 1180, 260, 0, Math.PI * 2);
  ctx.fill();

  ctx.fillStyle = "rgba(255, 255, 255, 0.92)";
  roundRect(ctx, 80, 90, 920, 1170, 56);
  ctx.fill();

  ctx.fillStyle = "#0f3d34";
  ctx.font = "800 54px Inter, Segoe UI, sans-serif";
  ctx.fillText("CarbonSnap Ledger", 140, 190);

  ctx.fillStyle = "#5f6f6b";
  ctx.font = "600 28px Inter, Segoe UI, sans-serif";
  ctx.fillText(`${user.value?.username || "CarbonSnap member"}'s impact snapshot`, 140, 240);

  ctx.fillStyle = "#0f766e";
  ctx.font = "900 130px Inter, Segoe UI, sans-serif";
  ctx.fillText(creditsDisplay.value, 140, 430);
  ctx.font = "800 34px Inter, Segoe UI, sans-serif";
  ctx.fillText("lifetime earned points", 150, 480);

  ctx.fillStyle = "#102f2b";
  ctx.font = "900 72px Inter, Segoe UI, sans-serif";
  ctx.fillText(totalCarbonSavedDisplay.value, 140, 620);
  ctx.font = "700 28px Inter, Segoe UI, sans-serif";
  ctx.fillStyle = "#5f6f6b";
  ctx.fillText("lifetime carbon reduced", 142, 668);

  drawMetric(ctx, "Forest", `${forestTreeCount.value}/${FOREST_MAX_TREES} trees`, 140, 770);
  drawMetric(ctx, "Level", `${forestLevel.value}${gamification.value?.level_title ? ` - ${gamification.value.level_title}` : ""}`, 140, 900);
  drawMetric(ctx, "30-day movement", monthlyTrendLabel.value, 140, 1030);

  ctx.fillStyle = "#0f3d34";
  ctx.font = "800 30px Inter, Segoe UI, sans-serif";
  ctx.fillText("carbonsnap.app/ledger", 140, 1190);
}

function drawMetric(ctx, label, value, x, y) {
  ctx.fillStyle = "#e8f7f1";
  roundRect(ctx, x, y - 54, 800, 92, 28);
  ctx.fill();
  ctx.fillStyle = "#5f6f6b";
  ctx.font = "800 22px Inter, Segoe UI, sans-serif";
  ctx.fillText(label.toUpperCase(), x + 34, y - 16);
  ctx.fillStyle = "#123f37";
  ctx.font = "900 34px Inter, Segoe UI, sans-serif";
  ctx.fillText(value, x + 34, y + 24);
}

function roundRect(ctx, x, y, width, height, radius) {
  ctx.beginPath();
  ctx.moveTo(x + radius, y);
  ctx.lineTo(x + width - radius, y);
  ctx.quadraticCurveTo(x + width, y, x + width, y + radius);
  ctx.lineTo(x + width, y + height - radius);
  ctx.quadraticCurveTo(x + width, y + height, x + width - radius, y + height);
  ctx.lineTo(x + radius, y + height);
  ctx.quadraticCurveTo(x, y + height, x, y + height - radius);
  ctx.lineTo(x, y + radius);
  ctx.quadraticCurveTo(x, y, x + radius, y);
  ctx.closePath();
}

function generateShareCard() {
  sharePanelOpen.value = true;
  shareStatus.value = "";
  shareError.value = "";
  const canvas = document.createElement("canvas");
  drawShareCard(canvas);
  shareCardUrl.value = canvas.toDataURL("image/png");
}

async function copyShareCard() {
  shareStatus.value = "";
  shareError.value = "";
  if (!shareCardUrl.value) {
    return;
  }
  if (!navigator.clipboard || typeof ClipboardItem === "undefined") {
    shareError.value = "Image copy is not supported in this browser. Download the PNG instead.";
    return;
  }
  const response = await fetch(shareCardUrl.value);
  const blob = await response.blob();
  await navigator.clipboard.write([new ClipboardItem({ [blob.type]: blob })]);
  shareStatus.value = "Ledger card copied as an image.";
}

function downloadShareCard() {
  if (!shareCardUrl.value) {
    return;
  }
  const link = document.createElement("a");
  link.href = shareCardUrl.value;
  link.download = "carbonsnap-ledger-card.png";
  link.click();
}

async function load() {
  if (!isLoggedIn.value) {
    return;
  }

  loading.value = true;
  error.value = "";

  try {
    const [summaryData, gamificationData, transactionData, recordData] = await Promise.all([
      fetchLedgerSummary(token.value),
      fetchLedgerGamification(token.value),
      fetchLedgerTransactions({ page: 1, perPage: 15, token: token.value }),
      fetchLedgerRecords({ page: 1, perPage: 15, token: token.value }),
    ]);

    summary.value = summaryData;
    gamification.value = gamificationData;
    transactions.value = transactionData.items || [];
    records.value = recordData.items || [];

    const latestPoints = summaryData?.current_points ?? gamificationData?.current_points;
    if (latestPoints != null) {
      updateUser({ current_points: latestPoints });
    }
  } catch (err) {
    error.value = err instanceof Error ? err.message : "Failed to load ledger.";
  } finally {
    loading.value = false;
  }
}

onMounted(load);
</script>

<style scoped src="../../styles/views/ledger-view.css"></style>
