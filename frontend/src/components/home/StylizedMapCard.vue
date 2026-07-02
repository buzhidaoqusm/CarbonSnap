<template>
  <article class="map-card" data-map-card>
    <div class="map-card__header">
      <div>
        <p class="map-card__eyebrow">{{ t("home.mapNearby") }}</p>
        <h3>{{ t("home.mapPointsFound") }}</h3>
      </div>
      <span>{{ t("home.liveRadius") }}</span>
    </div>
    <div class="map-card__canvas" aria-label="Stylized nearby recycling location map">
      <span class="map-card__route map-card__route--one"></span>
      <span class="map-card__route map-card__route--two"></span>
      <span
        v-for="location in locations"
        :key="location.name"
        class="map-card__pin"
        :style="{ left: `${location.x}%`, top: `${location.y}%` }"
        :title="`${location.name} ${location.distance}`"
      ></span>
    </div>
    <div class="map-card__locations">
      <p v-for="location in locations" :key="location.name">
        <span>{{ location.name }}</span>
        <strong>{{ location.distance }}</strong>
      </p>
    </div>
  </article>
</template>

<script setup>
import { useI18n } from "../../i18n/index.js";

defineProps({
  locations: {
    type: Array,
    required: true,
  },
});

const { t } = useI18n();
</script>
