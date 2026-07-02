<template>
  <section class="home-replica-section home-replica-process" aria-label="Process section">
    <div class="home-replica-section-header">
      <p class="home-replica-kicker">Process</p>
      <h2 class="home-replica-section-title">A four-step sequence to keep the page moving in a straight line.</h2>
    </div>

    <div class="home-replica-step-list">
      <article v-for="step in steps" :key="step.title" class="home-replica-step">
        <h3 class="home-replica-step__title">{{ step.title }}</h3>
        <p class="home-replica-step__copy">{{ step.copy }}</p>
      </article>
    </div>
  </section>
</template>

<script setup>
const steps = [
  { title: "Introduce the page", copy: "Open with a confident hero and a clear media frame." },
  { title: "Move through sections", copy: "Keep each block distinct but visually related." },
  { title: "Reinforce the message", copy: "Use compact cards, simple copy, and a measured rhythm." },
  { title: "Close on contact", copy: "End with a final section that feels like the last page of the same story." },
];
</script>
