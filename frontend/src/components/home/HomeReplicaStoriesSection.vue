<template>
  <section class="home-replica-section home-replica-stories" aria-label="Stories section">
    <div class="home-replica-section-header">
      <p class="home-replica-kicker">Featured stories</p>
      <h2 class="home-replica-section-title">A larger storytelling block with one featured moment and two supporting tiles.</h2>
    </div>

    <div class="home-replica-stories__grid">
      <article class="home-replica-story-card home-replica-story-card--featured">
        <div>
          <p class="home-replica-kicker">Feature one</p>
          <h3 class="home-replica-section-title" style="font-size: clamp(1.9rem, 2.6vw, 3rem);">A prominent media tile sits beside the text.</h3>
          <p class="home-replica-story-card__copy">
            This keeps the same editorial proportion the source page uses when it introduces a major case study or campaign highlight.
          </p>
        </div>
        <div class="home-replica-story-card__media" aria-hidden="true"></div>
      </article>

      <article v-for="story in stories" :key="story.title" class="home-replica-story-card">
        <div class="home-replica-story-card__media" aria-hidden="true"></div>
        <h3 class="home-replica-story-card__title">{{ story.title }}</h3>
        <p class="home-replica-story-card__copy">{{ story.copy }}</p>
      </article>
    </div>
  </section>
</template>

<script setup>
const stories = [
  { title: "Supporting story tile", copy: "A narrower card with a consistent image placeholder and short supporting text." },
  { title: "Secondary story tile", copy: "Another content block to preserve the three-part visual cadence." },
];
</script>
