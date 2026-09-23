import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";

import MemoryPanel from "../../src/components/ai/MemoryPanel.vue";


describe("MemoryPanel", () => {
  it("renders grouped memory items and delete action", () => {
    const wrapper = mount(MemoryPanel, {
      props: {
        summary: {
          action_preferences: {
            response_style: "concise",
          },
          content_interest_preferences: {
            topics: [{ topic_id: "battery-recycling", score: 0.88, event_count: 2 }],
            confidence_score: 0.88,
          },
        },
        items: [
          {
            id: 1,
            memory_type: "recycling_preference",
            memory_key: "prefer_nearby_options",
            value: { enabled: true },
          },
          {
            id: 2,
            memory_type: "topic_interest",
            memory_key: "battery",
            value: { topic: "battery" },
          },
        ],
      },
    });

    expect(wrapper.text()).toContain("response style");
    expect(wrapper.text()).toContain("concise");
    expect(wrapper.text()).toContain("recycling preference");
    expect(wrapper.text()).toContain("Nearby options first");
    expect(wrapper.text()).toContain("Enabled");
    expect(wrapper.text()).not.toContain('{"enabled":true}');
    expect(wrapper.text()).toContain("topic interest");
    expect(wrapper.text()).toContain("Recycling behavior topics");
    expect(wrapper.text()).toContain("Delete");
  });

  it("renders loading and empty states", () => {
    const wrapper = mount(MemoryPanel, {
      props: {
        summary: {},
        items: [],
        loading: true,
      },
    });

    expect(wrapper.text()).toContain("Loading memory...");
  });
});
