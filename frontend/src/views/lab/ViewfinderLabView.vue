<template>
  <main class="ui lab">
    <ViewfinderHero />
    <section class="lab__next">
      <p>{{ t("viewfinder.labNext") }}</p>
    </section>
  </main>
</template>

<script setup>
import ViewfinderHero from "../../components/viewfinder/ViewfinderHero.vue";
import { useI18n } from "../../i18n/index.js";

const { t } = useI18n();
</script>

<style scoped>
.lab {
  background: var(--color-steel);
}

/* Room to scroll: the first scroll is what takes the picture. */
.lab__next {
  display: grid;
  min-height: 110vh;
  place-items: start;
  padding: var(--space-9) clamp(20px, 5.5vw, 88px);
  color: var(--color-ink-2);
}
</style>
