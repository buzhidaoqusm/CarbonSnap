<template>
  <span class="prompt-version-badge">
    <span class="prompt-version-badge__name">{{ displayName }}</span>
    <span class="prompt-version-badge__version">{{ displayVersion }}</span>
  </span>
</template>

<script setup>
import { computed } from "vue";

const props = defineProps({
  name: {
    type: String,
    required: true,
  },
  version: {
    type: String,
    required: true,
  },
});

const displayName = computed(() =>
  String(props.name || "")
    .replace(/_/g, " ")
    .replace(/\b\w/g, (letter) => letter.toUpperCase()),
);
const displayVersion = computed(() => String(props.version || "").trim());
</script>

<style scoped>
.prompt-version-badge {
  align-items: center;
  display: inline-flex;
  min-width: 0;
  overflow: hidden;
  border: 1px solid rgba(15, 118, 110, 0.2);
  border-radius: 8px;
  background: rgba(240, 253, 250, 0.92);
  color: #134e4a;
  font-size: 0.78rem;
  font-weight: 700;
  line-height: 1.2;
}

.prompt-version-badge__name,
.prompt-version-badge__version {
  min-width: 0;
  overflow: hidden;
  padding: 4px 7px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.prompt-version-badge__name {
  border-right: 1px solid rgba(15, 118, 110, 0.16);
}

.prompt-version-badge__version {
  color: #0f766e;
  font-family: "Consolas", "Courier New", monospace;
}
</style>
