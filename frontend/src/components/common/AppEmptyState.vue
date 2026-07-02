<template>
  <section class="cs-empty-state" data-app-empty-state>
    <p v-if="eyebrow" class="cs-eyebrow">{{ eyebrow }}</p>
    <h2 class="cs-empty-state__title">{{ title }}</h2>
    <p class="cs-empty-state__copy">{{ copy }}</p>
    <div v-if="$slots.actions" class="app-empty-state__actions">
      <slot name="actions" />
    </div>
  </section>
</template>

<script setup>
defineProps({
  eyebrow: {
    type: String,
    default: "",
  },
  title: {
    type: String,
    required: true,
  },
  copy: {
    type: String,
    required: true,
  },
});
</script>

<style scoped>
.app-empty-state__actions {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
}
</style>
