<template>
  <aside class="memory-panel">
    <header class="memory-panel__header">
      <div>
        <h2 class="memory-panel__title">{{ t("ai.memory") }}</h2>
        <p class="memory-panel__subtitle">{{ t("ai.memorySubtitle") }}</p>
      </div>
      <button class="memory-panel__close" type="button" @click="$emit('close')">{{ t("common.close") }}</button>
    </header>

    <div v-if="loading" class="memory-panel__state">{{ t("ai.loadingMemory") }}</div>
    <p v-else-if="error" class="memory-panel__error">{{ error }}</p>
    <div v-else class="memory-panel__body">
      <section class="memory-panel__group">
        <h3 class="memory-panel__group-title">{{ t("ai.memoryResponseStyle") }}</h3>
        <p v-if="responseStyle" class="memory-panel__summary-chip">
          {{ responseStyle }}
        </p>
        <p v-else class="memory-panel__empty">{{ t("ai.memoryEmptyResponseStyle") }}</p>
      </section>

      <section class="memory-panel__group">
        <h3 class="memory-panel__group-title">{{ t("ai.memoryPreference") }}</h3>
        <ul v-if="recyclingPreferences.length" class="memory-panel__list">
          <li v-for="item in recyclingPreferences" :key="item.id" class="memory-panel__item">
            <div>
              <p class="memory-panel__item-key">{{ formatMemoryKey(item) }}</p>
              <p class="memory-panel__item-value">{{ formatValue(item.value) }}</p>
            </div>
            <button v-if="item.id" class="memory-panel__delete" type="button" @click="$emit('delete', item.id)">
              {{ t("common.delete") }}
            </button>
          </li>
        </ul>
        <p v-else class="memory-panel__empty">{{ t("ai.memoryEmptyPreferences") }}</p>
      </section>

      <section class="memory-panel__group">
        <h3 class="memory-panel__group-title">{{ t("ai.memoryTopicInterest") }}</h3>
        <ul v-if="contentInterestTopics.length" class="memory-panel__list">
          <li v-for="item in contentInterestTopics" :key="item.id || item.topic_id" class="memory-panel__item">
            <div>
              <p class="memory-panel__item-key">{{ formatMemoryKey(item) }}</p>
              <p class="memory-panel__item-value">{{ formatTopicValue(item) }}</p>
            </div>
            <button v-if="item.id" class="memory-panel__delete" type="button" @click="$emit('delete', item.id)">
              {{ t("common.delete") }}
            </button>
          </li>
        </ul>
        <p v-else class="memory-panel__empty">{{ t("ai.memoryEmptyTopics") }}</p>
      </section>

      <section class="memory-panel__group">
        <h3 class="memory-panel__group-title">{{ t("ai.memoryItemMethods") }}</h3>
        <ul v-if="itemMethodItems.length" class="memory-panel__list">
          <li v-for="item in itemMethodItems" :key="item.id || item.memory_key" class="memory-panel__item">
            <div>
              <p class="memory-panel__item-key">{{ formatMemoryKey(item) }}</p>
              <p class="memory-panel__item-value">{{ formatValue(item.value) }}</p>
            </div>
            <button v-if="item.id" class="memory-panel__delete" type="button" @click="$emit('delete', item.id)">
              {{ t("common.delete") }}
            </button>
          </li>
        </ul>
        <p v-else class="memory-panel__empty">{{ t("ai.memoryEmptyItemMethods") }}</p>
      </section>

      <section class="memory-panel__group">
        <h3 class="memory-panel__group-title">{{ t("ai.memoryBehaviorTopics") }}</h3>
        <ul v-if="behaviorTopics.length" class="memory-panel__list">
          <li v-for="topic in behaviorTopics" :key="topic.topic_id" class="memory-panel__item">
            <div>
              <p class="memory-panel__item-key">{{ topic.topic_id }}</p>
              <p class="memory-panel__item-value">
                {{ t("ai.memoryScore", { score: formatScore(topic.score) }) }}
                <span v-if="topic.source_count"> · {{ t("ai.memoryCaseCount", { count: topic.source_count }) }}</span>
              </p>
            </div>
          </li>
        </ul>
        <p v-else class="memory-panel__empty">{{ t("ai.memoryEmptyBehavior") }}</p>
      </section>
    </div>
  </aside>
</template>

<script setup>
import { computed } from "vue";
import { useI18n } from "../../i18n/index.js";

const props = defineProps({
  summary: {
    type: Object,
    default: () => ({}),
  },
  items: {
    type: Array,
    default: () => [],
  },
  loading: {
    type: Boolean,
    default: false,
  },
  error: {
    type: String,
    default: "",
  },
});

defineEmits(["close", "delete"]);
const { t } = useI18n();

const responseStyle = computed(
  () => props.summary.action_preferences?.response_style || props.summary.response_style || "",
);

function normalizeKeyLabel(value) {
  return String(value || "")
    .replace(/_/g, " ")
    .replace(/-/g, " ")
    .trim();
}

const MEMORY_KEY_LABELS = {
  prefer_nearby_options: "ai.memoryNearbyFirst",
  allow_manual_area_input: "ai.memoryManualArea",
  max_recycling_distance_km: "ai.memoryMaxDistance",
};

const recyclingPreferences = computed(() =>
  props.items.filter((item) => item.memory_type === "recycling_preference").length
    ? props.items.filter((item) => item.memory_type === "recycling_preference")
    : Object.entries(props.summary.action_preferences || {})
        .filter(([key, value]) =>
          ["prefer_nearby_options", "allow_manual_area_input", "max_recycling_distance_km"].includes(key) &&
          value !== null &&
          value !== undefined,
        )
        .map(([key, value]) => ({
          id: null,
          label: normalizeKeyLabel(key),
          memory_key: key,
          value: { value },
        })),
);
const itemMethodItems = computed(() =>
  props.items.filter((item) => item.memory_type === "item_method_preference").length
    ? props.items.filter((item) => item.memory_type === "item_method_preference")
    : (props.summary.action_preferences?.preferred_recycling_methods || []).map((item, index) => ({
        id: null,
        memory_key: item.item_type || `method-${index}`,
        value: { preferred_method: item.preferred_method },
        item_type: item.item_type,
      })),
);
const contentInterestTopics = computed(() => {
  if (props.items.filter((item) => item.memory_type === "topic_interest").length) {
    return props.items.filter((item) => item.memory_type === "topic_interest");
  }

  return (props.summary.content_interest_preferences?.topics || []).map((topic) => ({
    id: null,
    topic_id: topic.topic_id,
    score: topic.score,
    event_count: topic.event_count || topic.source_count || 0,
    source_count: topic.source_count || topic.event_count || 0,
  }));
});
const behaviorTopics = computed(() =>
  (props.summary.content_interest_preferences?.topics || []).filter(
    (topic) => Number(topic.event_count || topic.source_count || 0) > 0,
  ),
);

function formatValue(value) {
  if (!value || typeof value !== "object") {
    return "";
  }
  if (typeof value.enabled === "boolean") {
    return value.enabled ? t("common.enabled") : t("common.disabled");
  }
  if (typeof value.value === "boolean") {
    return value.value ? t("common.enabled") : t("common.disabled");
  }
  if (typeof value.value === "string") {
    return value.value;
  }
  if (typeof value.value === "number") {
    return `${value.value}`;
  }
  if (typeof value.topic === "string") {
    return value.topic;
  }
  if (typeof value.preferred_method === "string") {
    return value.preferred_method;
  }
  return JSON.stringify(value);
}

function formatMemoryKey(item) {
  const rawKey = String(item?.memory_key || item?.label || item?.topic_id || item?.item_type || "").trim();
  if (!rawKey) {
    return "";
  }
  return MEMORY_KEY_LABELS[rawKey] ? t(MEMORY_KEY_LABELS[rawKey]) : normalizeKeyLabel(rawKey);
}

function formatScore(value) {
  const numeric = Number(value || 0);
  if (!Number.isFinite(numeric)) {
    return "0.00";
  }
  return numeric.toFixed(2);
}

function formatTopicValue(item) {
  if (item.value) {
    return formatValue(item.value);
  }
  const segments = [t("ai.memoryScore", { score: formatScore(item.score) })];
  const count = Number(item.event_count || item.source_count || 0);
  if (count) {
    segments.push(t("ai.memoryCaseCount", { count }));
  }
  return segments.join(" · ");
}
</script>

<style scoped>
.memory-panel {
  background: rgba(255, 255, 255, 0.96);
  border-left: 1px solid rgba(9, 30, 66, 0.08);
  box-shadow: -16px 0 32px rgba(9, 30, 66, 0.08);
  display: flex;
  flex-direction: column;
  height: 100%;
  padding: 18px;
}

.memory-panel__header {
  align-items: flex-start;
  display: flex;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 16px;
}

.memory-panel__title {
  color: #0e3f37;
  font-family: "Space Grotesk", "Trebuchet MS", sans-serif;
  font-size: 1.1rem;
  margin: 0;
}

.memory-panel__subtitle {
  color: #55716c;
  margin: 6px 0 0;
}

.memory-panel__close,
.memory-panel__delete {
  background: #ffffff;
  border: 1px solid #cad7e7;
  border-radius: 10px;
  color: #0f766e;
  cursor: pointer;
  font-weight: 700;
  padding: 8px 10px;
}

.memory-panel__body {
  display: flex;
  flex: 1;
  flex-direction: column;
  gap: 16px;
  min-height: 0;
  overflow: auto;
}

.memory-panel__group {
  border: 1px solid #dbe5ef;
  border-radius: 14px;
  padding: 14px;
}

.memory-panel__group-title {
  color: #163f39;
  font-family: "Space Grotesk", "Trebuchet MS", sans-serif;
  font-size: 1rem;
  margin: 0 0 10px;
}

.memory-panel__summary-chip {
  background: rgba(20, 184, 166, 0.14);
  border-radius: 999px;
  color: #0f766e;
  display: inline-block;
  font-weight: 700;
  margin: 0;
  padding: 6px 10px;
}

.memory-panel__list {
  display: flex;
  flex-direction: column;
  gap: 10px;
  list-style: none;
  margin: 0;
  padding: 0;
}

.memory-panel__item {
  align-items: flex-start;
  display: flex;
  justify-content: space-between;
  gap: 12px;
}

.memory-panel__item-key {
  color: #153c36;
  font-weight: 700;
  margin: 0;
}

.memory-panel__item-value {
  color: #5a726d;
  margin: 4px 0 0;
}

.memory-panel__state,
.memory-panel__empty {
  color: #667085;
  margin: 0;
}

.memory-panel__error {
  color: #b91c1c;
  font-weight: 600;
  margin: 0;
}
</style>
