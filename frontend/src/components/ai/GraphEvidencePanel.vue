<template>
  <section v-if="hasEvidence" class="graph-evidence-panel" aria-label="Graph evidence">
    <header class="graph-evidence-panel__header">
      <h4 class="graph-evidence-panel__title">Graph Evidence</h4>
      <span v-if="confidenceLabel" class="graph-evidence-panel__confidence">
        {{ confidenceLabel }}
      </span>
    </header>

    <ol v-if="normalizedPaths.length" class="graph-evidence-panel__paths">
      <li
        v-for="(path, index) in normalizedPaths"
        :key="`${path.from}-${path.relation}-${path.to}-${index}`"
      >
        <span>{{ path.from }}</span>
        <strong>{{ formatRelation(path.relation) }}</strong>
        <span>{{ path.to }}</span>
      </li>
    </ol>

    <div v-if="normalizedRelationFacts.length" class="graph-evidence-panel__group">
      <h5>Forum Facts</h5>
      <ul>
        <li v-for="fact in normalizedRelationFacts" :key="fact.id || `${fact.subject}-${fact.relation}-${fact.object}`">
          <strong>{{ fact.subject }} -- {{ formatRelation(fact.relation) }} -- {{ fact.object }}</strong>
          <span v-if="fact.supportCount">
            {{ fact.supportCount }} supporting source{{ fact.supportCount === 1 ? "" : "s" }}
          </span>
        </li>
      </ul>
    </div>

    <div v-if="normalizedRules.length" class="graph-evidence-panel__group">
      <h5>Rules</h5>
      <ul>
        <li v-for="rule in normalizedRules" :key="rule.id || rule.title">
          <strong>{{ rule.title || rule.id }}</strong>
          <span v-if="rule.description">{{ rule.description }}</span>
          <em v-if="rule.locality">{{ rule.locality }}</em>
        </li>
      </ul>
    </div>

    <div v-if="normalizedRisks.length" class="graph-evidence-panel__group">
      <h5>Risks</h5>
      <ul>
        <li v-for="risk in normalizedRisks" :key="risk.name">
          <strong>{{ risk.name }}</strong>
          <span v-if="risk.description">{{ risk.description }}</span>
          <em v-if="risk.severity">{{ formatRelation(risk.severity) }}</em>
        </li>
      </ul>
    </div>
  </section>
</template>

<script setup>
import { computed } from "vue";

const props = defineProps({
  paths: {
    type: Array,
    default: () => [],
  },
  rules: {
    type: Array,
    default: () => [],
  },
  risks: {
    type: Array,
    default: () => [],
  },
  relationFacts: {
    type: Array,
    default: () => [],
  },
  confidence: {
    type: String,
    default: "",
  },
});

const normalizedPaths = computed(() =>
  props.paths
    .filter((path) => path && path.from && path.relation && path.to)
    .map((path) => ({
      from: String(path.from),
      relation: String(path.relation),
      to: String(path.to),
    })),
);

const normalizedRules = computed(() =>
  props.rules
    .filter((rule) => rule && (rule.title || rule.id || rule.description))
    .map((rule) => ({
      id: rule.id ? String(rule.id) : "",
      title: rule.title ? String(rule.title) : "",
      description: rule.description ? String(rule.description) : "",
      locality: rule.locality ? String(rule.locality) : "",
    })),
);

const normalizedRisks = computed(() =>
  props.risks
    .filter((risk) => risk && (risk.name || risk.description))
    .map((risk) => ({
      name: risk.name ? String(risk.name) : "Unnamed risk",
      description: risk.description ? String(risk.description) : "",
      severity: risk.severity ? String(risk.severity) : "",
    })),
);

const normalizedRelationFacts = computed(() =>
  props.relationFacts
    .filter(
      (fact) =>
        fact &&
        (fact.subject || fact.subject_key) &&
        (fact.relation || fact.relation_key) &&
        (fact.object || fact.object_key),
    )
    .map((fact) => ({
      id: fact.id ? String(fact.id) : "",
      subject: String(fact.subject || fact.subject_key),
      relation: String(fact.relation || fact.relation_key),
      object: String(fact.object || fact.object_key),
      supportCount: Number(fact.support_count || 0),
    })),
);

const hasEvidence = computed(
  () =>
    normalizedPaths.value.length ||
    normalizedRelationFacts.value.length ||
    normalizedRules.value.length ||
    normalizedRisks.value.length,
);

const confidenceLabel = computed(() => {
  const value = String(props.confidence || "").trim();
  return value ? `${formatRelation(value)} confidence` : "";
});

function formatRelation(value) {
  return String(value || "")
    .replace(/[_-]/g, " ")
    .replace(/\s+/g, " ")
    .trim()
    .toLowerCase()
    .replace(/\b\w/g, (letter) => letter.toUpperCase());
}
</script>

<style scoped>
.graph-evidence-panel {
  border: 1px solid rgba(15, 118, 110, 0.13);
  border-radius: 8px;
  background: #ffffff;
  display: grid;
  gap: 9px;
  padding: 9px;
}

.graph-evidence-panel__header {
  align-items: center;
  display: flex;
  gap: 8px;
  justify-content: space-between;
  min-width: 0;
}

.graph-evidence-panel__title {
  color: #123d38;
  font-size: 0.8rem;
  font-weight: 800;
  margin: 0;
}

.graph-evidence-panel__confidence {
  background: #eef6ff;
  border: 1px solid rgba(37, 99, 235, 0.12);
  border-radius: 999px;
  color: #1d4e89;
  flex: 0 0 auto;
  font-size: 0.72rem;
  font-weight: 800;
  padding: 3px 7px;
}

.graph-evidence-panel__paths {
  display: grid;
  gap: 6px;
  list-style: none;
  margin: 0;
  padding: 0;
}

.graph-evidence-panel__paths li {
  align-items: center;
  background: #f8fbfb;
  border: 1px solid rgba(15, 118, 110, 0.1);
  border-radius: 8px;
  display: grid;
  gap: 5px;
  grid-template-columns: minmax(0, 1fr) auto minmax(0, 1fr);
  padding: 7px 8px;
}

.graph-evidence-panel__paths span {
  color: #123d38;
  font-size: 0.8rem;
  font-weight: 700;
  overflow-wrap: anywhere;
}

.graph-evidence-panel__paths strong {
  background: #ecfdf5;
  border-radius: 999px;
  color: #0f766e;
  font-size: 0.68rem;
  font-weight: 800;
  padding: 3px 7px;
  text-align: center;
  white-space: nowrap;
}

.graph-evidence-panel__group {
  display: grid;
  gap: 5px;
}

.graph-evidence-panel__group h5 {
  color: #486560;
  font-size: 0.74rem;
  font-weight: 800;
  margin: 0;
}

.graph-evidence-panel__group ul {
  display: grid;
  gap: 5px;
  list-style: none;
  margin: 0;
  padding: 0;
}

.graph-evidence-panel__group li {
  display: grid;
  gap: 3px;
  border-left: 3px solid rgba(15, 118, 110, 0.18);
  padding-left: 8px;
}

.graph-evidence-panel__group strong {
  color: #123d38;
  font-size: 0.8rem;
}

.graph-evidence-panel__group span,
.graph-evidence-panel__group em {
  color: #607975;
  font-size: 0.76rem;
  font-style: normal;
  line-height: 1.4;
}

@media (max-width: 520px) {
  .graph-evidence-panel__paths li {
    grid-template-columns: 1fr;
  }

  .graph-evidence-panel__paths strong {
    justify-self: start;
  }
}
</style>
