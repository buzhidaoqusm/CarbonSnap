import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";

import AgentTracePanel from "../../src/components/ai/AgentTracePanel.vue";

const trace = {
  schema_version: "graph-agent-trace-v1",
  router: {
    intent: "general_chat",
    confidence: 0.87,
    used_fallback: false,
  },
  retrieval: {
    forum: {
      enabled: true,
      citations: [{ post_id: 12, title: "Bottle Sorting Guide", url: "/forum/posts/12" }],
      blocked: [{ post_id: 99, guardrail_reason: "instruction_override" }],
    },
    neo4j: {
      enabled: true,
      confidence: "medium",
      paths: [{ from: "battery", relation: "HAS_RISK", to: "fire hazard" }],
      rules: [{ id: "battery-rule", title: "Certified drop-off only" }],
      risks: [{ name: "fire hazard", severity: "high" }],
    },
  },
  guardrails: {
    fallback_applied: true,
    reasons: ["instruction_override"],
  },
  tool_calls: [
    {
      name: "search_forum",
      risk_level: "low",
      execution_mode: "planned_for_downstream_nodes",
      reason: "decision_requested_forum_rag",
    },
  ],
  prompt_versions: {
    router: "router-v1",
    general_chat_answer: "general-chat-answer-v1",
  },
  timing: {
    total_ms: 432,
  },
};

describe("AgentTracePanel", () => {
  it("renders trace sections without dumping raw JSON", () => {
    const wrapper = mount(AgentTracePanel, {
      props: {
        trace,
      },
    });

    expect(wrapper.find("details").exists()).toBe(true);
    expect(wrapper.text()).toContain("Agent Trace");
    expect(wrapper.text()).toContain("general_chat");
    expect(wrapper.text()).toContain("1 citation");
    expect(wrapper.text()).toContain("Bottle Sorting Guide");
    expect(wrapper.find('a[href="/forum/posts/12"]').exists()).toBe(true);
    expect(wrapper.text()).toContain("1 path");
    expect(wrapper.text()).toContain("Graph Evidence");
    expect(wrapper.text()).toContain("Has Risk");
    expect(wrapper.text()).toContain("Certified drop-off only");
    expect(wrapper.text()).toContain("instruction_override");
    expect(wrapper.text()).toContain("search_forum");
    expect(wrapper.text()).toContain("low");
    expect(wrapper.text()).toContain("Planned For Downstream Nodes");
    expect(wrapper.text()).toContain("Decision Requested Forum Rag");
    expect(wrapper.text()).toContain("router-v1");
    expect(wrapper.text()).toContain("general-chat-answer-v1");
    expect(wrapper.text()).toContain("432");
    expect(wrapper.text()).not.toContain('"schema_version"');
  });

  it("does not render when trace is empty", () => {
    const wrapper = mount(AgentTracePanel, {
      props: {
        trace: null,
      },
    });

    expect(wrapper.html()).toBe("<!--v-if-->");
  });

  it("counts open graph relation facts as Neo4j evidence", () => {
    const wrapper = mount(AgentTracePanel, {
      props: {
        trace: {
          ...trace,
          retrieval: {
            ...trace.retrieval,
            neo4j: {
              enabled: true,
              confidence: "medium",
              paths: [],
              rules: [],
              risks: [],
              relation_facts: [
                {
                  id: "fact-1",
                  subject: "plastic bottle",
                  relation: "can_be_reused_as",
                  object: "mini lantern",
                  support_count: 1,
                },
              ],
            },
          },
        },
      },
    });

    expect(wrapper.text()).toContain("1 fact");
    expect(wrapper.text()).toContain("Graph Evidence");
    expect(wrapper.text()).toContain("Forum Facts");
    expect(wrapper.text()).toContain("plastic bottle");
    expect(wrapper.text()).toContain("Can Be Reused As");
    expect(wrapper.text()).not.toContain("0 paths");
  });
});
