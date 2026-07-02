<template>
  <article class="panel home-quiet-close">
    <p class="cs-eyebrow">Quiet close</p>
    <p class="home-quiet-close__line">
      A system for people who want their environmental effort to mean something after the moment
      passes.
    </p>
    <RouterLink class="cs-button cs-button--accent" to="/ai">Open Assistant</RouterLink>
  </article>
</template>

<script setup>
import { RouterLink } from "vue-router";
</script>

<style scoped>
.home-quiet-close {
  display: grid;
  gap: 14px;
  align-content: start;
  max-width: 80ch;
}

.home-quiet-close__line {
  font-family: var(--cs-font-heading);
  font-size: clamp(1.6rem, 2.6vw, 2.15rem);
  line-height: 1.1;
  color: var(--cs-text-strong);
  max-width: 32ch;
}

@media (max-width: 640px) {
  .home-quiet-close {
    gap: 12px;
  }
}
</style>
