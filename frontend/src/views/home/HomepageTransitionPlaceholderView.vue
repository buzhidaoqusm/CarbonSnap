<template>
  <AppLayout
    :is-authenticated="false"
    :avatar-url="''"
    variant="homepage"
    header-variant="immersive-home"
    header-state="solid"
    main-variant="immersive-home"
    :show-footer="false"
  >
    <section class="transition-placeholder">
      <div class="transition-placeholder__panel">
        <p class="transition-placeholder__eyebrow">Transition target</p>
        <h1 class="transition-placeholder__title">The homepage handoff landed.</h1>
        <p class="transition-placeholder__body">
          This page is intentionally lightweight for now. It exists so the three-stage
          homepage can finish with a smooth destination before we wire the real AI
          experience behind the CTA.
        </p>
        <RouterLink class="transition-placeholder__link" to="/ai">
          Open AI chat page
        </RouterLink>
      </div>
    </section>
  </AppLayout>
</template>

<script setup>
import { RouterLink } from "vue-router";

import AppLayout from "../../layouts/AppLayout.vue";
</script>

<style scoped>
.transition-placeholder {
  position: relative;
  min-height: 100dvh;
  padding: 132px 20px 48px;
  background:
    radial-gradient(circle at 50% 14%, rgba(244, 206, 130, 0.18), transparent 22%),
    radial-gradient(circle at 78% 18%, rgba(119, 165, 141, 0.18), transparent 26%),
    linear-gradient(180deg, #14211b 0%, #182822 50%, #1a2e27 100%);
}

.transition-placeholder__panel {
  width: min(760px, 100%);
  margin: 0 auto;
  padding: clamp(28px, 5vw, 56px);
  border-radius: 36px;
  text-align: center;
  background:
    linear-gradient(180deg, rgba(255, 250, 239, 0.08), rgba(255, 250, 239, 0.03)),
    rgba(255, 255, 255, 0.03);
  box-shadow:
    inset 0 0 0 1px rgba(255, 246, 224, 0.08),
    0 28px 90px rgba(0, 0, 0, 0.28);
}

.transition-placeholder__eyebrow {
  margin: 0;
  color: rgba(245, 234, 204, 0.76);
  font-size: 0.78rem;
  letter-spacing: 0.28em;
  text-transform: uppercase;
}

.transition-placeholder__title {
  margin: 18px 0 0;
  color: #fbf2de;
  font-family: "Cormorant Garamond", Georgia, serif;
  font-size: clamp(2.8rem, 6vw, 4.8rem);
  line-height: 0.95;
}

.transition-placeholder__body {
  max-width: 34ch;
  margin: 18px auto 0;
  color: rgba(236, 232, 223, 0.84);
  font-size: 1.04rem;
  line-height: 1.7;
}

.transition-placeholder__link {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 220px;
  margin-top: 28px;
  padding: 14px 26px;
  border-radius: 999px;
  background: linear-gradient(135deg, #f4cf85 0%, #e8aa4c 100%);
  color: #1d160f;
  font-family: "Space Grotesk", "Trebuchet MS", sans-serif;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-decoration: none;
  text-transform: uppercase;
}

@media (max-width: 720px) {
  .transition-placeholder {
    padding-top: 112px;
  }

  .transition-placeholder__link {
    width: 100%;
    min-width: 0;
  }
}
</style>
