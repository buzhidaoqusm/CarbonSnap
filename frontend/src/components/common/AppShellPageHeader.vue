<template>
  <header class="app-shell-page-header" data-app-shell-page-header>
    <div class="app-shell-page-header__body">
      <p v-if="eyebrow" class="app-shell-page-header__eyebrow">
        {{ eyebrow }}
      </p>
      <h1 class="app-shell-page-header__title">{{ title }}</h1>
      <p v-if="description" class="app-shell-page-header__description">
        {{ description }}
      </p>
    </div>

    <div v-if="$slots.actions" class="app-shell-page-header__actions">
      <slot name="actions" />
    </div>
  </header>
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
  description: {
    type: String,
    default: "",
  },
});
</script>

<style scoped>
.app-shell-page-header {
  display: flex;
  align-items: end;
  justify-content: space-between;
  gap: 18px;
  padding: 8px 0 4px;
}

.app-shell-page-header__body {
  display: grid;
  gap: 10px;
  min-width: 0;
}

.app-shell-page-header__eyebrow {
  color: var(--cs-primary);
  font-size: 0.78rem;
  font-weight: 800;
  letter-spacing: 0.18em;
  text-transform: uppercase;
}

.app-shell-page-header__title {
  font-size: clamp(2rem, 4vw, 3.35rem);
  line-height: 0.98;
}

.app-shell-page-header__description {
  max-width: 68ch;
  color: var(--cs-text-muted);
  line-height: 1.65;
}

.app-shell-page-header__actions {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 12px;
}

@media (max-width: 840px) {
  .app-shell-page-header {
    flex-direction: column;
    align-items: stretch;
  }
}
</style>
