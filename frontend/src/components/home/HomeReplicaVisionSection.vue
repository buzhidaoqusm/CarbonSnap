<template>
  <section class="home-replica-section home-replica-vision" aria-label="Vision section">
    <div class="home-replica-vision__statement">
      <p class="home-replica-kicker">Vision</p>
      <h2 class="home-replica-vision__quote">The page should feel composed, spacious, and carefully directed.</h2>
      <p class="home-replica-vision__copy">
        This section mirrors the source homepage's quieter value-proposition area. The key job is to preserve tone and hierarchy without overfilling the page.
      </p>
    </div>

    <div class="home-replica-vision__panel">
      <div class="home-replica-vision__meter" v-for="metric in metrics" :key="metric.label">
        <p class="home-replica-vision__meter-label">{{ metric.label }}</p>
        <div class="home-replica-vision__meter-bar" :style="{ '--meter-width': metric.width }">
          <span></span>
        </div>
      </div>
    </div>
  </section>
</template>

<script setup>
const metrics = [
  { label: "Clarity", width: "82%" },
  { label: "Scale", width: "74%" },
  { label: "Restraint", width: "88%" },
];
</script>
