<template>
  <section class="home-live-status-block panel">
    <div class="home-live-status-block__header">
      <p class="cs-eyebrow">What is live today</p>
      <h2>Built honestly around the current backend</h2>
      <p class="subtitle">
        Notifications are active, while Projects and Profile remain intentionally lightweight for now.
      </p>
    </div>

    <div class="home-live-status-block__grid">
      <article class="home-live-status-block__item">
        <h3>Notifications are live</h3>
        <p>Unread counts, mark-as-read actions, and account activity already connect to the backend.</p>
      </article>

      <article class="home-live-status-block__item">
        <h3>Projects and profile stay restrained</h3>
        <p>These areas stay intentionally light until deeper backend support arrives.</p>
      </article>
    </div>
  </section>
</template>

<style scoped>
.home-live-status-block {
  display: grid;
  gap: 18px;
}

.home-live-status-block__header {
  display: grid;
  gap: 10px;
}

.home-live-status-block__grid {
  display: grid;
  gap: 16px;
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.home-live-status-block__item {
  display: grid;
  gap: 10px;
  padding: 18px;
  border: 1px solid var(--cs-outline);
  border-radius: 22px;
  background: rgba(255, 255, 255, 0.72);
}

.home-live-status-block__item h3 {
  font-size: 1.1rem;
}

.home-live-status-block__item p {
  color: var(--cs-text-muted);
  line-height: 1.6;
}

@media (max-width: 640px) {
  .home-live-status-block__grid {
    grid-template-columns: minmax(0, 1fr);
  }
}
</style>
