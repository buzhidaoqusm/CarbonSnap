<template>
  <article
    class="stage-copy"
    :class="[`stage-copy--${chapter.id}`, { 'stage-copy--reduced': reducedMotion }]"
  >
    <p class="stage-copy__kicker">
      <span class="stage-copy__kicker-text">{{ chapter.kicker }}</span>
    </p>
    <h1 class="stage-copy__title">
      <span class="stage-copy__title-text">{{ chapter.title }}</span>
    </h1>
    <p class="stage-copy__body">
      <span class="stage-copy__body-text">{{ chapter.body }}</span>
    </p>
    <p v-if="chapter.accent" class="stage-copy__accent">
      <span class="stage-copy__accent-text">{{ chapter.accent }}</span>
    </p>
    <RouterLink
      v-if="chapter.ctaHref && chapter.ctaLabel"
      class="stage-copy__cta"
      :to="chapter.ctaHref"
    >
      {{ chapter.ctaLabel }}
    </RouterLink>
  </article>
</template>

<script setup>
import { RouterLink } from "vue-router";

defineProps({
  chapter: {
    type: Object,
    required: true,
  },
  reducedMotion: {
    type: Boolean,
    default: false,
  },
});
</script>
