import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";

import GraphEvidencePanel from "../../src/components/ai/GraphEvidencePanel.vue";

describe("GraphEvidencePanel", () => {
  it("renders readable graph paths and evidence without raw JSON", () => {
    const wrapper = mount(GraphEvidencePanel, {
      props: {
        confidence: "medium",
        paths: [
          { from: "battery", relation: "HAS_RISK", to: "fire hazard" },
          { from: "battery", relation: "DISPOSE_AS", to: "hazardous drop-off" },
        ],
        rules: [
          {
            id: "battery-dropoff",
            title: "Use certified drop-off",
            description: "Do not place loose batteries in curbside bins.",
            locality: "General",
          },
        ],
        risks: [
          {
            name: "fire hazard",
            description: "Damaged lithium batteries can ignite during collection.",
            severity: "high",
          },
        ],
        relationFacts: [
          {
            id: "fact-1",
            subject: "plastic bottle",
            relation: "can_be_reused_as",
            object: "mini lantern",
            support_count: 2,
          },
        ],
      },
    });

    expect(wrapper.text()).toContain("Graph Evidence");
    expect(wrapper.text()).toContain("Medium confidence");
    expect(wrapper.text()).toContain("battery");
    expect(wrapper.text()).toContain("Has Risk");
    expect(wrapper.text()).toContain("Dispose As");
    expect(wrapper.text()).toContain("Use certified drop-off");
    expect(wrapper.text()).toContain("fire hazard");
    expect(wrapper.text()).toContain("Forum Facts");
    expect(wrapper.text()).toContain("plastic bottle");
    expect(wrapper.text()).toContain("Can Be Reused As");
    expect(wrapper.text()).toContain("2 supporting sources");
    expect(wrapper.text()).not.toContain('"relation"');
    expect(wrapper.text()).not.toContain("{");
  });

  it("does not render without graph evidence", () => {
    const wrapper = mount(GraphEvidencePanel);

    expect(wrapper.html()).toBe("<!--v-if-->");
  });
});
