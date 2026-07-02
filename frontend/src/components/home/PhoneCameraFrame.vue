<template>
  <div class="phone-camera" data-phone-camera>
    <div class="phone-camera__viewport">
      <div class="phone-camera__badge">
        <span></span>
        {{ t("home.aiAnalysis") }}
      </div>
      <div class="phone-camera__corner phone-camera__corner--tl"></div>
      <div class="phone-camera__corner phone-camera__corner--tr"></div>
      <div class="phone-camera__corner phone-camera__corner--bl"></div>
      <div class="phone-camera__corner phone-camera__corner--br"></div>
      <div class="phone-camera__focus"></div>
      <div class="phone-camera__waste-row">
        <div
          v-for="item in wasteItems"
          :key="item.id"
          class="phone-camera__item"
          :class="[`phone-camera__item--${item.id}`, { 'phone-camera__item--shared-source': item.id === 'plastic' }]"
        >
          <WasteObject v-if="item.id !== 'plastic'" :item="item" />
          <div class="phone-camera__label" aria-hidden="true">
            <span>{{ item.name }}</span>
            <strong>{{ item.weight }}</strong>
            <small>{{ t("home.co2Saved") }} {{ item.carbonSaved }}</small>
          </div>
        </div>
      </div>
      <div class="phone-camera__ticks"></div>
    </div>
    <img class="phone-camera__frame" :src="cameraFrameAsset" alt="" draggable="false" />
  </div>
</template>

<script setup>
import { cameraFrameAsset } from "./landingData";
import WasteObject from "./WasteObject.vue";
import { useI18n } from "../../i18n/index.js";

defineProps({
  wasteItems: {
    type: Array,
    required: true,
  },
});

const { t } = useI18n();
</script>
