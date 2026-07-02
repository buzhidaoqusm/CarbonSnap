<template>
  <div class="home-system-loop-stack">
    <div class="home-system-loop-stack__list">
      <article
        v-for="(step, index) in steps"
        :key="step.label"
        class="home-system-loop-stack__card panel"
      >
        <p class="home-system-loop-stack__index">0{{ index + 1 }}</p>
        <p class="cs-eyebrow">{{ step.label }}</p>
        <h2>{{ step.title }}</h2>
        <p class="subtitle">{{ step.copy }}</p>
      </article>
    </div>
  </div>
</template>

<script setup>
defineProps({
  steps: {
    type: Array,
    default: () => [],
  },
});
</script>

<style scoped>
.home-system-loop-stack {
  width: 100%;
}

.home-system-loop-stack__list {
  display: grid;
  gap: 18px;
}

.home-system-loop-stack__card {
  display: grid;
  gap: 12px;
  align-content: start;
}

.home-system-loop-stack__index {
  color: var(--cs-primary);
  font-size: 0.78rem;
  font-weight: 800;
  letter-spacing: 0.18em;
}

.home-system-loop-stack__card h2 {
  font-size: 1.5rem;
}

@media (max-width: 980px) {
  .home-system-loop-stack__list {
    gap: 16px;
  }
}
</style>
