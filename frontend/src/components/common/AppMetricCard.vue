<template>
  <article class="app-metric-card" data-app-metric-card>
    <p class="app-metric-card__label">{{ label }}</p>
    <h3 class="app-metric-card__value">{{ value }}</h3>
    <p v-if="hint" class="app-metric-card__hint">{{ hint }}</p>
  </article>
</template>

<script setup>
defineProps({
  label: {
    type: String,
    required: true,
  },
  value: {
    type: String,
    required: true,
  },
  hint: {
    type: String,
    default: "",
  },
});
</script>

<style scoped>
.app-metric-card {
  display: grid;
  gap: 10px;
  border: 1px solid var(--cs-outline);
  border-radius: 28px;
  background: rgba(255, 255, 255, 0.88);
  padding: 22px;
  box-shadow: var(--cs-shadow-soft);
}

.app-metric-card__label {
  color: var(--cs-text-soft);
  font-size: 0.74rem;
  font-weight: 800;
  letter-spacing: 0.18em;
  text-transform: uppercase;
}

.app-metric-card__value {
  font-size: clamp(1.8rem, 3vw, 2.6rem);
  line-height: 1;
}

.app-metric-card__hint {
  color: var(--cs-text-muted);
  line-height: 1.55;
}
</style>
