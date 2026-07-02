<template>
  <section
    ref="stageRootRef"
    class="cinematic-home"
    :data-chapter="activeChapter"
    :data-phase="scenePhase"
    :data-reduced-motion="isReducedMotion ? 'true' : 'false'"
    :style="stageStyle"
  >
    <div class="cinematic-home__wash cinematic-home__wash--left" aria-hidden="true"></div>
    <div class="cinematic-home__wash cinematic-home__wash--right" aria-hidden="true"></div>

    <div class="cinematic-home__viewport" aria-hidden="true">
      <div ref="webglMountRef" class="cinematic-home__webgl"></div>
      <div class="cinematic-home__grain"></div>
      <div class="cinematic-home__veil-markers">
        <span></span>
        <span></span>
      </div>
      <div class="cinematic-home__coordinates cinematic-home__coordinates--left">25.3444 S</div>
      <div class="cinematic-home__coordinates cinematic-home__coordinates--right">131.0369 E</div>
      <nav class="cinematic-home__chapters" aria-label="Homepage chapters">
        <span
          v-for="(chapter, index) in chapters"
          :key="chapter.id"
          class="cinematic-home__chapter"
          :class="{
            'cinematic-home__chapter--active': chapter.id === activeChapter,
            'cinematic-home__chapter--complete': index < activeChapterIndex,
          }"
          :style="{ '--chapter-fill': getChapterFill(index).toFixed(3) }"
        >
          <span class="cinematic-home__chapter-label">{{ chapter.railLabel }}</span>
        </span>
      </nav>
    </div>

    <div class="cinematic-home__sections">
      <section
        v-for="chapter in chapters"
        :key="chapter.id"
        class="cinematic-home__section"
        :class="[
          `cinematic-home__section--${chapter.id}`,
          { 'cinematic-home__section--active': chapter.id === activeChapter },
        ]"
      >
        <div class="cinematic-home__section-inner">
          <div v-if="chapter.id === 'intro'" class="cinematic-home__chrome">
            <span class="cinematic-home__kicker">Step into the interface</span>
            <div class="cinematic-home__chrome-actions">
              <RouterLink class="cinematic-home__action" to="/ai">Open AI</RouterLink>
              <button class="cinematic-home__menu" type="button" aria-label="Stage menu">
                <span></span>
                <span></span>
              </button>
            </div>
          </div>

          <StageChapterContent
            :chapter="chapter"
            :reduced-motion="isReducedMotion"
          />
        </div>
      </section>
    </div>
  </section>
</template>

<script setup>
import { computed, ref } from "vue";
import { RouterLink } from "vue-router";

import StageChapterContent from "./StageChapterContent.vue";
import { useHomepageScrollScene } from "../../composables/home/useHomepageScrollScene";
import { useStageWebGL } from "../../composables/home/useStageWebGL";

const stageRootRef = ref(null);
const webglMountRef = ref(null);

const chapters = [
  {
    id: "intro",
    railLabel: "Intro",
    kicker: "Step into the interface",
    title: "CarbonSnap",
    body: "A living environmental interface that turns recycling into something you can see, feel, and follow through real page motion.",
    accent: "Still. Composed. Waiting for motion.",
  },
  {
    id: "capture",
    railLabel: "Capture",
    kicker: "Capture",
    title: "Recognize waste before the moment slips away",
    body: "Point, scan, and let the interface resolve the object while the decision is still in your hands and the guidance still matters.",
    accent: "Image-led recognition with immediate direction.",
  },
  {
    id: "insight",
    railLabel: "Insight",
    kicker: "Insight",
    title: "Read carbon impact as the scene opens",
    body: "AI-assisted interpretation turns a single disposal choice into visible context instead of hidden backend math and silent estimates.",
    accent: "Measured impact. Visible action.",
  },
  {
    id: "impact",
    railLabel: "Impact",
    kicker: "Impact",
    title: "Turn one action into public momentum",
    body: "Individual recycling events accumulate into a shared environmental signal that feels immediate, local, and collective.",
    accent: "Small actions become public momentum.",
  },
  {
    id: "outro",
    railLabel: "Outro",
    kicker: "Next",
    title: "Enter the assistant when the sequence clears",
    body: "Continue into the AI workflow and turn the cinematic preview into real guidance the moment the homepage hands control back to you.",
    accent: "The sequence ends. The workflow begins.",
    ctaLabel: "Launch AI Flow",
    ctaHref: "/ai",
  },
];

const {
  activeChapter,
  chapterProgress,
  isReducedMotion,
  progress,
  scenePhase,
} = useHomepageScrollScene(stageRootRef);

useStageWebGL({
  activeChapter,
  isReducedMotion,
  mountRef: webglMountRef,
  progress,
  scenePhase,
});

const activeChapterIndex = computed(() =>
  Math.max(
    0,
    chapters.findIndex((chapter) => chapter.id === activeChapter.value),
  ),
);

const stageStyle = computed(() => ({
  "--chapter-progress": chapterProgress.value.toFixed(3),
  "--scene-progress": progress.value.toFixed(3),
}));

function getChapterFill(index) {
  if (index < activeChapterIndex.value) {
    return 1;
  }

  if (index === activeChapterIndex.value) {
    return chapterProgress.value;
  }

  return 0;
}
</script>

<style scoped src="../../styles/views/home-stage.css"></style>
