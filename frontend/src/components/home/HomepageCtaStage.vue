<template>
  <section class="home-stage cta-stage" data-home-stage="cta">
    <div class="cta-stage__terrain" aria-hidden="true">
      <span class="cta-stage__rock cta-stage__rock--tl"></span>
      <span class="cta-stage__rock cta-stage__rock--tr"></span>
      <span class="cta-stage__rock cta-stage__rock--bl"></span>
      <span class="cta-stage__rock cta-stage__rock--br"></span>
      <span class="cta-stage__moss"></span>
    </div>
    <span class="cta-stage__glow" aria-hidden="true"></span>
    <div class="home-stage__inner cta-stage__inner">
      <div class="cta-stage__panel" data-animate="cta">
        <div class="cta-stage__copy">
          <p class="cta-stage__eyebrow">Greenplanet</p>
          <h2 class="cta-stage__title">
            Make it green
          </h2>
          <p class="cta-stage__body">
            Now more than ever, our planet needs our help.
          </p>
          <button
            class="cta-stage__button"
            type="button"
            :disabled="navigating"
            @click="handleActivate"
          >
            {{ navigating ? "Transitioning..." : "do it now" }}
          </button>
        </div>
      </div>
    </div>
  </section>
</template>

<script setup>
const props = defineProps({
  navigating: {
    type: Boolean,
    default: false,
  },
});

const emit = defineEmits(["activate"]);

function handleActivate() {
  if (props.navigating) {
    return;
  }

  emit("activate");
}
</script>
