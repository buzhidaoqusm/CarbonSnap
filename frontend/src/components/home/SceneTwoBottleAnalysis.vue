<template>
  <section id="how-it-works" class="landing-scene landing-scene--analysis" data-scene-two aria-label="Plastic bottle analysis">
    <div class="analysis-stage">
      <div class="analysis-stage__visual" data-analysis-bottle-zone>
        <div class="analysis-leaves" data-analysis-leaves aria-hidden="true">
          <span v-for="leaf in 12" :key="leaf"></span>
        </div>
        <div class="analysis-stage__shadow" data-analysis-shadow></div>
      </div>

      <div class="analysis-stage__content" data-analysis-content>
        <p class="scene-kicker">{{ t("home.sceneBottleKicker") }}</p>
        <h2>{{ t("home.sceneBottleTitle") }}</h2>
        <p class="scene-copy">
          {{ t("home.analysisBody") }}
        </p>

        <div class="analysis-metric-grid">
          <article v-for="metric in analysisMetrics" :key="metric.label" class="analysis-card" data-analysis-card>
            <p>{{ metric.label }}</p>
            <strong>{{ metric.value }}</strong>
            <span>{{ metric.meta }}</span>
          </article>
        </div>

        <article class="analysis-guidance" data-analysis-card>
          <p>{{ guidance.title }}</p>
          <h3>{{ guidance.body }}</h3>
        </article>

        <StylizedMapCard :locations="locations" />
      </div>
    </div>
  </section>
</template>

<script setup>
import StylizedMapCard from "./StylizedMapCard.vue";
import { useI18n } from "../../i18n/index.js";

defineProps({
  analysisMetrics: {
    type: Array,
    required: true,
  },
  guidance: {
    type: Object,
    required: true,
  },
  locations: {
    type: Array,
    required: true,
  },
});

const { t } = useI18n();

</script>
