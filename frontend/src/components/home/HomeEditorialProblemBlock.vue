<template>
  <article class="panel home-editorial-problem">
    <p class="cs-eyebrow">The everyday problem</p>
    <h2>The real problem is not awareness. It is follow-through.</h2>
    <p class="subtitle">
      For many people, waste reduction breaks down in ordinary moments. An item is hard to judge,
      the next responsible action feels uncertain, and even when the effort is made, it often
      disappears without becoming a visible habit or record.
    </p>
  </article>
</template>

<style scoped>
.home-editorial-problem {
  display: grid;
  gap: 14px;
  max-width: 88ch;
}

.home-editorial-problem h2 {
  font-family: var(--cs-font-heading);
  font-size: clamp(2rem, 3.5vw, 2.9rem);
  line-height: 1;
  color: var(--cs-text-strong);
}

.home-editorial-problem .subtitle {
  max-width: 76ch;
}
</style>
