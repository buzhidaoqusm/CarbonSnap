<template>
  <section v-if="hasLocations" class="nearby-map-card" :aria-label="t('ai.nearbyMap')">
    <div class="nearby-map-card__map-shell">
      <div ref="miniMapElementRef" class="nearby-map-card__map"></div>

      <button
        class="nearby-map-card__expand-button"
        type="button"
        :aria-label="t('ai.nearbyExpandMap')"
        :title="t('ai.nearbyExpandMap')"
        @click.stop.prevent="openFullscreen"
      >
        <svg
          class="nearby-map-card__expand-icon"
          viewBox="0 0 24 24"
          fill="none"
          xmlns="http://www.w3.org/2000/svg"
          aria-hidden="true"
        >
          <g
            stroke="currentColor"
            stroke-width="2.4"
            stroke-linecap="round"
            stroke-linejoin="round"
          >
            <path d="M8 3H5.5C4.11929 3 3 4.11929 3 5.5V8" />
            <path d="M16 3H18.5C19.8807 3 21 4.11929 21 5.5V8" />
            <path d="M8 21H5.5C4.11929 21 3 19.8807 3 18.5V16" />
            <path d="M16 21H18.5C19.8807 21 21 19.8807 21 18.5V16" />
            <path d="M9.5 9.5L5 5" />
            <path d="M14.5 9.5L19 5" />
            <path d="M9.5 14.5L5 19" />
            <path d="M14.5 14.5L19 19" />
          </g>
        </svg>
      </button>
    </div>
  </section>

  <Teleport to="body">
    <div
      v-if="isFullscreen"
      class="nearby-map-modal"
      :style="{ '--nearby-map-modal-top': modalTopOffset }"
      role="dialog"
      aria-modal="true"
      :aria-label="t('ai.nearbyMapExpanded')"
    >
      <div class="nearby-map-modal__scrim" @click="closeFullscreen"></div>

      <div class="nearby-map-modal__panel">
        <section class="nearby-map-modal__map-shell">
          <div class="nearby-map-modal__actions">
            <button class="nearby-map-modal__icon-button" type="button" @click="closeFullscreen">
              {{ t("common.close") }}
            </button>
            <button class="nearby-map-modal__icon-button" type="button" @click="resetFullscreenView">
              {{ t("ai.nearbyResetView") }}
            </button>
          </div>

          <div ref="fullscreenMapElementRef" class="nearby-map-modal__map"></div>
        </section>

        <aside class="nearby-map-modal__sidebar">
          <div class="nearby-map-modal__sidebar-header">
            <h3 class="nearby-map-modal__sidebar-title">{{ t("ai.nearbyLocationsCount", { count: normalizedLocations.length }) }}</h3>
            <p class="nearby-map-modal__sidebar-subtitle">
              {{ t("ai.nearbyMapHint") }}
            </p>
          </div>

          <div class="nearby-map-modal__list">
            <button
              v-for="(location, index) in normalizedLocations"
              :key="location.osm_url || `${location.name}-${index}`"
              class="nearby-map-modal__result"
              :class="{ 'nearby-map-modal__result--active': index === selectedLocationIndex }"
              type="button"
              @click="focusLocation(index)"
            >
              <div class="nearby-map-modal__result-index">{{ index + 1 }}</div>

              <div class="nearby-map-modal__result-body">
                <p class="nearby-map-modal__result-title">{{ location.name }}</p>
                <p class="nearby-map-modal__result-meta">
                  {{ location.category }} - {{ formatDistance(location.distance_meters) }}
                </p>
                <p class="nearby-map-modal__result-address">{{ location.address }}</p>
                <a
                  class="nearby-map-modal__result-link"
                  :href="location.osm_url"
                  target="_blank"
                  rel="noreferrer"
                  @click.stop
                >
                  {{ t("ai.nearbyOpenOsm") }}
                </a>
              </div>
            </button>
          </div>
        </aside>
      </div>
    </div>
  </Teleport>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from "vue";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import { useI18n } from "../../i18n/index.js";

const emit = defineEmits(["ready"]);
const { t } = useI18n();

const props = defineProps({
  locations: {
    type: Array,
    default: () => [],
  },
});

const miniMapElementRef = ref(null);
const fullscreenMapElementRef = ref(null);
const isFullscreen = ref(false);
const selectedLocationIndex = ref(0);
const modalTopOffset = ref("104px");

const normalizedLocations = computed(() =>
  props.locations
    .map((location, index) => ({
      ...location,
      address: location.address || "Address unavailable",
      category: location.category || "Recycling point",
      distance_meters: Number(location.distance_meters || 0),
      lat: Number(location.lat),
      lng: Number(location.lng),
      markerIndex: index,
    }))
    .filter((location) => Number.isFinite(location.lat) && Number.isFinite(location.lng)),
);

const hasLocations = computed(() => normalizedLocations.value.length > 0);
let miniMapInstance = null;
let miniMarkerLayer = null;
let fullscreenMapInstance = null;
let fullscreenMarkerLayer = null;
let miniMarkers = [];
let fullscreenMarkers = [];
let bodyOverflowBeforeFullscreen = "";
let miniMapReadyCycle = 0;
let lastEmittedReadyCycle = 0;

function updateModalTopOffset() {
  if (typeof document === "undefined") {
    modalTopOffset.value = "104px";
    return;
  }

  const header = document.querySelector(".app-header");
  if (!header) {
    modalTopOffset.value = "104px";
    return;
  }

  const headerRect = header.getBoundingClientRect();
  modalTopOffset.value = `${Math.max(84, Math.ceil(headerRect.bottom) + 12)}px`;
}

function formatDistance(distanceMeters) {
  if (distanceMeters >= 1000) {
    return `${(distanceMeters / 1000).toFixed(1)} km away`;
  }
  return `${Math.round(distanceMeters)} m away`;
}

function waitForFrame() {
  return new Promise((resolve) => {
    window.requestAnimationFrame(() => resolve());
  });
}

function buildMarkerIcon(index, isSelected, scale = "small") {
  return L.divIcon({
    className: "nearby-map-card__marker",
    html: `<span class="nearby-map-card__marker-dot nearby-map-card__marker-dot--${scale}${isSelected ? " nearby-map-card__marker-dot--selected" : ""}">${index + 1}</span>`,
    iconSize: scale === "large" ? [38, 38] : [32, 32],
    iconAnchor: scale === "large" ? [19, 19] : [16, 16],
  });
}

function ensureMiniMap() {
  if (!miniMapElementRef.value || miniMapInstance) {
    return;
  }

  miniMapInstance = L.map(miniMapElementRef.value, {
    attributionControl: false,
    zoomControl: false,
    scrollWheelZoom: false,
  });

  L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    maxZoom: 19,
    attribution: "&copy; OpenStreetMap contributors",
  }).addTo(miniMapInstance);

  miniMarkerLayer = L.layerGroup().addTo(miniMapInstance);
}

function ensureFullscreenMap() {
  if (!fullscreenMapElementRef.value || fullscreenMapInstance) {
    return;
  }

  fullscreenMapInstance = L.map(fullscreenMapElementRef.value, {
    attributionControl: false,
    zoomControl: true,
    scrollWheelZoom: true,
  });

  L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    maxZoom: 19,
    attribution: "&copy; OpenStreetMap contributors",
  }).addTo(fullscreenMapInstance);

  fullscreenMarkerLayer = L.layerGroup().addTo(fullscreenMapInstance);
}

function bindMarker(marker, index) {
  marker.on("click", () => {
    selectedLocationIndex.value = index;
  });
}

function renderMiniMap() {
  if (!hasLocations.value) {
    return;
  }

  ensureMiniMap();
  if (!miniMapInstance || !miniMarkerLayer) {
    return;
  }

  miniMarkerLayer.clearLayers();
  miniMarkers = [];

  const bounds = [];

  normalizedLocations.value.forEach((location, index) => {
    const latLng = L.latLng(location.lat, location.lng);
    bounds.push(latLng);

    const marker = L.marker(latLng, {
      icon: buildMarkerIcon(index, index === selectedLocationIndex.value, "small"),
      keyboard: false,
    });

    marker.bindPopup(
      `<strong>${location.name}</strong><br>${location.category}<br>${formatDistance(location.distance_meters)}`,
    );
    bindMarker(marker, index);
    marker.addTo(miniMarkerLayer);
    miniMarkers.push(marker);
  });

  if (bounds.length === 1) {
    miniMapInstance.setView(bounds[0], 15, { animate: false });
  } else {
    miniMapInstance.fitBounds(bounds, {
      animate: false,
      padding: [28, 28],
      maxZoom: 15,
    });
  }

  miniMapInstance.invalidateSize(false);
}

async function emitMiniMapReady(cycle) {
  if (!hasLocations.value || !miniMapInstance || cycle !== miniMapReadyCycle) {
    return;
  }

  await waitForFrame();
  await waitForFrame();

  if (!hasLocations.value || !miniMapInstance || cycle !== miniMapReadyCycle) {
    return;
  }

  miniMapInstance.invalidateSize(false);
  if (lastEmittedReadyCycle === cycle) {
    return;
  }

  lastEmittedReadyCycle = cycle;
  emit("ready");
}

function renderFullscreenMap() {
  if (!isFullscreen.value || !hasLocations.value) {
    return;
  }

  ensureFullscreenMap();
  if (!fullscreenMapInstance || !fullscreenMarkerLayer) {
    return;
  }

  fullscreenMarkerLayer.clearLayers();
  fullscreenMarkers = [];

  normalizedLocations.value.forEach((location, index) => {
    const marker = L.marker([location.lat, location.lng], {
      icon: buildMarkerIcon(index, index === selectedLocationIndex.value, "large"),
      keyboard: false,
    });

    marker.bindPopup(
      `<strong>${location.name}</strong><br>${location.address}<br>${location.category}`,
    );
    bindMarker(marker, index);
    marker.addTo(fullscreenMarkerLayer);
    fullscreenMarkers.push(marker);
  });

  focusLocation(selectedLocationIndex.value, { openPopup: false, smooth: false });
  fullscreenMapInstance.invalidateSize(false);
}

function focusLocation(index, options = {}) {
  const { openPopup = true, smooth = true } = options;
  const location = normalizedLocations.value[index];
  if (!location) {
    return;
  }

  selectedLocationIndex.value = index;

  if (fullscreenMapInstance) {
    fullscreenMapInstance.setView([location.lat, location.lng], 14, {
      animate: smooth,
    });
  }

  if (openPopup && fullscreenMarkers[index]) {
    fullscreenMarkers[index].openPopup();
  }
}

function resetFullscreenView() {
  if (!fullscreenMapInstance || !normalizedLocations.value.length) {
    return;
  }

  const bounds = normalizedLocations.value.map((location) => [location.lat, location.lng]);
  fullscreenMapInstance.fitBounds(bounds, {
    animate: true,
    padding: [42, 42],
    maxZoom: 14,
  });
}

async function openFullscreen() {
  updateModalTopOffset();
  bodyOverflowBeforeFullscreen = document.body.style.overflow;
  document.body.style.overflow = "hidden";
  isFullscreen.value = true;

  await nextTick();
  await waitForFrame();
  await waitForFrame();
  renderFullscreenMap();
}

function closeFullscreen() {
  isFullscreen.value = false;
  document.body.style.overflow = bodyOverflowBeforeFullscreen;
}

watch(
  () => props.locations,
  () => {
    selectedLocationIndex.value = 0;
    miniMapReadyCycle += 1;
    lastEmittedReadyCycle = 0;

    nextTick(async () => {
      renderMiniMap();
      renderFullscreenMap();
      await emitMiniMapReady(miniMapReadyCycle);
    });
  },
  {
    deep: true,
    immediate: true,
  },
);

watch(selectedLocationIndex, () => {
  nextTick(() => {
    renderMiniMap();
    renderFullscreenMap();
  });
});

watch(isFullscreen, async (value) => {
  if (value) {
    await nextTick();
    renderFullscreenMap();
    return;
  }

  if (fullscreenMapInstance) {
    fullscreenMapInstance.remove();
    fullscreenMapInstance = null;
    fullscreenMarkerLayer = null;
    fullscreenMarkers = [];
  }
});

onMounted(() => {
  updateModalTopOffset();
  window.addEventListener("resize", updateModalTopOffset);
});

onBeforeUnmount(() => {
  document.body.style.overflow = bodyOverflowBeforeFullscreen;
  window.removeEventListener("resize", updateModalTopOffset);

  if (miniMapInstance) {
    miniMapInstance.remove();
    miniMapInstance = null;
    miniMarkerLayer = null;
    miniMarkers = [];
  }

  if (fullscreenMapInstance) {
    fullscreenMapInstance.remove();
    fullscreenMapInstance = null;
    fullscreenMarkerLayer = null;
    fullscreenMarkers = [];
  }
});
</script>

<style scoped>
.nearby-map-card {
  position: relative;
  overflow: hidden;
  border: 1px solid rgba(15, 118, 110, 0.12);
  border-radius: 24px;
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.92) 0%, rgba(245, 251, 248, 0.96) 100%);
  box-shadow: 0 20px 40px rgba(15, 23, 42, 0.08);
}

.nearby-map-card__map-shell {
  position: relative;
  min-height: 320px;
  isolation: isolate;
}

.nearby-map-card__map {
  position: relative;
  z-index: 0;
  height: 320px;
  width: 100%;
}

.nearby-map-card__expand-button,
.nearby-map-modal__icon-button {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border: 1px solid rgba(148, 163, 184, 0.24);
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.96);
  box-shadow: 0 12px 26px rgba(15, 23, 42, 0.15);
  color: #102a43;
  cursor: pointer;
  font-family: "Space Grotesk", "Trebuchet MS", sans-serif;
  font-size: 0.88rem;
  font-weight: 700;
  padding: 10px 14px;
}

.nearby-map-card__expand-button {
  position: absolute;
  top: 16px;
  right: 16px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  z-index: 1200;
  width: 46px;
  height: 46px;
  padding: 0;
  border-color: transparent;
  background: transparent;
  box-shadow: none;
  color: #102a43;
  isolation: isolate;
}

.nearby-map-card__expand-icon {
  width: 24px;
  height: 24px;
  display: block;
  color: currentColor;
  position: relative;
  flex-shrink: 0;
  filter:
    drop-shadow(0 1px 1px rgba(255, 255, 255, 0.9))
    drop-shadow(0 2px 5px rgba(255, 255, 255, 0.7));
}

.nearby-map-card__expand-button:hover,
.nearby-map-card__expand-button:focus-visible {
  color: #081f33;
  outline: none;
  transform: translateY(-1px);
}

.nearby-map-card__expand-button:hover .nearby-map-card__expand-icon,
.nearby-map-card__expand-button:focus-visible .nearby-map-card__expand-icon {
  filter:
    drop-shadow(0 1px 1px rgba(255, 255, 255, 0.95))
    drop-shadow(0 3px 8px rgba(255, 255, 255, 0.82));
}

.nearby-map-modal__result-link {
  display: inline-flex;
  align-items: center;
  margin-top: 10px;
  color: #0f766e;
  font-weight: 700;
  text-decoration: none;
}

.nearby-map-modal__result-link:hover {
  text-decoration: underline;
}

.nearby-map-modal {
  position: fixed;
  top: var(--nearby-map-modal-top, 104px);
  right: 0;
  bottom: 0;
  left: 0;
  z-index: 1600;
}

.nearby-map-modal__scrim {
  position: absolute;
  inset: 0;
  background: rgba(2, 6, 23, 0.38);
  backdrop-filter: blur(6px);
}

.nearby-map-modal__panel {
  position: absolute;
  inset: 12px 18px 18px;
  display: grid;
  grid-template-columns: minmax(0, 1fr) 360px;
  gap: 16px;
}

.nearby-map-modal__map-shell,
.nearby-map-modal__sidebar {
  position: relative;
  overflow: hidden;
  border: 1px solid rgba(148, 163, 184, 0.22);
  border-radius: 28px;
  background: rgba(255, 255, 255, 0.95);
  box-shadow: 0 24px 50px rgba(15, 23, 42, 0.18);
}

.nearby-map-modal__actions {
  position: absolute;
  top: 16px;
  left: 16px;
  z-index: 500;
  display: flex;
  gap: 10px;
}

.nearby-map-modal__map {
  width: 100%;
  height: 100%;
  min-height: 70dvh;
}

.nearby-map-modal__sidebar {
  display: flex;
  flex-direction: column;
}

.nearby-map-modal__sidebar-header {
  padding: 22px 22px 14px;
  border-bottom: 1px solid rgba(148, 163, 184, 0.16);
}

.nearby-map-modal__sidebar-title {
  margin: 0;
  color: #102a43;
  font-family: "Space Grotesk", "Trebuchet MS", sans-serif;
  font-size: 1.18rem;
}

.nearby-map-modal__sidebar-subtitle {
  margin: 8px 0 0;
  color: #486581;
  line-height: 1.5;
}

.nearby-map-modal__list {
  flex: 1;
  overflow: auto;
  padding: 10px;
}

.nearby-map-modal__result {
  width: 100%;
  display: grid;
  grid-template-columns: 40px minmax(0, 1fr);
  gap: 12px;
  border: 1px solid transparent;
  border-radius: 18px;
  background: transparent;
  cursor: pointer;
  margin-bottom: 8px;
  padding: 14px;
  text-align: left;
  transition:
    border-color 180ms ease,
    background 180ms ease,
    transform 180ms ease;
}

.nearby-map-modal__result:hover,
.nearby-map-modal__result--active {
  border-color: rgba(20, 184, 166, 0.24);
  background: linear-gradient(180deg, rgba(240, 253, 250, 0.96) 0%, rgba(239, 246, 255, 0.98) 100%);
  transform: translateY(-1px);
}

.nearby-map-modal__result-index {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 40px;
  height: 40px;
  border-radius: 999px;
  background: #102a43;
  color: #ffffff;
  font-family: "Space Grotesk", "Trebuchet MS", sans-serif;
  font-weight: 700;
}

.nearby-map-modal__result--active .nearby-map-modal__result-index {
  background: #0f766e;
}

.nearby-map-modal__result-title {
  margin: 0;
  color: #102a43;
  font-family: "Space Grotesk", "Trebuchet MS", sans-serif;
  font-size: 1rem;
  line-height: 1.35;
}

.nearby-map-modal__result-meta,
.nearby-map-modal__result-address {
  margin: 6px 0 0;
  color: #486581;
  line-height: 1.5;
}

.nearby-map-card :deep(.leaflet-container),
.nearby-map-modal :deep(.leaflet-container) {
  font-family: "Source Sans 3", "Segoe UI", sans-serif;
}

.nearby-map-card :deep(.leaflet-control-attribution),
.nearby-map-modal :deep(.leaflet-control-attribution) {
  display: none;
}

.nearby-map-card :deep(.leaflet-top),
.nearby-map-card :deep(.leaflet-bottom),
.nearby-map-modal :deep(.leaflet-top),
.nearby-map-modal :deep(.leaflet-bottom) {
  z-index: 180;
}

.nearby-map-card :deep(.leaflet-container),
.nearby-map-card :deep(.leaflet-pane),
.nearby-map-card :deep(.leaflet-top),
.nearby-map-card :deep(.leaflet-bottom) {
  z-index: auto;
}

.nearby-map-card :deep(.nearby-map-card__marker),
.nearby-map-modal :deep(.nearby-map-card__marker) {
  background: transparent;
  border: none;
}

.nearby-map-card :deep(.nearby-map-card__marker-dot),
.nearby-map-modal :deep(.nearby-map-card__marker-dot) {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border: 2px solid rgba(255, 255, 255, 0.92);
  border-radius: 999px;
  background: #102a43;
  box-shadow: 0 8px 18px rgba(15, 23, 42, 0.25);
  color: #ffffff;
  font-family: "Space Grotesk", "Trebuchet MS", sans-serif;
  font-weight: 700;
}

.nearby-map-card :deep(.nearby-map-card__marker-dot--small),
.nearby-map-modal :deep(.nearby-map-card__marker-dot--small) {
  width: 32px;
  height: 32px;
  font-size: 0.86rem;
}

.nearby-map-card :deep(.nearby-map-card__marker-dot--large),
.nearby-map-modal :deep(.nearby-map-card__marker-dot--large) {
  width: 38px;
  height: 38px;
  font-size: 0.92rem;
}

.nearby-map-card :deep(.nearby-map-card__marker-dot--selected),
.nearby-map-modal :deep(.nearby-map-card__marker-dot--selected) {
  background: #0f766e;
}

@media (max-width: 960px) {
  .nearby-map-modal__panel {
    grid-template-columns: minmax(0, 1fr);
    inset: 12px;
  }

  .nearby-map-modal__map-shell {
    min-height: 56dvh;
  }

  .nearby-map-modal__sidebar {
    max-height: 34dvh;
  }
}

@media (max-width: 640px) {
  .nearby-map-card {
    border-radius: 20px;
  }

  .nearby-map-card__map-shell {
    min-height: 280px;
  }

  .nearby-map-card__map {
    height: 280px;
  }

  .nearby-map-card__expand-button,
  .nearby-map-modal__icon-button {
    padding: 9px 12px;
  }

  .nearby-map-card__expand-button {
    top: 12px;
    right: 12px;
    width: 42px;
    height: 42px;
    padding: 0;
  }

  .nearby-map-modal__panel {
    inset: 8px 8px 12px;
  }

  .nearby-map-modal__actions {
    left: 12px;
    top: 12px;
    flex-wrap: wrap;
  }

  .nearby-map-modal__sidebar-header {
    padding: 18px 16px 12px;
  }

  .nearby-map-modal__list {
    padding: 8px;
  }

  .nearby-map-modal__result {
    grid-template-columns: 34px minmax(0, 1fr);
    padding: 12px;
  }

  .nearby-map-modal__result-index {
    width: 34px;
    height: 34px;
  }
}
</style>
