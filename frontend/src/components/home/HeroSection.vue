<template>
  <section class="landing-hero" data-home-hero aria-label="CarbonSnap hero">
    <div class="landing-hero__copy" data-hero-copy>
      <h1>
        <span>{{ t("home.heroSnapWaste") }}</span>
        <strong>{{ t("home.heroMeasureImpact") }}</strong>
      </h1>
      <p class="landing-hero__lead">
        {{ t("home.heroLead") }}
      </p>
      <div class="landing-hero__actions">
        <RouterLink class="landing-button landing-button--dark" :to="getStartedRoute" data-home-get-started>
          {{ t("home.heroGetStarted") }}
          <span aria-hidden="true">-></span>
        </RouterLink>
        <button
          class="landing-button landing-button--light"
          type="button"
          data-home-demo-trigger
          @click="$emit('playDemo')"
        >
          {{ t("home.heroWatchDemo") }}
          <span aria-hidden="true">{{ t("home.heroPlay") }}</span>
        </button>
      </div>
    </div>

    <div class="landing-hero__camera" data-hero-camera>
      <PhoneCameraFrame :waste-items="wasteItems" />
    </div>
  </section>
</template>

<script setup>
import { computed } from "vue";
import { RouterLink } from "vue-router";

import PhoneCameraFrame from "./PhoneCameraFrame.vue";
import { useAuth } from "../../composables/useAuth.js";
import { useI18n } from "../../i18n/index.js";

defineEmits(["playDemo"]);

defineProps({
  wasteItems: {
    type: Array,
    required: true,
  },
});

const { isLoggedIn } = useAuth();
const { t } = useI18n();
const getStartedRoute = computed(() => (isLoggedIn.value ? "/ai" : "/login"));
</script>
