<template>
  <footer class="app-footer" data-app-shell-footer>
    <div class="app-footer__inner">
      <section class="app-footer__brand-block">
        <RouterLink class="app-footer__brand" to="/">{{ brand.name }}</RouterLink>
        <p class="app-footer__description">{{ footerDescription }}</p>
      </section>

      <section
        v-for="section in sections"
        :key="section.key"
        class="app-footer__section"
      >
        <h2 class="app-footer__heading">{{ section.title }}</h2>
        <nav class="app-footer__links" :aria-label="section.title">
          <RouterLink
            v-for="link in section.links"
            :key="link.key"
            class="app-footer__link"
            :to="link.href"
          >
            {{ link.label }}
          </RouterLink>
        </nav>
      </section>
    </div>
    <p class="app-footer__copyright">
      Copyright {{ year }} CarbonSnap. {{ t("footer.copyright") }}
    </p>
  </footer>
</template>

<script setup>
import { computed } from "vue";
import { RouterLink } from "vue-router";
import {
  footerBrand,
  footerNavSections,
} from "../../app/navigation/footerNavSections";
import { useI18n } from "../../i18n/index.js";

const props = defineProps({
  brand: {
    type: Object,
    default: () => footerBrand,
  },
  sections: {
    type: Array,
    default: () => footerNavSections,
  },
});

const year = computed(() => new Date().getFullYear());
const { t } = useI18n();
const footerDescription = computed(() => t("footer.description"));
const sections = computed(() => props.sections.map((section) => ({
  ...section,
  title: t(`footer.${section.key}`),
  links: section.links.map((link) => ({
    ...link,
    label: t(`nav.${link.key}`),
  })),
})));
</script>

<style scoped>
.app-footer {
  margin-top: 32px;
  padding: 0 16px 28px;
}

.app-footer__inner,
.app-footer__copyright {
  width: min(var(--cs-shell-max-width), calc(100vw - 32px));
  margin-left: auto;
  margin-right: auto;
}

.app-footer__inner {
  display: grid;
  grid-template-columns: minmax(260px, 1.2fr) repeat(2, minmax(180px, 1fr));
  gap: 24px;
  border: 1px solid var(--cs-outline);
  border-radius: 32px;
  background: rgba(255, 255, 255, 0.84);
  box-shadow: var(--cs-shadow-soft);
  padding: 28px;
}

.app-footer__brand-block {
  display: grid;
  gap: 12px;
}

.app-footer__brand {
  color: var(--cs-primary);
  font-family: var(--cs-font-heading);
  font-size: 1.45rem;
  font-weight: 800;
  letter-spacing: -0.04em;
  text-decoration: none;
}

.app-footer__description,
.app-footer__copyright {
  color: var(--cs-text-muted);
  line-height: 1.6;
}

.app-footer__section {
  display: grid;
  align-content: start;
  gap: 14px;
}

.app-footer__heading {
  font-size: 0.88rem;
  letter-spacing: 0.18em;
  text-transform: uppercase;
}

.app-footer__links {
  display: grid;
  gap: 10px;
}

.app-footer__link {
  color: var(--cs-text);
  font-weight: 700;
  text-decoration: none;
}

.app-footer__link:hover,
.app-footer__link:focus-visible {
  color: var(--cs-primary);
  outline: none;
}

.app-footer__copyright {
  margin-top: 14px;
  text-align: center;
}

@media (max-width: 820px) {
  .app-footer__inner {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 640px) {
  .app-footer {
    padding-left: 12px;
    padding-right: 12px;
  }

  .app-footer__inner,
  .app-footer__copyright {
    width: calc(100vw - 24px);
  }

  .app-footer__inner {
    padding: 22px 18px;
  }
}
</style>
