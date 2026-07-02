<template>
  <article class="panel home-editorial-change-grid">
    <div class="home-editorial-change-grid__header">
      <p class="cs-eyebrow">What CarbonSnap changes</p>
      <h2>From uncertainty to clarity</h2>
      <p class="subtitle">CarbonSnap is designed to make waste reduction feel less abstract.</p>
    </div>

    <div class="home-editorial-change-grid__lines" role="list" aria-label="CarbonSnap changes">
      <div v-for="line in changeLines" :key="line" class="home-editorial-change-grid__line" role="listitem">
        <p>{{ line }}</p>
      </div>
    </div>

    <p class="home-editorial-change-grid__link">
      CarbonSnap is designed to make waste reduction feel less abstract. It helps people
      understand what an item is, follow through on the next responsible step, connect their
      actions to a wider circular community, and keep a record of impact that lasts beyond the
      moment itself.
    </p>
  </article>
</template>

<script setup>
const changeLines = [
  "From uncertainty to clarity",
  "From intention to completed action",
  "From isolated effort to shared circulation",
  "From forgotten moments to visible impact",
];
</script>

<style scoped>
.home-editorial-change-grid {
  display: grid;
  gap: 18px;
  width: 100%;
}

.home-editorial-change-grid__header {
  display: grid;
  gap: 10px;
  max-width: 78ch;
}

.home-editorial-change-grid__header h2 {
  font-family: var(--cs-font-heading);
  font-size: clamp(2rem, 3.6vw, 3rem);
  line-height: 0.98;
  color: var(--cs-text-strong);
}

.home-editorial-change-grid__header .subtitle,
.home-editorial-change-grid__link {
  max-width: 78ch;
}

.home-editorial-change-grid__lines {
  display: grid;
  gap: 12px;
}

.home-editorial-change-grid__line {
  border: 1px solid rgba(18, 43, 19, 0.08);
  border-radius: 24px;
  background: rgba(255, 255, 255, 0.72);
  padding: 18px 20px;
  box-shadow: 0 12px 28px rgba(18, 43, 19, 0.06);
}

.home-editorial-change-grid__line p {
  font-family: var(--cs-font-heading);
  font-size: clamp(1.2rem, 1.6vw, 1.5rem);
  line-height: 1.08;
  color: var(--cs-text-strong);
}

.home-editorial-change-grid__link {
  font-size: 1.02rem;
  line-height: 1.75;
  color: var(--cs-text);
}

@media (max-width: 640px) {
  .home-editorial-change-grid__line {
    padding: 16px 18px;
    border-radius: 20px;
  }
}
</style>
