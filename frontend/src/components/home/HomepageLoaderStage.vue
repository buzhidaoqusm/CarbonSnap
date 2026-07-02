<template>
  <section class="home-stage loader-stage" data-home-stage="loader">
    <div class="loader-stage__scene" aria-hidden="true">
      <span class="loader-stage__bg loader-stage__bg--base"></span>
      <span class="loader-stage__bg loader-stage__bg--mid"></span>
      <span class="loader-stage__bg loader-stage__bg--focus"></span>
      <span class="loader-stage__light loader-stage__light--core"></span>
      <span class="loader-stage__light loader-stage__light--sky"></span>
      <span class="loader-stage__mist loader-stage__mist--one"></span>
      <span class="loader-stage__mist loader-stage__mist--two"></span>
      <span class="loader-stage__mist loader-stage__mist--three"></span>
      <span class="loader-stage__depth-field"></span>
      <span class="loader-stage__focus-bloom"></span>
      <div class="loader-stage__particles">
        <span class="loader-stage__particle loader-stage__particle--1"></span>
        <span class="loader-stage__particle loader-stage__particle--2"></span>
        <span class="loader-stage__particle loader-stage__particle--3"></span>
        <span class="loader-stage__particle loader-stage__particle--4"></span>
        <span class="loader-stage__particle loader-stage__particle--5"></span>
        <span class="loader-stage__particle loader-stage__particle--6"></span>
        <span class="loader-stage__particle loader-stage__particle--7"></span>
        <span class="loader-stage__particle loader-stage__particle--8"></span>
        <span class="loader-stage__particle loader-stage__particle--9"></span>
        <span class="loader-stage__particle loader-stage__particle--10"></span>
      </div>
      <span class="loader-stage__scene-overlay"></span>
      <span class="loader-stage__scene-vignette"></span>
    </div>
    <span class="loader-stage__halo" aria-hidden="true"></span>
    <div class="home-stage__inner loader-stage__inner">
      <div class="loader-stage__content">
        <p class="loader-stage__eyebrow">CarbonSnap</p>
        <h1 class="loader-stage__title">Reduce your carbon footprint</h1>
        <p class="loader-stage__subline">
          Track your impact, build greener habits, and turn everyday choices into lower emissions.
        </p>

        <div class="loader-stage__ring-shell">
          <svg
            class="loader-stage__ring-svg"
            viewBox="0 0 220 220"
            aria-hidden="true"
          >
            <circle
              class="loader-stage__ring-track"
              cx="110"
              cy="110"
              r="86"
            />
            <circle
              class="loader-stage__ring-progress"
              data-loader-progress
              cx="110"
              cy="110"
              r="86"
            />
          </svg>

          <div class="loader-stage__center">
            <strong class="loader-stage__value">{{ progress }}%</strong>
            <span class="loader-stage__label">Loading</span>
          </div>
        </div>

        <button
          class="loader-stage__arrow"
          type="button"
          :disabled="!loadingComplete"
          data-loader-arrow
          aria-label="Scroll to next stage"
          @click="handleEnter"
        >
          <svg
            class="loader-stage__arrow-icon"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            stroke-width="1.7"
            stroke-linecap="round"
            stroke-linejoin="round"
            aria-hidden="true"
          >
            <path d="M12 5v14" />
            <path d="m6 13 6 6 6-6" />
          </svg>
        </button>
      </div>
    </div>
  </section>
</template>

<script setup>
const props = defineProps({
  loadingComplete: {
    type: Boolean,
    default: false,
  },
  progress: {
    type: Number,
    default: 0,
  },
});

const emit = defineEmits(["enter"]);

function handleEnter() {
  if (!props.loadingComplete) {
    return;
  }

  emit("enter");
}
</script>
