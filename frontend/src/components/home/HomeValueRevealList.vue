<template>
  <div class="home-value-reveal-list">
    <article
      v-for="(item, index) in items"
      :key="item.title"
      class="home-value-reveal-list__item panel"
      :style="{ transitionDelay: `${index * 90}ms` }"
    >
      <p class="home-value-reveal-list__eyebrow">0{{ index + 1 }}</p>
      <h2>{{ item.title }}</h2>
      <p class="subtitle">{{ item.copy }}</p>
    </article>
  </div>
</template>

<script setup>
defineProps({
  items: {
    type: Array,
    default: () => [],
  },
});
</script>

<style scoped>
.home-value-reveal-list {
  display: grid;
  gap: 20px;
  grid-template-columns: repeat(3, minmax(0, 1fr));
}

.home-value-reveal-list__item {
  display: grid;
  gap: 12px;
  align-content: start;
  min-height: 100%;
  transition:
    transform 220ms ease,
    box-shadow 220ms ease,
    border-color 220ms ease;
}

.home-value-reveal-list__item:hover {
  transform: translateY(-2px);
}

.home-value-reveal-list__eyebrow {
  color: var(--cs-primary);
  font-size: 0.78rem;
  font-weight: 800;
  letter-spacing: 0.18em;
}

@media (max-width: 980px) {
  .home-value-reveal-list {
    grid-template-columns: minmax(0, 1fr);
  }
}
</style>
