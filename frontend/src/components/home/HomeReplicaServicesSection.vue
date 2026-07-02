<template>
  <section id="services" class="home-replica-section home-replica-services" aria-label="Services section">
    <div class="home-replica-section-header">
      <p class="home-replica-kicker">Services</p>
      <h2 class="home-replica-section-title">A simple grid of capabilities with room to breathe.</h2>
      <p class="home-replica-section-lead">
        The original homepage uses compact cards and a clear section cadence. These placeholders mirror that layout while staying content-neutral.
      </p>
    </div>

    <div class="home-replica-services__grid">
      <article v-for="service in services" :key="service.title" class="home-replica-service-card">
        <div class="home-replica-service-card__media" aria-hidden="true"></div>
        <h3 class="home-replica-service-card__title">{{ service.title }}</h3>
        <p class="home-replica-service-card__copy">{{ service.copy }}</p>
      </article>
    </div>
  </section>
</template>

<script setup>
const services = [
  { title: "Collection flow", copy: "A clean card shape with a short note and a visual block to anchor the section." },
  { title: "Processing path", copy: "A lightweight placeholder for the operational story the source site introduces." },
  { title: "Material loops", copy: "A compact grid cell that keeps the same density and balance as the reference." },
  { title: "Community reach", copy: "A fourth card to preserve the wide desktop rhythm and rightward visual weight." },
];
</script>
