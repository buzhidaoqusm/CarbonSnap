<template>
  <main
    ref="landingRoot"
    class="carbon-landing"
    data-carbon-landing
    :style="{ '--landing-hero-bg': `url(${heroBackgroundAsset})` }"
  >
    <AppHeader
      :is-authenticated="isLoggedIn"
      :avatar-alt="avatarAlt"
      :avatar-url="avatarUrl"
      :points-label="pointsLabel"
    />

    <SceneOneShutterCards :waste-items="wasteItems">
      <HeroSection :waste-items="wasteItems" @play-demo="playHomepageDemo" />
    </SceneOneShutterCards>

    <SceneTwoBottleAnalysis
      :analysis-metrics="plasticBottleAnalysis"
      :guidance="plasticBottleGuidance"
      :locations="nearbyLocations"
    />

    <SceneThreeBottleRecycleAudit :features="auditFeatures" />

    <div class="shared-bottle" data-shared-bottle aria-hidden="true">
      <WasteObject :item="plasticBottle" />
    </div>

    <div class="audit-bin-fixed-front" data-audit-front-fixed aria-hidden="true">
      <img :src="recycleBinFrontAsset" alt="" draggable="false" />
    </div>
  </main>
</template>

<script setup>
import { computed, onBeforeUnmount } from "vue";

import HeroSection from "../components/home/HeroSection.vue";
import SceneOneShutterCards from "../components/home/SceneOneShutterCards.vue";
import SceneTwoBottleAnalysis from "../components/home/SceneTwoBottleAnalysis.vue";
import SceneThreeBottleRecycleAudit from "../components/home/SceneThreeBottleRecycleAudit.vue";
import WasteObject from "../components/home/WasteObject.vue";
import AppHeader from "../components/common/AppHeader.vue";
import {
  getAuditFeatures,
  getNearbyLocations,
  getPlasticBottleAnalysis,
  getPlasticBottleGuidance,
  getWasteItems,
  heroBackgroundAsset,
  recycleBinFrontAsset,
} from "../components/home/landingData";
import { useAuth } from "../composables/useAuth.js";
import { useHomeLandingMotion } from "../composables/home/useHomeLandingMotion";
import { useI18n } from "../i18n/index.js";

const { isLoggedIn, user } = useAuth();
const { t } = useI18n();
const landingRoot = useHomeLandingMotion();
const wasteItems = computed(() => getWasteItems(t));
const plasticBottleAnalysis = computed(() => getPlasticBottleAnalysis(t));
const plasticBottleGuidance = computed(() => getPlasticBottleGuidance(t));
const nearbyLocations = computed(() => getNearbyLocations(t));
const auditFeatures = computed(() => getAuditFeatures(t));
const plasticBottle = computed(() => wasteItems.value.find((item) => item.id === "plastic"));
const DEMO_SCROLL_DURATION_MS = 10000;
let demoScrollFrame = 0;
let stopDemoScroll = null;

const avatarAlt = computed(() => user.value?.username || "User avatar");
const avatarUrl = computed(() => user.value?.avatar_url || "");
const pointsLabel = computed(() => {
  if (isLoggedIn.value && user.value?.current_points != null) {
    return `${user.value.current_points} pts`;
  }
  return "0 pts";
});

function maxScrollTop() {
  const documentElement = document.documentElement;
  const body = document.body;
  const scrollHeight = Math.max(
    documentElement?.scrollHeight || 0,
    body?.scrollHeight || 0,
  );

  return Math.max(0, scrollHeight - window.innerHeight);
}

function forceNativeScrollBehavior() {
  const documentElement = document.documentElement;
  const body = document.body;
  const previousDocumentScrollBehavior = documentElement.style.scrollBehavior;
  const previousBodyScrollBehavior = body.style.scrollBehavior;

  documentElement.style.scrollBehavior = "auto";
  body.style.scrollBehavior = "auto";

  return () => {
    documentElement.style.scrollBehavior = previousDocumentScrollBehavior;
    body.style.scrollBehavior = previousBodyScrollBehavior;
  };
}

function cancelDemoScroll() {
  if (demoScrollFrame) {
    window.cancelAnimationFrame(demoScrollFrame);
    demoScrollFrame = 0;
  }

  stopDemoScroll?.();
  stopDemoScroll = null;
}

function playHomepageDemo() {
  if (typeof window === "undefined") {
    return;
  }

  cancelDemoScroll();

  const startTop = window.scrollY || window.pageYOffset || 0;
  const targetTop = maxScrollTop();

  if (targetTop <= startTop) {
    return;
  }

  const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  if (reduceMotion) {
    window.scrollTo({ top: targetTop, left: 0, behavior: "smooth" });
    return;
  }

  const interruptEvents = ["wheel", "touchstart", "keydown", "mousedown"];
  const restoreScrollBehavior = forceNativeScrollBehavior();
  const interrupt = () => cancelDemoScroll();
  const cleanup = () => {
    interruptEvents.forEach((eventName) => {
      window.removeEventListener(eventName, interrupt);
    });
    restoreScrollBehavior();
  };

  interruptEvents.forEach((eventName) => {
    window.addEventListener(eventName, interrupt, { passive: true });
  });
  stopDemoScroll = cleanup;

  const startedAt = performance.now();
  const step = (now) => {
    const progress = Math.min((now - startedAt) / DEMO_SCROLL_DURATION_MS, 1);

    window.scrollTo({
      top: startTop + (targetTop - startTop) * progress,
      left: 0,
      behavior: "auto",
    });

    if (progress < 1) {
      demoScrollFrame = window.requestAnimationFrame(step);
      return;
    }

    cancelDemoScroll();
  };

  demoScrollFrame = window.requestAnimationFrame(step);
}

onBeforeUnmount(() => {
  cancelDemoScroll();
});
</script>

<style src="../styles/views/home-view.css"></style>
