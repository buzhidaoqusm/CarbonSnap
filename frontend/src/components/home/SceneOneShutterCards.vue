<template>
  <section id="product" class="landing-scene landing-scene--capture" data-scene-one aria-label="AI capture scene">
    <slot />

    <div class="capture-overlay" data-capture-overlay>
      <div class="capture-overlay__flash" data-shutter-flash></div>
      <div class="capture-overlay__ring" data-shutter-ring></div>
      <div class="capture-overlay__cards" aria-label="Recognized recyclable carbon estimates">
        <GlassInfoCard v-for="item in wasteItems" :key="item.id" :item="item" />
      </div>
      <p class="capture-overlay__caption" data-capture-caption>
        AI separates every material signal from the camera feed, then translates recognition into item-level carbon impact.
      </p>
    </div>
  </section>
</template>

<script setup>
import GlassInfoCard from "./GlassInfoCard.vue";

defineProps({
  wasteItems: {
    type: Array,
    required: true,
  },
});
</script>
