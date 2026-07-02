<template>
  <aside
    v-if="visible"
    class="app-shell-sidebar"
    data-app-shell-sidebar
  >
    <div class="app-shell-sidebar__account">
      <p class="app-shell-sidebar__label">{{ t("sidebar.accountHealth") }}</p>
      <h2 class="app-shell-sidebar__title">
        {{ accountTitle }}
      </h2>
      <p class="app-shell-sidebar__copy">
        {{ accountCopy }}
      </p>
    </div>

    <section class="app-shell-sidebar__section">
      <p class="app-shell-sidebar__section-label">{{ pageContext.eyebrow }}</p>
      <h2 class="app-shell-sidebar__section-title">{{ pageContext.title }}</h2>
      <p class="app-shell-sidebar__section-copy">{{ pageContext.copy }}</p>
    </section>

    <section class="app-shell-sidebar__section">
      <p class="app-shell-sidebar__section-label">{{ t("sidebar.inThisSpace") }}</p>
      <ul class="app-shell-sidebar__list">
        <li
          v-for="item in pageContext.items"
          :key="item"
          class="app-shell-sidebar__list-item"
        >
          <span class="app-shell-sidebar__dot"></span>
          <span>{{ item }}</span>
        </li>
      </ul>
    </section>

    <section v-if="pageContext.links.length" class="app-shell-sidebar__section">
      <p class="app-shell-sidebar__section-label">{{ t("sidebar.quickLinks") }}</p>
      <div class="app-shell-sidebar__links">
        <RouterLink
          v-for="link in pageContext.links"
          :key="link.href"
          class="app-shell-sidebar__link"
          :class="{ 'app-shell-sidebar__link--active': isActive(link.href) }"
          :to="link.href"
        >
          <span>{{ link.label }}</span>
        </RouterLink>
      </div>
    </section>

    <div class="app-shell-sidebar__footer">
      <RouterLink class="app-shell-sidebar__cta" to="/ai">
        AI Snap
      </RouterLink>
    </div>
  </aside>
</template>

<script setup>
import { computed } from "vue";
import { RouterLink, useRoute } from "vue-router";
import { useI18n } from "../../i18n/index.js";

const props = defineProps({
  isAuthenticated: {
    type: Boolean,
    default: false,
  },
  user: {
    type: Object,
    default: null,
  },
  visible: {
    type: Boolean,
    default: true,
  },
});

const route = useRoute();
const { t } = useI18n();

const accountTitle = computed(() => {
  if (!props.isAuthenticated) {
    return t("sidebar.guestMode");
  }
  return props.user?.username ? `${props.user.username}` : t("sidebar.impactSeedling");
});

const accountCopy = computed(() => {
  if (!props.isAuthenticated) {
    return t("sidebar.guestCopy");
  }

  const points = props.user?.current_points;
  if (points != null) {
    return t("sidebar.pointsCopy", { points });
  }

  return t("sidebar.accountCopy");
});

const pageContext = computed(() => {
  if (route.path.startsWith("/forum")) {
    return {
      eyebrow: t("sidebar.forumEyebrow"),
      title: t("sidebar.forumTitle"),
      copy: t("sidebar.forumCopy"),
      items: [
        t("sidebar.forumItem1"),
        t("sidebar.forumItem2"),
        t("sidebar.forumItem3"),
      ],
      links: [
        { label: t("sidebar.openMarket"), href: "/market" },
        { label: t("sidebar.openAi"), href: "/ai" },
      ],
    };
  }

  if (route.path.startsWith("/market")) {
    return {
      eyebrow: t("sidebar.marketEyebrow"),
      title: t("sidebar.marketTitle"),
      copy: t("sidebar.marketCopy"),
      items: [
        t("sidebar.marketItem1"),
        t("sidebar.marketItem2"),
        t("sidebar.marketItem3"),
      ],
      links: [
        { label: t("sidebar.myOrders"), href: "/market/orders" },
        { label: t("sidebar.forumIdeas"), href: "/forum" },
      ],
    };
  }

  if (route.path.startsWith("/ledger")) {
    return {
      eyebrow: t("sidebar.ledgerEyebrow"),
      title: t("sidebar.ledgerTitle"),
      copy: t("sidebar.ledgerCopy"),
      items: [
        t("sidebar.ledgerItem1"),
        t("sidebar.ledgerItem2"),
        props.isAuthenticated
          ? t("sidebar.ledgerItemSignedIn", { points: props.user?.current_points ?? 0 })
          : t("sidebar.ledgerItemSignedOut"),
      ],
      links: [
        { label: t("sidebar.openAi"), href: "/ai" },
        { label: t("sidebar.openMarket"), href: "/market" },
      ],
    };
  }

  if (route.path.startsWith("/notification")) {
    return {
      eyebrow: t("sidebar.notificationEyebrow"),
      title: t("sidebar.notificationTitle"),
      copy: t("sidebar.notificationCopy"),
      items: [
        t("sidebar.notificationItem1"),
        t("sidebar.notificationItem2"),
        t("sidebar.notificationItem3"),
      ],
      links: [
        { label: t("sidebar.openForum"), href: "/forum" },
        { label: t("sidebar.openOrders"), href: "/market/orders" },
      ],
    };
  }

  if (route.path.startsWith("/project")) {
    return {
      eyebrow: t("sidebar.projectEyebrow"),
      title: t("sidebar.projectTitle"),
      copy: t("sidebar.projectCopy"),
      items: [
        t("sidebar.projectItem1"),
        t("sidebar.projectItem2"),
        t("sidebar.projectItem3"),
      ],
      links: [
        { label: t("sidebar.openForum"), href: "/forum" },
        { label: t("sidebar.openMarket"), href: "/market" },
      ],
    };
  }

  if (route.path.startsWith("/profile")) {
    return {
      eyebrow: t("sidebar.profileEyebrow"),
      title: t("sidebar.profileTitle"),
      copy: t("sidebar.profileCopy"),
      items: [
        t("sidebar.profileItem1"),
        t("sidebar.profileItem2"),
        t("sidebar.profileItem3"),
      ],
      links: [
        { label: t("sidebar.openLedger"), href: "/ledger" },
        { label: t("sidebar.openNotifications"), href: "/notification" },
      ],
    };
  }

  return {
    eyebrow: t("sidebar.workspaceEyebrow"),
    title: t("sidebar.workspaceTitle"),
    copy: t("sidebar.workspaceCopy"),
    items: [
      t("sidebar.workspaceItem1"),
      t("sidebar.workspaceItem2"),
      t("sidebar.workspaceItem3"),
    ],
    links: [{ label: t("sidebar.openAi"), href: "/ai" }],
  };
});

function isActive(href) {
  return route.path === href || (href !== "/" && route.path.startsWith(href));
}
</script>

<style scoped>
.app-shell-sidebar {
  display: flex;
  min-height: calc(100dvh - 110px);
  flex-direction: column;
  gap: 18px;
  border: 1px solid var(--cs-outline);
  border-radius: 28px;
  background: rgba(237, 242, 240, 0.84);
  box-shadow: var(--cs-shadow-soft);
  padding: 22px 18px 18px;
}

.app-shell-sidebar__account {
  display: grid;
  gap: 8px;
  border-radius: 22px;
  background: rgba(255, 255, 255, 0.82);
  padding: 18px;
}

.app-shell-sidebar__label {
  color: var(--cs-text-soft);
  font-size: 0.76rem;
  font-weight: 800;
  letter-spacing: 0.18em;
  text-transform: uppercase;
}

.app-shell-sidebar__title {
  font-size: 1.2rem;
}

.app-shell-sidebar__copy {
  color: var(--cs-text-muted);
  font-size: 0.94rem;
  line-height: 1.55;
}

.app-shell-sidebar__section {
  display: grid;
  gap: 10px;
}

.app-shell-sidebar__section-label {
  color: var(--cs-text-soft);
  font-size: 0.76rem;
  font-weight: 800;
  letter-spacing: 0.18em;
  text-transform: uppercase;
}

.app-shell-sidebar__section-title {
  font-size: 1.08rem;
}

.app-shell-sidebar__section-copy {
  color: var(--cs-text-muted);
  font-size: 0.94rem;
  line-height: 1.6;
}

.app-shell-sidebar__list {
  display: grid;
  gap: 12px;
  list-style: none;
  margin: 0;
  padding: 0;
}

.app-shell-sidebar__list-item {
  display: grid;
  grid-template-columns: 9px minmax(0, 1fr);
  gap: 12px;
  align-items: start;
  color: var(--cs-text-muted);
  line-height: 1.55;
}

.app-shell-sidebar__links {
  display: grid;
  gap: 8px;
}

.app-shell-sidebar__link {
  display: flex;
  align-items: center;
  border-radius: 18px;
  color: var(--cs-text-muted);
  padding: 12px 14px;
  text-decoration: none;
  transition: transform 180ms ease, background-color 180ms ease, color 180ms ease;
}

.app-shell-sidebar__link:hover,
.app-shell-sidebar__link:focus-visible {
  background: rgba(255, 255, 255, 0.82);
  color: var(--cs-text);
  transform: translateX(2px);
  outline: none;
}

.app-shell-sidebar__link--active {
  background: rgba(255, 255, 255, 0.96);
  color: var(--cs-primary);
  box-shadow: 0 12px 24px rgba(43, 48, 47, 0.05);
}

.app-shell-sidebar__dot {
  width: 9px;
  height: 9px;
  border-radius: 999px;
  background: currentColor;
  opacity: 0.5;
}

.app-shell-sidebar__footer {
  margin-top: auto;
}

.app-shell-sidebar__cta {
  display: inline-flex;
  width: 100%;
  align-items: center;
  justify-content: center;
  border-radius: 999px;
  background: var(--cs-accent);
  color: #324600;
  padding: 12px 16px;
  font-weight: 800;
  text-decoration: none;
}
</style>
