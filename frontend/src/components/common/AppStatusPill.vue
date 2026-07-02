<template>
  <span class="app-status-pill" :class="`app-status-pill--${tone}`" data-app-status-pill>
    {{ text }}
  </span>
</template>

<script setup>
defineProps({
  text: {
    type: String,
    required: true,
  },
  tone: {
    type: String,
    default: "neutral",
  },
});
</script>

<style scoped>
.app-status-pill {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 999px;
  padding: 6px 10px;
  font-size: 0.78rem;
  font-weight: 800;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.app-status-pill--neutral {
  background: rgba(90, 97, 95, 0.1);
  color: var(--cs-text-muted);
}

.app-status-pill--success {
  background: rgba(38, 104, 41, 0.12);
  color: var(--cs-primary);
}

.app-status-pill--accent {
  background: rgba(185, 246, 0, 0.24);
  color: #4f6500;
}

.app-status-pill--warning {
  background: rgba(183, 121, 31, 0.15);
  color: var(--cs-warning);
}

.app-status-pill--danger {
  background: rgba(179, 27, 37, 0.12);
  color: var(--cs-danger);
}

.app-status-pill--info {
  background: rgba(0, 101, 113, 0.14);
  color: var(--cs-info);
}
</style>
