<template>
  <section id="impact" class="landing-scene landing-scene--audit" data-scene-three aria-label="AI audit recycling scene">
    <div class="audit-stage">
      <div class="audit-stage__visual" data-audit-visual>
        <div class="audit-leaves" data-audit-leaves aria-hidden="true">
          <span v-for="leaf in 12" :key="leaf"></span>
        </div>
        <div class="audit-bin audit-bin--base" data-audit-bin aria-hidden="true">
          <img class="audit-bin__image" :src="recycleBinBaseAsset" alt="" draggable="false" />
        </div>
        <div class="audit-bin audit-bin--front" aria-hidden="true">
          <img class="audit-bin__image" :src="recycleBinFrontAsset" alt="" draggable="false" />
          <span class="audit-bin__label">{{ t("home.recycle") }}</span>
        </div>
        <div class="audit-stage__verified" data-audit-verified>{{ t("home.verified") }}</div>
      </div>

      <article class="audit-panel" data-audit-panel>
        <p class="scene-kicker">{{ t("home.auditKicker") }}</p>
        <h2>{{ t("home.auditTitle") }}</h2>
        <p class="scene-copy">
          {{ t("home.auditBody") }}
        </p>
        <ul>
          <li v-for="feature in features" :key="feature">{{ feature }}</li>
        </ul>
      </article>
    </div>
  </section>
</template>

<script setup>
import { recycleBinBaseAsset, recycleBinFrontAsset } from "./landingData";
import { useI18n } from "../../i18n/index.js";

defineProps({
  features: {
    type: Array,
    required: true,
  },
});

const { t } = useI18n();
</script>
