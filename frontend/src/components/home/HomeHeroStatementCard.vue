<template>
  <article class="home-hero-statement-card">
    <p class="home-hero-statement-card__eyebrow">Our response</p>
    <h2 class="home-hero-statement-card__title">Designed as a practical system, not just a message.</h2>
    <p class="home-hero-statement-card__copy">
      We built CarbonSnap to help people move from intention to follow-through by making
      recyclable decisions clearer, environmental action easier to complete, and personal
      impact easier to remember.
    </p>
  </article>
</template>

<style scoped>
.home-hero-statement-card {
  display: grid;
  align-content: center;
  gap: 14px;
  width: 100%;
  border: 1px solid rgba(255, 255, 255, 0.12);
  border-radius: 32px;
  background: rgba(243, 247, 245, 0.12);
  backdrop-filter: blur(18px);
  padding: 24px;
}

.home-hero-statement-card__eyebrow {
  color: inherit;
  font-size: 0.78rem;
  font-weight: 800;
  letter-spacing: 0.18em;
  text-transform: uppercase;
}

.home-hero-statement-card__title {
  color: inherit;
  font-family: var(--cs-font-heading);
  font-size: clamp(1.9rem, 3vw, 2.6rem);
  line-height: 0.98;
}

.home-hero-statement-card__copy {
  color: inherit;
  line-height: 1.7;
  opacity: 0.92;
}

@media (max-width: 640px) {
  .home-hero-statement-card {
    padding: 20px;
  }
}
</style>
