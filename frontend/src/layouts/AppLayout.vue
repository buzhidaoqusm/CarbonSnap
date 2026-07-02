<template>
  <div class="app-layout" :class="{ 'app-layout--home': variant === 'home' }" data-app-layout>
    <AppHeader
      :variant="variant"
      :is-authenticated="isAuthenticated"
      :avatar-url="avatarUrl"
      :avatar-alt="avatarAlt"
      :avatar-href="avatarHref"
      :points-label="pointsLabel"
    />

    <div class="app-layout__body" :class="{ 'app-layout__body--home': variant === 'home' }" data-app-layout-body>
      <AppShellSidebar
        v-if="showSidebar && variant !== 'home'"
        class="app-layout__sidebar"
        :is-authenticated="isAuthenticated"
        :user="user"
        :visible="showSidebar"
      />

      <main
        class="app-layout__main"
        :class="{ 'app-layout__main--full': !showSidebar || variant === 'home' }"
        data-app-layout-main
      >
        <slot />
      </main>
    </div>

    <AppFooter v-if="showFooter" />
  </div>
</template>

<script setup>
import { computed } from "vue";
import { headerBrand } from "../app/navigation/headerNavItems";
import AppFooter from "../components/common/AppFooter.vue";
import AppHeader from "../components/common/AppHeader.vue";
import AppShellSidebar from "../components/common/AppShellSidebar.vue";

const props = defineProps({
  isAuthenticated: {
    type: Boolean,
    default: false,
  },
  avatarUrl: {
    type: String,
    default: "",
  },
  avatarAlt: {
    type: String,
    default: "User avatar",
  },
  avatarHref: {
    type: String,
    default: "/profile",
  },
  variant: {
    type: String,
    default: "default",
  },
  showSidebar: {
    type: Boolean,
    default: true,
  },
  showFooter: {
    type: Boolean,
    default: true,
  },
  user: {
    type: Object,
    default: null,
  },
});

const pointsLabel = computed(() => {
  if (props.isAuthenticated && props.user?.current_points != null) {
    return `${props.user.current_points} pts`;
  }
  return "0 pts";
});
</script>

<style scoped>
.app-layout {
  min-height: 100dvh;
}

.app-layout__body {
  display: grid;
  width: min(var(--cs-shell-max-width), calc(100vw - 32px));
  margin: 18px auto 0;
  grid-template-columns: 280px minmax(0, 1fr);
  gap: 24px;
  align-items: start;
}

.app-layout__body--home {
  grid-template-columns: minmax(0, 1fr);
  width: min(1380px, calc(100vw - 32px));
}

.app-layout__sidebar {
  position: sticky;
  top: 112px;
}

.app-layout__main {
  min-width: 0;
}

.app-layout__main--full {
  grid-column: 1 / -1;
}

@media (max-width: 980px) {
  .app-layout__body {
    width: calc(100vw - 24px);
    grid-template-columns: minmax(0, 1fr);
  }

  .app-layout__sidebar {
    display: none;
  }
}

@media (max-width: 640px) {
  .app-layout__body,
  .app-layout__body--home {
    width: calc(100vw - 24px);
    margin-top: 14px;
  }
}
</style>
