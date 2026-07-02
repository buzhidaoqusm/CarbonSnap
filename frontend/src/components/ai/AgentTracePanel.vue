<template>
  <details v-if="hasTrace" class="agent-trace-panel">
    <summary class="agent-trace-panel__summary">
      <span class="agent-trace-panel__title">Agent Trace</span>
      <span class="agent-trace-panel__meta">{{ summaryText }}</span>
    </summary>

    <div class="agent-trace-panel__body">
      <section class="agent-trace-panel__section">
        <h3 class="agent-trace-panel__heading">Router</h3>
        <dl class="agent-trace-panel__grid">
          <div>
            <dt>Intent</dt>
            <dd>{{ router.intent || "unknown" }}</dd>
          </div>
          <div>
            <dt>Confidence</dt>
            <dd>{{ formatConfidence(router.confidence) }}</dd>
          </div>
          <div>
            <dt>Fallback</dt>
            <dd>{{ router.used_fallback ? router.fallback_mode || "applied" : "none" }}</dd>
          </div>
        </dl>
      </section>

      <section class="agent-trace-panel__section">
        <h3 class="agent-trace-panel__heading">Retrieval</h3>
        <dl class="agent-trace-panel__grid">
          <div>
            <dt>Forum</dt>
            <dd>{{ forumStatus }}</dd>
          </div>
          <div>
            <dt>Neo4j</dt>
            <dd>{{ neo4jStatus }}</dd>
          </div>
          <div>
            <dt>Blocked</dt>
            <dd>{{ blockedCount }}</dd>
          </div>
        </dl>
        <ul v-if="forumCitations.length" class="agent-trace-panel__references" aria-label="Forum citations used">
          <li v-for="citation in forumCitations" :key="citation.reference_id || citation.url || citation.title">
            <a v-if="citation.url" :href="citation.url">{{ citation.title || citation.url }}</a>
            <span v-else>{{ citation.title || "Untitled forum citation" }}</span>
          </li>
        </ul>
        <GraphEvidencePanel
          v-if="hasGraphEvidence"
          :paths="graphPaths"
          :rules="graphRules"
          :risks="graphRisks"
          :relation-facts="graphRelationFacts"
          :confidence="neo4j.confidence"
        />
      </section>

      <section v-if="guardrailReasons.length || guardrails.fallback_applied" class="agent-trace-panel__section">
        <h3 class="agent-trace-panel__heading">Guardrails</h3>
        <p class="agent-trace-panel__copy">
          {{ guardrails.fallback_applied ? "Fallback applied" : "No fallback" }}
        </p>
        <ul v-if="guardrailReasons.length" class="agent-trace-panel__list">
          <li v-for="reason in guardrailReasons" :key="reason">{{ reason }}</li>
        </ul>
      </section>

      <section v-if="toolCalls.length" class="agent-trace-panel__section">
        <h3 class="agent-trace-panel__heading">Tools</h3>
        <ul class="agent-trace-panel__tools">
          <li v-for="tool in toolCalls" :key="tool.name || tool.tool_name">
            <span class="agent-trace-panel__tool-name">{{ tool.name || tool.tool_name }}</span>
            <span v-if="tool.risk_level" class="agent-trace-panel__tool-chip">
              {{ tool.risk_level }}
            </span>
            <span v-if="tool.execution_mode" class="agent-trace-panel__tool-chip">
              {{ formatLabel(tool.execution_mode) }}
            </span>
            <span v-if="tool.reason" class="agent-trace-panel__tool-reason">
              {{ formatLabel(tool.reason) }}
            </span>
          </li>
        </ul>
      </section>

      <section v-if="promptEntries.length" class="agent-trace-panel__section">
        <h3 class="agent-trace-panel__heading">Prompts</h3>
        <div class="agent-trace-panel__badges">
          <PromptVersionBadge
            v-for="[name, version] in promptEntries"
            :key="name"
            :name="name"
            :version="String(version)"
          />
        </div>
      </section>

      <section v-if="timingEntries.length" class="agent-trace-panel__section">
        <h3 class="agent-trace-panel__heading">Timing</h3>
        <dl class="agent-trace-panel__grid">
          <div v-for="[name, value] in timingEntries" :key="name">
            <dt>{{ formatLabel(name) }}</dt>
            <dd>{{ value }}</dd>
          </div>
        </dl>
      </section>
    </div>
  </details>
</template>

<script setup>
import { computed } from "vue";

import GraphEvidencePanel from "./GraphEvidencePanel.vue";
import PromptVersionBadge from "./PromptVersionBadge.vue";

const props = defineProps({
  trace: {
    type: Object,
    default: null,
  },
});

const hasTrace = computed(() => Boolean(props.trace && typeof props.trace === "object"));
const router = computed(() => props.trace?.router || {});
const retrieval = computed(() => props.trace?.retrieval || {});
const forum = computed(() => retrieval.value.forum || {});
const neo4j = computed(() => retrieval.value.neo4j || {});
const guardrails = computed(() => props.trace?.guardrails || {});
const guardrailReasons = computed(() =>
  Array.isArray(guardrails.value.reasons) ? guardrails.value.reasons.filter(Boolean) : [],
);
const toolCalls = computed(() =>
  Array.isArray(props.trace?.tool_calls) ? props.trace.tool_calls.filter(Boolean) : [],
);
const promptEntries = computed(() =>
  Object.entries(props.trace?.prompt_versions || {}).filter(([, version]) => version),
);
const timingEntries = computed(() =>
  Object.entries(props.trace?.timing || {}).filter(([, value]) => value !== null && value !== undefined && value !== ""),
);
const forumCitations = computed(() =>
  Array.isArray(forum.value.citations)
    ? forum.value.citations.filter((citation) => citation && typeof citation === "object")
    : [],
);
const blockedCount = computed(() => {
  const blocked = forum.value.blocked;
  return Array.isArray(blocked) ? blocked.length : Number(forum.value.blocked_count || 0);
});
const citationCount = computed(() => {
  return forumCitations.value.length || Number(forum.value.citation_count || 0);
});
const pathCount = computed(() => {
  const paths = neo4j.value.paths;
  return Array.isArray(paths) ? paths.length : Number(neo4j.value.path_count || 0);
});
const relationFactCount = computed(() => {
  const relationFacts = neo4j.value.relation_facts;
  return Array.isArray(relationFacts) ? relationFacts.length : Number(neo4j.value.relation_fact_count || 0);
});
const graphPaths = computed(() => (Array.isArray(neo4j.value.paths) ? neo4j.value.paths.filter(Boolean) : []));
const graphRules = computed(() => (Array.isArray(neo4j.value.rules) ? neo4j.value.rules.filter(Boolean) : []));
const graphRisks = computed(() => (Array.isArray(neo4j.value.risks) ? neo4j.value.risks.filter(Boolean) : []));
const graphRelationFacts = computed(() =>
  Array.isArray(neo4j.value.relation_facts) ? neo4j.value.relation_facts.filter(Boolean) : [],
);
const hasGraphEvidence = computed(
  () =>
    graphPaths.value.length ||
    graphRelationFacts.value.length ||
    graphRules.value.length ||
    graphRisks.value.length,
);
const forumStatus = computed(() =>
  forum.value.enabled ? `${citationCount.value} citation${citationCount.value === 1 ? "" : "s"}` : "disabled",
);
const neo4jStatus = computed(() => {
  if (!neo4j.value.enabled) {
    return "disabled";
  }
  const parts = [];
  if (pathCount.value) {
    parts.push(`${pathCount.value} path${pathCount.value === 1 ? "" : "s"}`);
  }
  if (relationFactCount.value) {
    parts.push(`${relationFactCount.value} fact${relationFactCount.value === 1 ? "" : "s"}`);
  }
  return parts.length ? parts.join(", ") : "0 evidence";
});
const summaryText = computed(() => {
  const intent = router.value.intent || "unknown";
  const forumLabel = forum.value.enabled ? "forum on" : "forum off";
  const neo4jLabel = neo4j.value.enabled ? "graph on" : "graph off";
  return `${intent} · ${forumLabel} · ${neo4jLabel}`;
});

function formatConfidence(value) {
  const numeric = Number(value);
  if (!Number.isFinite(numeric)) {
    return "n/a";
  }
  return `${Math.round(numeric * 100)}%`;
}

function formatLabel(value) {
  return String(value || "")
    .replace(/_/g, " ")
    .replace(/\b\w/g, (letter) => letter.toUpperCase());
}
</script>

<style scoped>
.agent-trace-panel {
  overflow: hidden;
  border: 1px solid rgba(15, 118, 110, 0.14);
  border-radius: 10px;
  background: rgba(247, 252, 250, 0.9);
  margin-top: 10px;
}

.agent-trace-panel__summary {
  align-items: center;
  cursor: pointer;
  display: flex;
  gap: 10px;
  justify-content: space-between;
  min-height: 38px;
  padding: 9px 11px;
}

.agent-trace-panel__title {
  color: #0f3f3a;
  font-size: 0.88rem;
  font-weight: 800;
}

.agent-trace-panel__meta {
  color: #54716d;
  font-size: 0.78rem;
  font-weight: 700;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.agent-trace-panel__body {
  display: grid;
  gap: 10px;
  border-top: 1px solid rgba(15, 118, 110, 0.12);
  padding: 11px;
}

.agent-trace-panel__section {
  display: grid;
  gap: 8px;
}

.agent-trace-panel__heading {
  color: #365a56;
  font-family: var(--cs-font-heading, "Trebuchet MS", sans-serif);
  font-size: 0.82rem;
  margin: 0;
}

.agent-trace-panel__grid {
  display: grid;
  gap: 8px;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  margin: 0;
}

.agent-trace-panel__grid div {
  min-width: 0;
  border: 1px solid rgba(15, 118, 110, 0.12);
  border-radius: 8px;
  background: #ffffff;
  padding: 8px;
}

.agent-trace-panel__grid dt {
  color: #607975;
  font-size: 0.72rem;
  font-weight: 800;
  margin: 0 0 4px;
}

.agent-trace-panel__grid dd {
  color: #123d38;
  font-size: 0.86rem;
  font-weight: 700;
  margin: 0;
  overflow-wrap: anywhere;
}

.agent-trace-panel__copy {
  color: #486560;
  font-size: 0.86rem;
  margin: 0;
}

.agent-trace-panel__list {
  display: grid;
  gap: 5px;
  margin: 0;
  padding-left: 18px;
}

.agent-trace-panel__list li {
  color: #486560;
  font-size: 0.84rem;
}

.agent-trace-panel__tools {
  display: grid;
  gap: 7px;
  list-style: none;
  margin: 0;
  padding: 0;
}

.agent-trace-panel__tools li {
  align-items: center;
  background: #ffffff;
  border: 1px solid rgba(15, 118, 110, 0.12);
  border-radius: 8px;
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  min-width: 0;
  padding: 7px 8px;
}

.agent-trace-panel__tool-name {
  color: #123d38;
  font-family: Consolas, "Courier New", monospace;
  font-size: 0.8rem;
  font-weight: 800;
  overflow-wrap: anywhere;
}

.agent-trace-panel__tool-chip {
  background: #ecfdf5;
  border: 1px solid rgba(15, 118, 110, 0.12);
  border-radius: 999px;
  color: #0f766e;
  font-size: 0.72rem;
  font-weight: 800;
  padding: 3px 7px;
}

.agent-trace-panel__tool-reason {
  color: #607975;
  font-size: 0.76rem;
  font-weight: 700;
  overflow-wrap: anywhere;
}

.agent-trace-panel__references {
  display: grid;
  gap: 5px;
  margin: 0;
  padding-left: 18px;
}

.agent-trace-panel__references li {
  color: #486560;
  font-size: 0.84rem;
}

.agent-trace-panel__references a {
  color: #007c75;
  font-weight: 700;
  text-decoration: underline;
  text-underline-offset: 2px;
}

.agent-trace-panel__badges {
  display: flex;
  flex-wrap: wrap;
  gap: 7px;
}

@media (max-width: 640px) {
  .agent-trace-panel__summary {
    align-items: flex-start;
    flex-direction: column;
  }

  .agent-trace-panel__grid {
    grid-template-columns: 1fr;
  }
}
</style>
