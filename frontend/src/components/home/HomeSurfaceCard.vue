<template>
  <article class="home-surface-card panel">
    <p class="cs-eyebrow">{{ eyebrow }}</p>
    <h2>{{ title }}</h2>

    <RouterLink class="cs-button cs-button--secondary home-surface-card__cta" :to="to">
      {{ ctaLabel }}
    </RouterLink>
  </article>
</template>

<script setup>
import { RouterLink } from "vue-router";

defineProps({
  eyebrow: {
    type: String,
    required: true,
  },
  title: {
    type: String,
    required: true,
  },
  ctaLabel: {
    type: String,
    required: true,
  },
  to: {
    type: String,
    required: true,
  },
});
</script>

<style scoped>
.home-surface-card {
  display: grid;
  gap: 14px;
  align-content: start;
  min-height: 100%;
  transition:
    transform 200ms ease,
    box-shadow 200ms ease,
    border-color 200ms ease;
}

.home-surface-card:hover {
  transform: translateY(-2px);
}

.home-surface-card h2 {
  font-size: clamp(1.2rem, 1.8vw, 1.6rem);
  line-height: 1.1;
  max-width: 20ch;
}

.home-surface-card__cta {
  justify-self: start;
  margin-top: 4px;
}

@media (max-width: 640px) {
  .home-surface-card__cta {
    width: 100%;
  }
}
</style>
