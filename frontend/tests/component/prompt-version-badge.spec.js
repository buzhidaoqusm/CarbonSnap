import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";

import PromptVersionBadge from "../../src/components/ai/PromptVersionBadge.vue";

describe("PromptVersionBadge", () => {
  it("renders prompt name and version", () => {
    const wrapper = mount(PromptVersionBadge, {
      props: {
        name: "general_chat_answer",
        version: "general-chat-answer-v1",
      },
    });

    expect(wrapper.text()).toContain("General Chat Answer");
    expect(wrapper.text()).toContain("general-chat-answer-v1");
  });
});
