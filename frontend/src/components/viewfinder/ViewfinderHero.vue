<template>
  <section
    ref="root"
    class="vf"
    :class="{ 'vf--ready': sceneReady }"
    :data-state="state"
    aria-labelledby="vf-title"
  >
    <canvas ref="canvas" class="vf__canvas" aria-hidden="true"></canvas>
    <div class="vf__blink" aria-hidden="true"></div>

    <div class="vf__copy">
      <h1 id="vf-title" class="vf__title">
        <span>{{ t("viewfinder.titleLine1") }}</span>
        <span>{{ t("viewfinder.titleLine2") }}</span>
      </h1>
      <p class="vf__lead">{{ t("viewfinder.lead") }}</p>
      <RouterLink class="vf__cta" to="/ai">{{ t("viewfinder.cta") }}</RouterLink>
      <!-- Narrow screens have no room for a label beside each item: after the
           photo, the results take the place of the lead instead. -->
      <ol v-if="state === 'captured'" class="vf__summary" :aria-label="t('viewfinder.resultsLabel')">
        <li v-for="(result, index) in results" :key="result.id" :style="{ '--delay': `${index * 90}ms` }">
          <span class="vf__result-name">
            <span class="vf__chip" :style="{ background: materialColor(result.material) }"></span>
            <strong>{{ result.name }}</strong>
          </span>
          <span class="vf__data">{{ formatWeight(result.weightKg) }}</span>
          <span class="vf__data">{{ formatKg(result.co2Kg) }} CO<sub>2</sub>e</span>
          <span class="vf__data vf__data--points">+{{ result.points }}</span>
        </li>
      </ol>
    </div>

    <!-- Live: the focus box moves from item to item, like autofocus. -->
    <div ref="focusBox" class="vf__focus" aria-hidden="true">
      <span class="vf__corner vf__corner--tl"></span>
      <span class="vf__corner vf__corner--tr"></span>
      <span class="vf__corner vf__corner--bl"></span>
      <span class="vf__corner vf__corner--br"></span>
    </div>
    <div ref="focusLabel" class="vf__focus-label" aria-hidden="true">
      <span class="vf__result-name">
        <span class="vf__chip" :style="{ background: materialColor(focusedItem.material) }"></span>
        <strong>{{ t(focusedItem.nameKey) }}</strong>
      </span>
      <span class="vf__data">{{ t("viewfinder.weight") }} {{ formatWeight(focusedItem.weightKg) }}</span>
    </div>

    <!-- Captured: every item outlined, then annotated with what the backend would record. -->
    <svg
      v-if="state === 'captured'"
      class="vf__outlines"
      :viewBox="`0 0 ${viewport.width} ${viewport.height}`"
      aria-hidden="true"
    >
      <rect
        v-for="(result, index) in results"
        :key="result.id"
        :x="result.box.x"
        :y="result.box.y"
        :width="result.box.width"
        :height="result.box.height"
        rx="10"
        :style="{ '--length': result.perimeter, '--delay': `${index * 140}ms` }"
      />
    </svg>
    <ol v-if="state === 'captured'" class="vf__results" :aria-label="t('viewfinder.resultsLabel')">
      <li
        v-for="(result, index) in results"
        :key="result.id"
        class="vf__result"
        :style="{
          transform: `translate(${result.label.x}px, ${result.label.y}px)`,
          '--delay': `${index * 140 + result.drawMs}ms`,
        }"
      >
        <span class="vf__result-name">
          <span class="vf__chip" :style="{ background: materialColor(result.material) }"></span>
          <strong>{{ result.name }}</strong>
        </span>
        <span class="vf__data">{{ t("viewfinder.weight") }} {{ formatWeight(result.weightKg) }}</span>
        <span class="vf__data">{{ t("viewfinder.carbon") }} {{ formatKg(result.co2Kg) }} CO<sub>2</sub>e</span>
        <span class="vf__data vf__data--points">+{{ result.points }} {{ t("viewfinder.points") }}</span>
      </li>
    </ol>
    <p class="vf__sr" aria-live="polite">{{ announcement }}</p>

    <div class="vf__controls">
      <div class="vf__thumb-slot">
        <canvas
          ref="thumb"
          class="vf__thumb"
          :class="{ 'vf__thumb--filled': hasPhoto }"
          :width="thumbSize.width * 2"
          :height="thumbSize.height * 2"
          :style="{ width: `${thumbSize.width}px`, height: `${thumbSize.height}px` }"
          aria-hidden="true"
        ></canvas>
      </div>
      <div class="vf__zoom" role="group" :aria-label="t('viewfinder.zoom')">
        <button
          v-for="level in ZOOM_LEVELS"
          :key="level"
          type="button"
          :aria-pressed="zoomLevel === level"
          @click="setZoom(level)"
        >
          {{ level }}×
        </button>
      </div>
      <button
        class="vf__shutter"
        type="button"
        :aria-label="state === 'captured' ? t('viewfinder.retake') : t('viewfinder.shutter')"
        :disabled="state === 'loading'"
        @click="onShutter"
      >
        <span></span>
      </button>
    </div>

    <pre v-if="perfText" class="vf__perf">{{ perfText }}</pre>
  </section>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, reactive, ref, shallowRef } from "vue";
import { RouterLink } from "vue-router";

import { useI18n } from "../../i18n/index.js";
import { createFrameLoop } from "../../motion/frameLoop.js";
import { createPerfProbe } from "../../motion/perfProbe.js";
import { createSpring, isAtRest, stepSpring, SPRING_UI } from "../../motion/spring.js";
import { carbonFor, VIEWFINDER_ITEMS } from "./items.js";

const ZOOM_LEVELS = [0.5, 1, 2];
const FOCUS_INTERVAL = 2.8; // seconds on each item before autofocus moves on
const HUNT_SECONDS = 0.32; // the blur-then-sharp of a focus change
const HUNT_BLUR_PX = 1.2;
const FOCUS_PADDING = 12;
const DRAW_SPEED = 0.9; // outline stroke, px per ms: constant, like a plotter

const { t } = useI18n();

const root = ref(null);
const canvas = ref(null);
const thumb = ref(null);
const focusBox = ref(null);
const focusLabel = ref(null);

const state = ref("loading"); // loading -> live <-> captured
const sceneReady = ref(false);
const hasPhoto = ref(false);
const zoomLevel = ref(1);
const focusIndex = ref(0);
const results = shallowRef([]);
const announcement = ref("");
const viewport = reactive({ width: 1, height: 1 });
const perfText = ref("");

const focusedItem = computed(() => VIEWFINDER_ITEMS[focusIndex.value]);
const thumbSize = computed(() => {
  const aspect = viewport.width / viewport.height;
  const height = 60;
  return { width: Math.round(Math.min(96, height * aspect)), height };
});

let scene = null;
let disposed = false;
let reducedMotion = false;
let focusTimer = 0;
let huntTime = Infinity;
let focusPlaced = false;
const box = { x: createSpring(), y: createSpring(), w: createSpring(), h: createSpring(), scale: createSpring(1) };
const flip = { progress: createSpring(0), from: null };
const perf = new URLSearchParams(window.location.search).has("perf") ? createPerfProbe() : null;
let perfTimer = null;
let observers = [];

function materialColor(material) {
  return `var(--color-${material})`;
}

function formatKg(value) {
  return `${value.toFixed(2)} kg`;
}

// 0.016 kg is "16 g", not "0.02 kg".
function formatWeight(kg) {
  return kg < 1 ? `${Math.round(kg * 1000)} g` : formatKg(kg);
}

// --- per-frame work: written straight to the DOM, outside Vue's reactivity ---

function setBoxTargets(rect) {
  box.x.target = rect.x - FOCUS_PADDING;
  box.y.target = rect.y - FOCUS_PADDING;
  box.w.target = rect.width + FOCUS_PADDING * 2;
  box.h.target = rect.height + FOCUS_PADDING * 2;
  if (!focusPlaced || reducedMotion) {
    // First placement (or reduced motion): appear in place instead of flying in from the corner.
    for (const key of ["x", "y", "w", "h"]) {
      box[key].value = box[key].target;
      box[key].velocity = 0;
    }
    focusPlaced = true;
  }
}

function drawFocus(dt) {
  for (const spring of Object.values(box)) stepSpring(spring, dt);
  const el = focusBox.value;
  el.style.width = `${box.w.value}px`;
  el.style.height = `${box.h.value}px`;
  el.style.transform = `translate3d(${box.x.value}px, ${box.y.value}px, 0) scale(${box.scale.value})`;

  // The camera drifts, so the target never fully stops: "locked" means close and slow.
  const locked =
    huntTime >= HUNT_SECONDS &&
    Math.abs(box.x.value - box.x.target) < 2 &&
    Math.abs(box.w.value - box.w.target) < 2 &&
    Math.abs(box.x.velocity) < 60;
  // Above the box: items stand on the floor, so the space above them is empty
  // backdrop, and the labels after the photo sit there too.
  const label = focusLabel.value;
  const labelX = Math.min(Math.max(box.x.value, 16), viewport.width - 236);
  label.style.transform = `translate3d(${labelX}px, ${box.y.value - 10}px, 0) translateY(-100%)`;
  label.classList.toggle("is-visible", locked);
  el.classList.toggle("is-visible", true);
}

function startHunt() {
  huntTime = 0;
  // Autofocus overshoots wide, then closes in on the subject.
  box.scale.value = 1.14;
  box.scale.target = 1;
}

function stepHunt(dt) {
  if (huntTime >= HUNT_SECONDS) return;
  huntTime += dt;
  const u = Math.min(huntTime / HUNT_SECONDS, 1);
  canvas.value.style.filter = u < 1 ? `blur(${(HUNT_BLUR_PX * Math.sin(Math.PI * u)).toFixed(2)}px)` : "";
}

function drawFlip(dt) {
  if (!flip.from) return;
  stepSpring(flip.progress, dt);
  const p = flip.progress.value; // 1 = covering the viewfinder, 0 = in its slot
  const { dx, dy, sx, sy } = flip.from;
  thumb.value.style.transform = `translate(${dx * p}px, ${dy * p}px) scale(${1 + (sx - 1) * p}, ${1 + (sy - 1) * p})`;
  if (isAtRest(flip.progress, 0.001)) {
    thumb.value.style.transform = "";
    thumb.value.classList.remove("is-flying");
    flip.from = null;
  }
}

const loop = createFrameLoop((dt, time) => {
  if (state.value === "live" && scene) {
    const started = performance.now();
    focusTimer += dt;
    if (!reducedMotion && focusTimer >= FOCUS_INTERVAL) {
      focusTimer = 0;
      focusIndex.value = (focusIndex.value + 1) % VIEWFINDER_ITEMS.length;
      startHunt();
    }
    stepHunt(dt);
    scene.render(dt, time / 1000);
    setBoxTargets(scene.rects.get(focusedItem.value.id));
    drawFocus(dt);
    if (!sceneReady.value) sceneReady.value = true;
    perf?.record(time, performance.now() - started);
    // Reduced motion: nothing moves, so render only until the zoom settles.
    if (reducedMotion && scene.zoomSettled) loop.stop();
    return;
  }
  drawFlip(dt);
  if (state.value === "captured" && !flip.from) loop.stop(); // the photo is still: no more frames needed
});

// --- shutter ---

function capture() {
  if (state.value !== "live" || !scene) return;
  scene.captureInto(thumb.value);
  canvas.value.style.filter = "";
  const items = VIEWFINDER_ITEMS.map((item) => {
    const rect = scene.rects.get(item.id);
    const outline = { x: rect.x - 8, y: rect.y - 8, width: rect.width + 16, height: rect.height + 16 };
    const perimeter = Math.round(2 * (outline.width + outline.height));
    return {
      id: item.id,
      material: item.material,
      name: t(item.nameKey),
      weightKg: item.weightKg,
      ...carbonFor(item),
      box: outline,
      perimeter,
      drawMs: reducedMotion ? 0 : Math.round(perimeter / DRAW_SPEED),
      label: { x: outline.x, y: outline.y - 10 },
    };
  });
  results.value = items;
  announcement.value = t("viewfinder.announce", { count: items.length });
  hasPhoto.value = true;
  state.value = "captured";
  // Only now: the labels render inside v-if="state === 'captured'", and until
  // this change nothing had scheduled that render for nextTick() to wait for.
  void separateLabels();

  if (!reducedMotion) {
    // FLIP: First (the viewfinder) -> Last (the slot). Invert: start drawn over the
    // viewfinder. Play: a spring pulls the transform back to nothing.
    const first = canvas.value.getBoundingClientRect();
    const last = thumb.value.getBoundingClientRect();
    flip.from = {
      dx: first.left - last.left,
      dy: first.top - last.top,
      sx: first.width / last.width,
      sy: first.height / last.height,
    };
    flip.progress.value = 1;
    flip.progress.velocity = 0;
    flip.progress.target = 0;
    // Scaled 15x, the slot's 2px border would be a 30px frame: hide it until landing.
    thumb.value.classList.add("is-flying");
    drawFlip(0);
  }
  loop.start();
}

// Items stand close together, so their labels can collide. Keep each label
// inside the viewfinder, then walk them left to right and lift any label that
// overlaps one already placed.
async function separateLabels() {
  await nextTick();
  const elements = [...root.value.querySelectorAll(".vf__result")].filter((element) => element.offsetParent);
  if (elements.length === 0) return; // narrow layout: the summary list is showing instead
  const frame = root.value.getBoundingClientRect();
  const margin = 16;
  const rects = elements.map((element) => element.getBoundingClientRect());
  const order = rects.map((_, index) => index).sort((a, b) => rects[a].left - rects[b].left);
  const gap = 6;
  const placed = [];
  const lift = rects.map(() => 0);
  const nudge = rects.map((rect) => {
    if (rect.right > frame.right - margin) return frame.right - margin - rect.right;
    if (rect.left < frame.left + margin) return frame.left + margin - rect.left;
    return 0;
  });
  for (const index of order) {
    let { top, bottom } = rects[index];
    const left = rects[index].left + nudge[index];
    const right = rects[index].right + nudge[index];
    let moved = true;
    while (moved) {
      moved = false;
      for (const other of placed) {
        const overlaps =
          left < other.right + gap && right > other.left - gap && top < other.bottom + gap && bottom > other.top - gap;
        if (overlaps) {
          const dy = bottom - (other.top - gap);
          top -= dy;
          bottom -= dy;
          lift[index] += dy;
          moved = true;
        }
      }
    }
    placed.push({ left, right, top, bottom });
  }
  if (lift.some(Boolean) || nudge.some(Boolean)) {
    results.value = results.value.map((result, index) => ({
      ...result,
      label: { x: result.label.x + nudge[index], y: result.label.y - lift[index] },
    }));
  }
}

function retake() {
  results.value = [];
  announcement.value = "";
  focusTimer = 0;
  huntTime = Infinity;
  state.value = "live";
  perf?.pause();
  loop.start();
}

function onShutter() {
  if (state.value === "captured") retake();
  else capture();
}

function onScroll() {
  // The first scroll down takes the picture.
  if (state.value === "live" && window.scrollY > 4) capture();
}

function setZoom(level) {
  zoomLevel.value = level;
  scene?.setZoom(level, { immediate: reducedMotion });
  if (state.value === "live") loop.start();
}

// --- lifecycle ---

function measure() {
  const rect = root.value.getBoundingClientRect();
  viewport.width = Math.round(rect.width);
  viewport.height = Math.round(rect.height);
  scene?.resize(viewport.width, viewport.height, window.devicePixelRatio || 1);
  if (scene && state.value === "live") loop.start();
}

async function loadScene() {
  if (disposed) return;
  try {
    const { createViewfinderScene } = await import("./scene/viewfinderScene.js");
    const coarsePointer = window.matchMedia("(pointer: coarse)").matches;
    const created = await createViewfinderScene(canvas.value, {
      items: VIEWFINDER_ITEMS,
      maxPixelRatio: coarsePointer ? 1.5 : 2,
    });
    if (disposed) {
      created.dispose();
      return;
    }
    scene = created;
    scene.setDrift(reducedMotion ? 0 : 1);
    measure();
    state.value = "live";
    loop.start();
  } catch (error) {
    // No WebGL: the page keeps its static backdrop and copy.
    console.warn("Viewfinder scene unavailable:", error);
  }
}

onMounted(() => {
  reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  measure();

  const resizeObserver = new ResizeObserver(measure);
  resizeObserver.observe(root.value);
  // Off screen, the camera has nothing to show: stop rendering.
  const visibility = new IntersectionObserver(([entry]) => {
    if (entry.isIntersecting && state.value === "live" && scene) loop.start();
    else if (!entry.isIntersecting && state.value === "live") {
      loop.stop();
      perf?.pause();
    }
  });
  visibility.observe(root.value);
  observers = [resizeObserver, visibility];
  window.addEventListener("scroll", onScroll, { passive: true });

  // Let the page paint its copy first; three.js arrives when the browser is idle.
  if ("requestIdleCallback" in window) window.requestIdleCallback(loadScene, { timeout: 1500 });
  else window.setTimeout(loadScene, 200);

  if (perf) {
    window.__viewfinderPerf = perf;
    perfTimer = window.setInterval(() => {
      const s = perf.stats();
      perfText.value = `frames ${s.frames}\ninterval p50 ${s.intervalP50} ms  p95 ${s.intervalP95} ms\ncpu p50 ${s.cpuP50} ms  p95 ${s.cpuP95} ms\nlong frames ${s.longFrames}`;
    }, 500);
  }
});

onBeforeUnmount(() => {
  disposed = true;
  loop.stop();
  observers.forEach((observer) => observer.disconnect());
  window.removeEventListener("scroll", onScroll);
  window.clearInterval(perfTimer);
  scene?.dispose();
  scene = null;
});
</script>

<style scoped>
.vf {
  position: relative;
  isolation: isolate;
  overflow: hidden;
  height: 100svh;
  min-height: 600px;
  /* The static frame before three.js arrives: the same paper sweep, flat. */
  background: linear-gradient(180deg, #e7eaec 0%, #e7eaec 52%, #dde1e4 100%);
}

.vf__canvas {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  opacity: 0;
  transition: opacity 400ms linear;
}

.vf--ready .vf__canvas {
  opacity: 1;
}

/* A taken photo looks a touch flatter than the live preview. */
.vf[data-state="captured"] .vf__canvas {
  filter: saturate(0.86) brightness(0.98);
  transition:
    opacity 400ms linear,
    filter 500ms linear;
}

.vf__blink {
  position: absolute;
  inset: 0;
  z-index: 4;
  background: #000;
  opacity: 0;
  pointer-events: none;
}

.vf[data-state="captured"] .vf__blink {
  animation: vf-blink 170ms linear;
}

@keyframes vf-blink {
  0% {
    opacity: 0;
  }
  25% {
    opacity: 0.55;
  }
  100% {
    opacity: 0;
  }
}

.vf__copy {
  position: absolute;
  z-index: 2;
  top: clamp(56px, 11vh, 132px);
  left: clamp(20px, 5.5vw, 88px);
  max-width: min(60rem, calc(100% - 40px));
}

.vf__title {
  display: grid;
  font-size: clamp(2.4rem, 5vw, 4.5rem);
  font-stretch: var(--stretch-display);
  font-weight: 760;
  line-height: var(--leading-display);
  letter-spacing: -0.015em;
}

/* Han characters fill the whole em box: the Latin display leading makes lines touch. */
.vf__title:lang(zh) {
  font-weight: 700;
  line-height: 1.18;
  letter-spacing: 0;
}

.vf__lead {
  max-width: 32em;
  margin-top: var(--space-5);
  color: var(--color-ink-2);
  font-size: var(--text-18);
}

.vf__cta {
  display: inline-flex;
  align-items: center;
  margin-top: var(--space-6);
  padding: 14px 22px;
  border-radius: var(--radius-control);
  background: var(--color-blue);
  color: var(--color-paper);
  font-weight: 600;
  text-decoration: none;
}

.vf__cta:hover {
  background: var(--color-blue-strong);
}

.vf__focus {
  position: absolute;
  top: 0;
  left: 0;
  z-index: 1;
  opacity: 0;
  pointer-events: none;
  will-change: transform;
}

.vf__focus.is-visible {
  opacity: 1;
}

.vf[data-state="captured"] .vf__focus,
.vf[data-state="captured"] .vf__focus-label {
  visibility: hidden;
}

.vf__corner {
  position: absolute;
  width: 18px;
  height: 18px;
  border: 0 solid var(--color-focus);
}

.vf__corner--tl {
  top: 0;
  left: 0;
  border-top-width: 2px;
  border-left-width: 2px;
  border-top-left-radius: 6px;
}

.vf__corner--tr {
  top: 0;
  right: 0;
  border-top-width: 2px;
  border-right-width: 2px;
  border-top-right-radius: 6px;
}

.vf__corner--bl {
  bottom: 0;
  left: 0;
  border-bottom-width: 2px;
  border-left-width: 2px;
  border-bottom-left-radius: 6px;
}

.vf__corner--br {
  right: 0;
  bottom: 0;
  border-right-width: 2px;
  border-bottom-width: 2px;
  border-bottom-right-radius: 6px;
}

.vf__focus-label,
.vf__result {
  position: absolute;
  top: 0;
  left: 0;
  z-index: 3;
  display: grid;
  gap: 2px;
  padding: 8px 12px;
  border-radius: var(--radius-control);
  background: var(--color-paper);
  box-shadow: var(--shadow-float);
  font-size: var(--text-14);
  line-height: 1.3;
  white-space: nowrap;
  pointer-events: none;
}

.vf__focus-label {
  opacity: 0;
  transition: opacity var(--duration-crossfade) linear;
}

.vf__focus-label.is-visible {
  opacity: 1;
}

.vf__chip {
  display: inline-block;
  width: 9px;
  height: 9px;
  margin-right: 6px;
  border-radius: 2px;
  vertical-align: 0.05em;
}

.vf__data {
  color: var(--color-ink-2);
  font-stretch: var(--stretch-data);
  font-variant-numeric: tabular-nums;
}

.vf__data--points {
  color: var(--color-blue);
  font-weight: 600;
}

.vf__data sub {
  font-size: 0.72em;
  line-height: 0;
  vertical-align: -0.2em;
}

.vf__outlines {
  position: absolute;
  inset: 0;
  z-index: 2;
  width: 100%;
  height: 100%;
  pointer-events: none;
}

.vf__outlines rect {
  fill: none;
  stroke: var(--color-ink);
  stroke-width: 1.5;
  stroke-dasharray: var(--length);
  stroke-dashoffset: var(--length);
  /* Constant speed: a longer outline takes longer, like a plotter pen. */
  animation: vf-draw calc(var(--length) * 1ms / 0.9) linear var(--delay) forwards;
}

@keyframes vf-draw {
  to {
    stroke-dashoffset: 0;
  }
}

.vf__results {
  margin: 0;
  padding: 0;
  list-style: none;
}

.vf__result {
  translate: 0 -100%;
  opacity: 0;
  animation: vf-appear var(--duration-crossfade) linear var(--delay) forwards;
}

@keyframes vf-appear {
  to {
    opacity: 1;
  }
}

.vf__result-name {
  display: flex;
  align-items: center;
}

.vf__summary {
  display: none;
  margin: var(--space-5) 0 0;
  padding: 0;
  list-style: none;
  font-size: var(--text-14);
}

.vf__summary li {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto auto auto;
  gap: var(--space-3);
  align-items: baseline;
  padding: 7px 0;
  border-bottom: 1px solid var(--color-line);
  opacity: 0;
  animation: vf-appear var(--duration-crossfade) linear var(--delay) forwards;
}

@media (max-width: 719px) {
  .vf[data-state="captured"] .vf__lead,
  .vf[data-state="captured"] .vf__cta,
  .vf__results {
    display: none;
  }

  .vf__summary {
    display: block;
  }
}

.vf__controls {
  position: absolute;
  right: 0;
  bottom: 0;
  left: 0;
  z-index: 5;
  display: grid;
  grid-template-columns: 1fr auto 1fr;
  align-items: end;
  padding: 0 clamp(20px, 5.5vw, 88px) clamp(20px, 4vh, 36px);
}

.vf__thumb-slot {
  justify-self: start;
}

.vf__thumb {
  display: block;
  border: 2px solid var(--color-paper);
  border-radius: var(--radius-control);
  background: rgba(23, 33, 43, 0.08);
  box-shadow: var(--shadow-float);
  transform-origin: top left;
  opacity: 0.6;
}

.vf__thumb--filled {
  opacity: 1;
}

.vf__thumb.is-flying {
  border-color: transparent;
  box-shadow: none;
}

.vf__zoom {
  position: absolute;
  bottom: calc(clamp(20px, 4vh, 36px) + 96px);
  left: 50%;
  display: flex;
  gap: 4px;
  padding: 4px;
  border-radius: var(--radius-pill);
  background: rgba(255, 255, 255, 0.72);
  translate: -50% 0;
}

.vf__zoom button {
  min-width: 40px;
  padding: 6px 8px;
  border: 0;
  border-radius: var(--radius-pill);
  background: transparent;
  color: var(--color-ink);
  font-size: var(--text-12);
  font-stretch: var(--stretch-data);
  font-weight: 600;
  font-variant-numeric: tabular-nums;
}

.vf__zoom button[aria-pressed="true"] {
  background: var(--color-ink);
  color: var(--color-paper);
}

.vf__shutter {
  display: grid;
  place-items: center;
  width: 76px;
  height: 76px;
  padding: 0;
  border: 3px solid var(--color-ink);
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.5);
}

.vf__shutter span {
  width: 60px;
  height: 60px;
  border-radius: 50%;
  background: var(--color-ink);
  transition: transform 90ms linear;
}

.vf__shutter:active span {
  transform: scale(0.9);
}

.vf__shutter:disabled {
  opacity: 0.4;
}

.vf[data-state="captured"] .vf__shutter span {
  background: var(--color-paper);
  box-shadow: inset 0 0 0 2px var(--color-ink);
}

.vf__sr {
  position: absolute;
  width: 1px;
  height: 1px;
  overflow: hidden;
  clip-path: inset(50%);
}

.vf__perf {
  position: absolute;
  top: 12px;
  right: 12px;
  z-index: 6;
  margin: 0;
  padding: 8px 10px;
  border-radius: 8px;
  background: rgba(23, 33, 43, 0.85);
  color: #fff;
  font-size: 12px;
}

@media (max-width: 640px) {
  .vf__lead {
    font-size: var(--text-16);
  }

  .vf__zoom {
    bottom: calc(clamp(20px, 4vh, 36px) + 88px);
  }
}

@media (prefers-reduced-motion: reduce) {
  .vf[data-state="captured"] .vf__blink {
    animation: none;
  }

  .vf__outlines rect {
    stroke-dashoffset: 0;
    opacity: 0;
    animation: vf-appear var(--duration-crossfade) linear forwards;
  }
}
</style>
