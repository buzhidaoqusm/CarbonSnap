<template>
  <RouterView />
  <NotificationToastStack
    :toasts="toasts"
    @dismiss="dismissToast"
    @open="handleToastOpen"
  />
</template>

<script setup>
import { nextTick, onBeforeUnmount, onMounted, watch } from "vue";
import { RouterView, useRouter } from "vue-router";

import NotificationToastStack from "./components/common/NotificationToastStack.vue";
import { useAuth } from "./composables/useAuth.js";
import { useNotifications } from "./composables/useNotifications.js";
import { useToast } from "./composables/useToast.js";
import { applyStaticLocale, useI18n } from "./i18n/index.js";

const router = useRouter();
const { isLoggedIn, refreshCurrentUser } = useAuth();
const { openNotification, start, stop } = useNotifications();
const { toasts, dismissToast } = useToast();
const { locale } = useI18n();
let staticLocaleObserver = null;

async function handleToastOpen(notification) {
  if (notification?.kind !== "notification") {
    dismissToast(notification?.id);
    return;
  }

  const target = await openNotification(notification.notification || notification);
  if (target) {
    router.push(target);
  }
}

watch(
  () => isLoggedIn.value,
  (loggedIn) => {
    if (loggedIn) {
      void refreshCurrentUser().catch(() => {
        stop();
      });
      void start();
    } else {
      stop();
    }
  },
  {
    immediate: true,
  },
);

watch(
  locale,
  () => {
    nextTick(() => applyStaticLocale());
  },
  { immediate: true },
);

onMounted(() => {
  applyStaticLocale();
  staticLocaleObserver = new MutationObserver(() => {
    applyStaticLocale();
  });
  staticLocaleObserver.observe(document.body, {
    childList: true,
    subtree: true,
  });
});

onBeforeUnmount(() => {
  stop();
  staticLocaleObserver?.disconnect();
});
</script>
