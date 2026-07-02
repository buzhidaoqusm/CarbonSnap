<template>
  <header
    class="app-header"
    :class="{
      'app-header--home': variant === 'home',
      'app-header--fixed': positionMode === 'fixed',
      'app-header--static': positionMode === 'static',
    }"
    data-app-shell-topbar
  >
    <div class="app-header__inner">
      <div class="app-header__brand-group">
        <RouterLink class="app-header__brand" :to="brand.href" data-app-shell-brand>
          {{ brand.name }}
        </RouterLink>
        <nav class="app-header__nav" :aria-label="t('a11y.primaryNav')">
          <RouterLink
            v-for="item in visibleNavItems"
            :key="item.key"
            class="app-header__link"
            :class="{ 'app-header__link--active': isActive(item.href) }"
            :to="item.href"
            :data-app-shell-nav-item="item.key"
          >
            <span class="app-header__link-label">{{ item.label }}</span>
            <span
              v-if="item.key === 'notification' && notificationBadgeLabel"
              class="app-header__notification-badge"
              data-app-shell-notification-badge
            >
              {{ notificationBadgeLabel }}
            </span>
          </RouterLink>
        </nav>
      </div>

      <div class="app-header__actions" data-app-shell-actions>
        <button
          type="button"
          class="app-header__language"
          :aria-label="t('a11y.switchLanguage')"
          data-app-shell-language-toggle
          @click="toggleLocale"
        >
          <span>{{ localeLabel(locale) }}</span>
          <span aria-hidden="true">/</span>
          <strong>{{ localeLabel(nextLocale) }}</strong>
        </button>
        <RouterLink v-if="isSignedIn" class="app-header__points" to="/ledger" data-app-shell-points>
          <span class="app-header__points-dot"></span>
          <span>{{ pointsLabel }}</span>
        </RouterLink>
        <div
          ref="menuRoot"
          class="app-header__avatar-menu"
          data-app-shell-avatar-link
        >
          <button
            type="button"
            class="app-header__avatar-trigger"
            :aria-expanded="isMenuOpen ? 'true' : 'false'"
            :aria-label="isSignedIn ? t('a11y.openAccountMenu') : t('a11y.openProfile')"
            aria-haspopup="menu"
            @click="handleAvatarClick"
          >
            <img
              v-if="resolvedAvatarUrl"
              class="app-header__avatar"
              :src="resolvedAvatarUrl"
              :alt="avatarAlt"
            />
            <span v-else class="app-header__avatar-fallback">{{ avatarInitial }}</span>
            <span
              v-if="isSignedIn"
              class="app-header__avatar-chevron material-symbols-outlined"
              aria-hidden="true"
            >
              expand_more
            </span>
          </button>

          <Transition name="app-header-menu">
            <div
              v-if="isSignedIn && isMenuOpen"
              class="app-header__menu"
              role="menu"
              :aria-label="t('a11y.accountMenu')"
              data-app-shell-avatar-menu
            >
              <button
                v-for="item in avatarMenuItems"
                :key="item.key"
                type="button"
                class="app-header__menu-item"
                :class="{ 'app-header__menu-item--danger': item.key === 'logout' }"
                role="menuitem"
                :data-app-shell-avatar-action="item.key"
                @click="handleMenuAction(item.key)"
              >
                <span class="material-symbols-outlined" aria-hidden="true">{{ item.icon }}</span>
                <span>{{ item.label }}</span>
                <span
                  v-if="item.badge"
                  class="app-header__notification-badge"
                  data-app-shell-notification-badge
                >{{ item.badge }}</span>
              </button>
            </div>
          </Transition>
        </div>
      </div>
    </div>
  </header>
</template>

<script setup>
import {
  computed,
  inject,
  onBeforeUnmount,
  onMounted,
  ref,
  watch,
} from "vue";
import { RouterLink, routeLocationKey, routerKey } from "vue-router";
import {
  guestHeaderActions,
  headerBrand,
  primaryHeaderNavItems,
} from "../../app/navigation/headerNavItems";
import { resolveBackendUrl } from "../../api/http.js";
import { useAuth } from "../../composables/useAuth.js";
import { useNotifications } from "../../composables/useNotifications.js";
import { useI18n } from "../../i18n/index.js";

const props = defineProps({
  brand: {
    type: Object,
    default: () => headerBrand,
  },
  navItems: {
    type: Array,
    default: () => primaryHeaderNavItems,
  },
  guestActions: {
    type: Array,
    default: () => guestHeaderActions,
  },
  isAuthenticated: {
    type: [Boolean, Object],
    default: false,
  },
  avatarUrl: {
    type: String,
    default: "",
  },
  avatarHref: {
    type: String,
    default: "/profile",
  },
  avatarAlt: {
    type: String,
    default: "User avatar",
  },
  pointsLabel: {
    type: String,
    default: "Ledger",
  },
  variant: {
    type: String,
    default: "default",
  },
  positionMode: {
    type: String,
    default: "sticky",
    validator: (value) => ["sticky", "fixed", "static"].includes(value),
  },
});

const route = inject(routeLocationKey, null);
const router = inject(routerKey, null);
const currentPath = computed(() => route?.path || route?.value?.path || "/");
const { logout } = useAuth();
const { unreadCount } = useNotifications();
const { locale, nextLocale, toggleLocale, t, localeLabel } = useI18n();

const isMenuOpen = ref(false);
const menuRoot = ref(null);

const avatarInitial = computed(() => {
  const source = props.avatarAlt.trim();
  return source ? source.charAt(0).toUpperCase() : "U";
});
const resolvedAvatarUrl = computed(() => resolveBackendUrl(props.avatarUrl));

const visibleNavItems = computed(() => props.navItems.map((item) => ({
  ...item,
  label: t(`nav.${item.key}`),
})));
const notificationBadgeLabel = computed(() => {
  const count = Number(unreadCount.value || 0);
  if (count <= 0) {
    return "";
  }
  return count > 99 ? "99+" : String(count);
});
const isSignedIn = computed(() => {
  const source = props.isAuthenticated;
  if (source && typeof source === "object" && "value" in source) {
    return Boolean(source.value);
  }
  return Boolean(source);
});

const avatarMenuItems = computed(() => ([
  { key: "profile", label: t("nav.profile"), href: props.avatarHref || "/profile", icon: "person" },
  { key: "ledger", label: t("nav.ledger"), href: "/ledger", icon: "receipt_long" },
  { key: "notification", label: t("nav.notifications"), href: "/notification", icon: "notifications", badge: notificationBadgeLabel.value },
  { key: "logout", label: t("nav.logout"), href: "/login", icon: "logout" },
]));

function isActive(href) {
  return currentPath.value === href || (href !== "/" && currentPath.value.startsWith(href));
}

function closeMenu() {
  isMenuOpen.value = false;
}

function openPath(href) {
  closeMenu();
  if (!href) {
    return;
  }

  if (router?.push) {
    router.push(href);
    return;
  }

  if (typeof window !== "undefined") {
    window.location.assign(href);
  }
}

function handleAvatarClick() {
  if (!isSignedIn.value) {
    openPath(props.avatarHref || "/login");
    return;
  }

  isMenuOpen.value = !isMenuOpen.value;
}

function handleMenuAction(key) {
  if (key === "logout") {
    logout?.();
    openPath("/login");
    return;
  }

  const item = avatarMenuItems.value.find((entry) => entry.key === key);
  openPath(item?.href || "/");
}

function handleDocumentPointerDown(event) {
  if (!isMenuOpen.value || !menuRoot.value) {
    return;
  }

  if (menuRoot.value.contains(event.target)) {
    return;
  }

  closeMenu();
}

function handleDocumentKeydown(event) {
  if (event.key === "Escape") {
    closeMenu();
  }
}

watch(currentPath, () => {
  closeMenu();
});

onMounted(() => {
  document.addEventListener("pointerdown", handleDocumentPointerDown);
  document.addEventListener("keydown", handleDocumentKeydown);
});

onBeforeUnmount(() => {
  document.removeEventListener("pointerdown", handleDocumentPointerDown);
  document.removeEventListener("keydown", handleDocumentKeydown);
});
</script>

<style scoped>
.app-header {
  position: sticky;
  top: 0;
  z-index: 50;
  padding: 22px 16px 0;
}

.app-header--fixed {
  position: fixed;
  left: 0;
  right: 0;
  width: 100%;
}

.app-header--static {
  position: relative;
  top: auto;
  left: auto;
  right: auto;
  width: auto;
}

.app-header__inner {
  display: flex;
  width: min(var(--cs-shell-max-width), calc(100vw - 32px));
  margin: 0 auto;
  align-items: center;
  justify-content: space-between;
  gap: 20px;
  border: 1px solid rgba(170, 174, 172, 0.32);
  border-radius: 999px;
  background: rgba(243, 247, 245, 0.9);
  box-shadow: 0 8px 32px rgba(43, 48, 47, 0.06);
  backdrop-filter: blur(20px);
  padding: 14px 18px 14px 28px;
}

.app-header__brand-group,
.app-header__actions,
.app-header__nav {
  display: flex;
  align-items: center;
}

.app-header__brand-group {
  gap: 28px;
  min-width: 0;
}

.app-header__brand {
  color: var(--cs-primary);
  font-family: var(--cs-font-heading);
  font-size: 1.35rem;
  font-weight: 800;
  letter-spacing: -0.04em;
  text-decoration: none;
}

.app-header__nav {
  gap: 6px;
  flex-wrap: wrap;
}

.app-header__link {
  align-items: center;
  border-radius: 999px;
  color: var(--cs-text-muted);
  display: inline-flex;
  gap: 8px;
  padding: 12px 18px;
  font-size: 0.92rem;
  font-weight: 700;
  text-decoration: none;
  transition: background-color 180ms ease, color 180ms ease;
}

.app-header__link:hover,
.app-header__link:focus-visible {
  background: rgba(255, 255, 255, 0.88);
  color: var(--cs-text);
  outline: none;
}

.app-header__link--active {
  background: rgba(255, 255, 255, 0.96);
  color: #324600;
  box-shadow: inset 0 0 0 1px rgba(255, 255, 255, 0.9);
}

.app-header__link-label {
  min-width: 0;
}

.app-header__notification-badge {
  align-items: center;
  background: var(--cs-primary);
  border-radius: 999px;
  color: #f4fff1;
  display: inline-flex;
  font-size: 0.72rem;
  font-weight: 800;
  height: 20px;
  justify-content: center;
  line-height: 1;
  min-width: 20px;
  padding: 0 6px;
}

.app-header__actions {
  gap: 12px;
}

.app-header__language {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  border: 1px solid rgba(170, 174, 172, 0.36);
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.82);
  color: var(--cs-text-muted);
  cursor: pointer;
  font-size: 0.82rem;
  font-weight: 800;
  padding: 10px 12px;
  transition: background-color 180ms ease, color 180ms ease, border-color 180ms ease;
  white-space: nowrap;
}

.app-header__language strong {
  color: var(--cs-primary);
  font-weight: 900;
}

.app-header__language:hover,
.app-header__language:focus-visible {
  background: rgba(255, 255, 255, 0.96);
  border-color: rgba(38, 104, 41, 0.24);
  color: var(--cs-text);
  outline: none;
}

.app-header__points {
  display: inline-flex;
  align-items: center;
  gap: 10px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.92);
  color: var(--cs-text);
  padding: 12px 16px;
  font-size: 0.9rem;
  font-weight: 800;
  text-decoration: none;
}

.app-header__points-dot {
  width: 10px;
  height: 10px;
  border-radius: 999px;
  background: var(--cs-primary);
}

.app-header__avatar-menu {
  position: relative;
}

.app-header__avatar-trigger {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  border: 0;
  background: transparent;
  cursor: pointer;
  padding: 0;
}

.app-header__avatar-trigger:focus-visible {
  outline: 2px solid rgba(50, 70, 0, 0.28);
  outline-offset: 4px;
  border-radius: 999px;
}

.app-header__avatar,
.app-header__avatar-fallback {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 48px;
  height: 48px;
  border: 2px solid rgba(38, 104, 41, 0.14);
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.92);
}

.app-header__avatar {
  object-fit: cover;
}

.app-header__avatar-fallback {
  color: var(--cs-primary);
  font-family: var(--cs-font-heading);
  font-weight: 800;
}

.app-header__avatar-chevron {
  color: var(--cs-text-muted);
  font-size: 1.15rem;
  transition: transform 180ms ease, color 180ms ease;
}

.app-header__avatar-trigger[aria-expanded="true"] .app-header__avatar-chevron {
  color: var(--cs-text);
  transform: rotate(180deg);
}

.app-header__menu {
  position: absolute;
  top: calc(100% + 12px);
  right: 0;
  z-index: 60;
  min-width: 196px;
  border: 1px solid rgba(170, 174, 172, 0.35);
  border-radius: 24px;
  background: rgba(248, 250, 248, 0.98);
  box-shadow: 0 20px 48px rgba(43, 48, 47, 0.14);
  backdrop-filter: blur(18px);
  padding: 10px;
}

.app-header__menu-item {
  display: flex;
  width: 100%;
  align-items: center;
  gap: 12px;
  border: 0;
  border-radius: 18px;
  background: transparent;
  color: var(--cs-text);
  cursor: pointer;
  font-size: 0.92rem;
  font-weight: 700;
  padding: 12px 14px;
  text-align: left;
  transition: transform 180ms ease, background-color 180ms ease, color 180ms ease;
}

.app-header__menu-item:hover,
.app-header__menu-item:focus-visible {
  background: rgba(255, 255, 255, 0.94);
  color: #324600;
  outline: none;
  transform: translateX(2px);
}

.app-header__menu-item--danger {
  color: #8d2c2c;
}

.app-header__menu-item--danger:hover,
.app-header__menu-item--danger:focus-visible {
  color: #7a2323;
  background: rgba(255, 240, 240, 0.96);
}

.app-header-menu-enter-active,
.app-header-menu-leave-active {
  transition: opacity 180ms ease, transform 220ms ease;
  transform-origin: top right;
}

.app-header-menu-enter-from,
.app-header-menu-leave-to {
  opacity: 0;
  transform: translateY(-10px) scale(0.96);
}

.app-header-menu-enter-to,
.app-header-menu-leave-from {
  opacity: 1;
  transform: translateY(0) scale(1);
}

@media (prefers-reduced-motion: reduce) {
  .app-header__link,
  .app-header__language,
  .app-header__avatar-chevron,
  .app-header__menu-item,
  .app-header-menu-enter-active,
  .app-header-menu-leave-active {
    transition: none;
  }
}

@media (max-width: 1100px) {
  .app-header__inner {
    border-radius: 28px;
    padding: 16px 18px;
  }

  .app-header__brand-group {
    flex-wrap: wrap;
    gap: 12px;
  }
}

@media (max-width: 820px) {
  .app-header__inner {
    width: calc(100vw - 24px);
    flex-direction: column;
    align-items: stretch;
  }

  .app-header__brand-group,
  .app-header__actions {
    justify-content: space-between;
  }

  .app-header__nav {
    width: 100%;
  }
}

@media (max-width: 640px) {
  .app-header {
    padding: 12px 12px 0;
  }

  .app-header__actions {
    flex-wrap: wrap;
  }

  .app-header__points {
    flex: 1 1 0;
    justify-content: center;
  }

  .app-header__menu {
    right: 0;
    min-width: min(220px, calc(100vw - 32px));
  }
}
</style>
