<template>
  <section class="home-replica-section home-replica-impact" aria-label="Impact section">
    <div>
      <p class="home-replica-kicker">Impact</p>
      <h2 class="home-replica-section-title">A restrained chart block keeps the informational rhythm grounded.</h2>
      <p class="home-replica-section-lead">
        The reference design balances editorial copy with quantitative detail. This placeholder version keeps that balance without needing final project data.
      </p>
      <div class="home-replica-stat-row" style="margin-top: 20px;">
        <article v-for="stat in stats" :key="stat.label" class="home-replica-stat">
          <p class="home-replica-stat__value">{{ stat.value }}</p>
          <p class="home-replica-stat__label">{{ stat.label }}</p>
        </article>
      </div>
    </div>

    <div class="home-replica-impact__chart">
      <p class="home-replica-impact__chart-title">Placeholder performance chart</p>
      <div class="home-replica-bar-chart">
        <div
          v-for="bar in bars"
          :key="bar.label"
          class="home-replica-bar"
          :data-label="bar.label"
          :style="{ '--bar-height': bar.height }"
        ></div>
      </div>
      <p class="home-replica-impact__chart-note">
        The exact metrics can be swapped in later. For now, the visual footprint and balance are the important part.
      </p>
    </div>
  </section>
</template>

<script setup>
const stats = [
  { value: "24k", label: "Placeholder actions" },
  { value: "8.4t", label: "Illustrative savings" },
  { value: "92%", label: "Clearer message" },
];

const bars = [
  { label: "Jan", height: "52%" },
  { label: "Feb", height: "68%" },
  { label: "Mar", height: "84%" },
  { label: "Apr", height: "72%" },
  { label: "May", height: "90%" },
];
</script>
