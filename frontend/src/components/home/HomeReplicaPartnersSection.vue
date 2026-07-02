<template>
  <section class="home-replica-section home-replica-partners" aria-label="Partners section">
    <div class="home-replica-section-header">
      <p class="home-replica-kicker">Partners</p>
      <h2 class="home-replica-section-title">A quiet logo wall preserves the source page's sense of trust.</h2>
    </div>

    <div class="home-replica-partners__panel">
      <div class="home-replica-partners__list">
        <span v-for="partner in partners" :key="partner" class="home-replica-partners__logo">{{ partner }}</span>
      </div>
    </div>
  </section>
</template>

<script setup>
const partners = ["Logo One", "Logo Two", "Logo Three", "Logo Four", "Logo Five", "Logo Six"];
</script>
