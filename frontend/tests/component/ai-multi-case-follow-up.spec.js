import { asResponse } from "../helpers/fetch.js";
import { defineComponent, h, nextTick } from "vue";
import { mount } from "@vue/test-utils";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("../../src/api/ai/history.js", () => ({
  fetchAiConversations: vi.fn(),
  fetchAiConversationMessages: vi.fn(),
}));

vi.mock("../../src/api/ai/memory.js", () => ({
  fetchAiMemory: vi.fn(),
  deleteAiMemoryItem: vi.fn(),
}));

vi.mock("../../src/api/ai/chat.js", () => ({
  resumeRecyclingAnalysis: vi.fn(),
  streamRecyclingAudit: vi.fn(),
  streamAiChat: vi.fn(),
  streamRecyclingAnalysis: vi.fn(),
  submitLocationContext: vi.fn(),
}));

vi.mock("../../src/composables/useAuth.js", () => ({
  useAuth: () => ({
    user: { value: { username: "Alice", avatar_url: "" } },
    isLoggedIn: { value: true },
  }),
}));

const HeaderOnlyLayoutStub = defineComponent({
  name: "HeaderOnlyLayoutStub",
  setup(_, { slots }) {
    return () => h("div", { class: "header-only-layout-stub" }, slots.default?.());
  },
});

const CompletionAuditComposerStub = defineComponent({
  name: "CompletionAuditComposerStub",
  props: {
    caseData: {
      type: Object,
      default: null,
    },
  },
  template: '<div class="completion-audit-stub">Completion audit for {{ caseData?.id }}</div>',
});

const NearbyMapCardStub = defineComponent({
  name: "NearbyMapCardStub",
  template: '<div class="nearby-map-stub">Nearby map</div>',
});

const MemoryPanelStub = defineComponent({
  name: "MemoryPanelStub",
  template: '<div class="memory-panel-stub">Memory panel</div>',
});

const flushPromises = async () => {
  await Promise.resolve();
  await nextTick();
  await new Promise((resolve) => setTimeout(resolve, 0));
};

const waitForStreaming = (ms = 3200) => new Promise((resolve) => setTimeout(resolve, ms));

describe("AiChatView multi-case follow-up", () => {
  beforeEach(() => {
    vi.stubGlobal(
      "crypto",
      globalThis.crypto || {
        randomUUID: () => "test-uuid",
      },
    );
    Object.defineProperty(window, "innerWidth", {
      writable: true,
      configurable: true,
      value: 1280,
    });
  });

  afterEach(() => {
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
  });

  it("replays a clarification option as a resolved follow-up with explicit context", async () => {
    const { fetchAiConversations, fetchAiConversationMessages } = await import("../../src/api/ai/history.js");
    const { fetchAiMemory } = await import("../../src/api/ai/memory.js");
    const { streamAiChat } = await import("../../src/api/ai/chat.js");
    const AiChatView = (await import("../../src/views/ai/AiChatView.vue")).default;

    let hasPersistedConversation = false;
    const requests = [];

    fetchAiConversations.mockImplementation(async () => ({
      items: hasPersistedConversation
        ? [
            {
              id: 72,
              title: "Follow-up chat",
              status: "active",
              current_pending_action: "none",
              session_context_json: null,
            },
          ]
        : [],
      total: hasPersistedConversation ? 1 : 0,
      page: 1,
      per_page: 50,
    }));
    fetchAiConversationMessages.mockResolvedValue(asResponse({
      conversation: {
        id: 72,
        title: "Follow-up chat",
        status: "active",
        current_pending_action: "none",
        session_context_json: null,
      },
      items: [],
      total: 0,
      pending_recycling_case: null,
    }));
    fetchAiMemory.mockResolvedValue(asResponse({
      summary: {},
      items: [],
    }));
    streamAiChat.mockImplementation(async (payload, handlers) => {
      requests.push(payload);
      handlers.onMeta({
        conversation_id: 72,
        conversation_title: "Follow-up chat",
      });

      if (requests.length === 1) {
        hasPersistedConversation = true;
        await handlers.onClarification({
          data: {
            question: "Which item do you mean?",
            options: [
              { label: "Battery case", reply_text: "Okay, please wait." },
              { label: "Bottle case", reply_text: "Okay, please wait." },
            ],
          },
        });
        handlers.onDone({ stream_stage: "clarification" });
        return;
      }

      handlers.onDelta("Understood.");
      handlers.onDone({ stream_stage: "completed" });
    });

    const wrapper = mount(AiChatView, {
      global: {
        stubs: {
          HeaderOnlyLayout: HeaderOnlyLayoutStub,
          CompletionAuditComposer: CompletionAuditComposerStub,
          NearbyMapCard: NearbyMapCardStub,
          MemoryPanel: MemoryPanelStub,
        },
      },
    });

    await flushPromises();
    await flushPromises();

    await wrapper.find("textarea").setValue("I need more help with that.");
    await wrapper.find("form").trigger("submit.prevent");

    await flushPromises();
    await flushPromises();
    await flushPromises();
    await waitForStreaming();

    expect(wrapper.text()).toContain("Which item do you mean?");
    expect(wrapper.text()).toContain("Battery case");
    expect(requests).toHaveLength(1);

    await wrapper.find("textarea").setValue("I am still thinking.");
    await wrapper.find("form").trigger("submit.prevent");

    await flushPromises();
    await flushPromises();
    await flushPromises();
    await waitForStreaming();

    expect(requests).toHaveLength(2);
    expect(wrapper.text()).toContain("Which item do you mean?");
    expect(wrapper.text()).toContain("Battery case");

    await wrapper.findAll(".chat-card__button").find((button) => button.text() === "Battery case").trigger("click");

    await flushPromises();
    await flushPromises();
    await flushPromises();
    await waitForStreaming();

    expect(requests).toHaveLength(3);
    expect(requests[2].message).toContain("Clarification question: Which item do you mean?");
    expect(requests[2].message).toContain("Selected option: Battery case");
    expect(requests[2].message).toContain("Okay, please wait.");
    expect(requests[2].history).toEqual(
      expect.arrayContaining([
        expect.objectContaining({
          role: "assistant",
          content: expect.stringContaining("Clarification question: Which item do you mean?"),
        }),
      ]),
    );
    expect(wrapper.text()).toContain('Selected "Battery case". Continuing...');
    expect(wrapper.text()).not.toContain("Bottle case");
    const assistantTranscript = wrapper
      .findAll(".chat-message--assistant .chat-message__bubble")
      .map((node) => node.text())
      .join(" ");
    expect(assistantTranscript).toContain("Understood");
  }, 12000);
});
