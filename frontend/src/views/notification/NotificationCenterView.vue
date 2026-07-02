<template>
  <div class="notification-view bg-surface text-on-surface min-h-screen flex flex-col">
    <AppHeader
      :is-authenticated="isLoggedIn"
      :avatar-alt="avatarAlt"
      :avatar-href="avatarTarget"
      :avatar-url="avatarUrl"
      :points-label="`${creditsDisplay} pts`"
    />

    <div class="flex flex-1 flex-col">
      <main class="min-w-0 flex-1 overflow-y-auto p-6 md:p-10 pb-24 md:pb-12">
        <div class="mx-auto w-full max-w-5xl">
          <header class="mb-10">
            <h1 class="text-4xl font-headline font-black text-on-background tracking-tighter">Activity Stream</h1>
            <p class="text-on-surface-variant mt-2 font-body">Your environmental impact footprint and community updates.</p>
          </header>

          <p
            v-if="!isLoggedIn"
            class="mb-8 rounded-[2rem] border border-surface-container-high bg-white/80 p-6 text-sm text-on-surface-variant shadow-sm"
          >
            <RouterLink class="font-bold text-primary" to="/login">Sign in</RouterLink>
            to view your personal notification stream.
          </p>

          <template v-else>
            <div class="grid grid-cols-1 lg:grid-cols-3 gap-8">
              <div class="lg:col-span-2 space-y-8">
                <section class="space-y-6" data-notification-hero>
                  <div class="flex items-center justify-between px-2">
                    <h2 class="text-sm font-bold uppercase tracking-widest text-primary flex items-center gap-2">
                      <span class="material-symbols-outlined text-lg">notifications_active</span>
                      Live Updates
                    </h2>
                    <span class="text-[10px] bg-primary-container text-on-primary-container px-2 py-0.5 rounded-full font-bold uppercase">
                      Live
                    </span>
                  </div>

                  <div class="relative flex h-[500px] w-full flex-col p-2 overflow-hidden rounded-2xl border border-surface-container-high bg-surface-container-lowest shadow-sm">
                    <transition-group
                      v-if="visibleNotifications.length"
                      name="notification-list"
                      tag="div"
                      class="flex flex-col-reverse gap-y-3 overflow-y-auto pr-2 custom-scrollbar"
                      data-notification-list
                    >
                      <button
                        v-for="notification in visibleNotifications"
                        :key="notification.id"
                        class="flex w-full items-center gap-4 rounded-xl border border-surface-container-high bg-white p-4 transition-all hover:scale-[1.02] cursor-pointer text-left"
                        type="button"
                        data-notification-card
                        @click="handleOpenNotification(notification)"
                      >
                        <div
                          class="flex h-10 w-10 items-center justify-center rounded-lg text-white"
                          :style="{ backgroundColor: notificationColor(notification) }"
                        >
                          <span class="material-symbols-outlined">{{ notificationIcon(notification) }}</span>
                        </div>
                        <div class="flex flex-col overflow-hidden">
                          <div class="flex flex-row items-center whitespace-pre text-sm font-bold text-on-surface font-headline">
                            <span>{{ notificationLabel(notification) }}</span>
                            <span class="mx-1">|</span>
                            <span class="text-[10px] text-outline font-normal">{{ formatRelativeTime(notification.created_at) }}</span>
                          </div>
                          <p class="text-xs text-on-surface-variant font-body">
                            {{ notificationBody(notification) }}
                          </p>
                        </div>
                      </button>
                    </transition-group>

                    <div v-else class="flex flex-1 items-center justify-center rounded-[1.5rem] border border-dashed border-outline-variant/30 bg-white/60 p-6 text-sm text-on-surface-variant">
                      No notifications yet
                    </div>

                    <div class="pointer-events-none absolute inset-x-0 bottom-0 h-20 bg-gradient-to-t from-surface-container-lowest"></div>
                  </div>
                </section>
              </div>

              <aside class="space-y-6">
                <div class="bg-surface-container-low p-6 rounded-3xl sticky top-32">
                  <h3 class="font-headline font-bold text-xl mb-4">Preferences</h3>
                  <div class="space-y-6">
                    <div class="flex items-center justify-between">
                      <div>
                        <h5 class="text-sm font-bold text-on-surface">Push Notifications</h5>
                        <p class="text-[10px] text-on-surface-variant">Immediate mobile alerts</p>
                      </div>
                      <div class="w-10 h-5 bg-secondary-fixed rounded-full relative cursor-pointer" aria-hidden="true">
                        <div class="absolute right-1 top-1 w-3 h-3 bg-on-secondary-fixed rounded-full"></div>
                      </div>
                    </div>

                    <div class="flex items-center justify-between opacity-80">
                      <div>
                        <h5 class="text-sm font-bold text-on-surface">Email Digest</h5>
                        <p class="text-[10px] text-on-surface-variant">Weekly impact summary</p>
                      </div>
                      <div class="w-10 h-5 bg-outline-variant rounded-full relative cursor-pointer" aria-hidden="true">
                        <div class="absolute left-1 top-1 w-3 h-3 bg-surface-container-lowest rounded-full"></div>
                      </div>
                    </div>

                    <hr class="border-outline-variant/20" />

                    <div>
                      <h5 class="text-xs font-bold uppercase tracking-tighter text-outline mb-3">Alert Types</h5>
                      <div class="space-y-3">
                        <label class="flex items-center gap-3 cursor-pointer">
                          <input checked class="rounded border-outline-variant text-primary focus:ring-primary w-4 h-4" type="checkbox" />
                          <span class="text-sm font-medium text-on-surface-variant">Social Mentions</span>
                        </label>
                        <label class="flex items-center gap-3 cursor-pointer">
                          <input checked class="rounded border-outline-variant text-primary focus:ring-primary w-4 h-4" type="checkbox" />
                          <span class="text-sm font-medium text-on-surface-variant">Market Updates</span>
                        </label>
                        <label class="flex items-center gap-3 cursor-pointer">
                          <input checked class="rounded border-outline-variant text-primary focus:ring-primary w-4 h-4" type="checkbox" />
                          <span class="text-sm font-medium text-on-surface-variant">Audit Results</span>
                        </label>
                      </div>
                    </div>

                  </div>
                </div>
              </aside>
            </div>
          </template>
        </div>
      </main>
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
import { computed } from "vue";
import { RouterLink, useRouter } from "vue-router";

import AppHeader from "../../components/common/AppHeader.vue";
import { useNotifications } from "../../composables/useNotifications.js";
import { useAuth } from "../../composables/useAuth.js";

const { isLoggedIn, user } = useAuth();
const router = useRouter();
const { notifications, openNotification } = useNotifications();

const avatarAlt = computed(() => user.value?.username || "User Profile");
const avatarUrl = computed(() => user.value?.avatar_url || "");
const avatarTarget = computed(() => (isLoggedIn.value ? "/profile" : "/login"));
const creditsDisplay = computed(() => formatNumber(user.value?.current_points ?? 0));

const visibleNotifications = computed(() =>
  [...notifications.value]
    .sort((left, right) => Date.parse(right.created_at || "") - Date.parse(left.created_at || ""))
    .slice(0, 5),
);

function formatNumber(value) {
  const parsed = Number(value);
  if (Number.isNaN(parsed)) {
    return "0";
  }
  return parsed.toLocaleString();
}

function formatRelativeTime(value) {
  const time = Date.parse(value || "");
  if (Number.isNaN(time)) {
    return value || "";
  }

  const diffMinutes = Math.round((Date.now() - time) / 60000);
  if (diffMinutes < 1) {
    return "Just now";
  }
  if (diffMinutes < 60) {
    return `${diffMinutes}m ago`;
  }

  const diffHours = Math.round(diffMinutes / 60);
  if (diffHours < 24) {
    return `${diffHours}h ago`;
  }

  const diffDays = Math.round(diffHours / 24);
  return `${diffDays}d ago`;
}

function notificationLabel(notification) {
  return notification.title || formatEventLabel(notification.event_type);
}

function notificationBody(notification) {
  return notification.body || notification.description || fallbackNotificationBody(notification);
}

function fallbackNotificationBody(notification) {
  const eventType = String(notification.event_type || "").toLowerCase();
  if (eventType.includes("audit")) {
    return "AI verified your last snap";
  }
  if (eventType.includes("order")) {
    return "Bamboo Toothbrush shipped";
  }
  if (eventType.includes("project")) {
    return "Amazon Reforestation hit 80%";
  }
  if (eventType.includes("follow")) {
    return "Eco-Hero Alex joined your circle";
  }
  if (eventType.includes("credit")) {
    return "Verified Glass Recycling";
  }
  return "Open the linked route for the full update.";
}

function formatEventLabel(eventType) {
  return String(eventType || "activity")
    .replace(/_/g, " ")
    .replace(/\b\w/g, (character) => character.toUpperCase());
}

function notificationIcon(notification) {
  const eventType = String(notification.event_type || notification.source_type || "").toLowerCase();
  if (eventType.includes("audit")) {
    return "check_circle";
  }
  if (eventType.includes("order")) {
    return "package_2";
  }
  if (eventType.includes("project")) {
    return "forest";
  }
  if (eventType.includes("follow")) {
    return "person";
  }
  if (eventType.includes("credit")) {
    return "payments";
  }
  return "notifications";
}

function notificationColor(notification) {
  const eventType = String(notification.event_type || notification.source_type || "").toLowerCase();
  if (eventType.includes("audit")) {
    return "#45B26B";
  }
  if (eventType.includes("order")) {
    return "#1E86FF";
  }
  if (eventType.includes("project")) {
    return "#FF3D71";
  }
  if (eventType.includes("follow")) {
    return "#FFB800";
  }
  if (eventType.includes("credit")) {
    return "#00C9A7";
  }
  return "#266829";
}

async function handleOpenNotification(notification) {
  const target = await openNotification(notification);
  router.push(target || "/notification");
}
</script>

<style scoped src="../../styles/views/notification-view.css"></style>
