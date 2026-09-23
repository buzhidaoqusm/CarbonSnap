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
  emits: ["attempt-view-change"],
  template: '<button class="completion-audit-stub" @click="$emit(\'attempt-view-change\', { caseId: caseData?.id, attemptNo: 1, auditResult: \'unclear\' })">Completion audit for {{ caseData?.id }}</button>',
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

describe("AiChatView intent routing", () => {
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

  it("renders backend clarification output for an ambiguous request", async () => {
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
              id: 55,
              title: "Routing chat",
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
        id: 55,
        title: "Routing chat",
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
        conversation_id: 55,
        conversation_title: "Routing chat",
      });
      hasPersistedConversation = true;
      await handlers.onClarification({
        data: {
          question: "Which recycling case do you mean?",
          options: [
            { label: "Battery case", reply_text: "battery case" },
            { label: "Bottle case", reply_text: "bottle case" },
          ],
        },
      });
      handlers.onDone({ stream_stage: "clarification" });
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

    await wrapper.find("textarea").setValue("Can you help me with it?");
    await wrapper.find("form").trigger("submit.prevent");

    await flushPromises();
    await flushPromises();
    await flushPromises();
    await waitForStreaming();

    expect(requests).toHaveLength(1);
    expect(requests[0].message).toBe("Can you help me with it?");
    expect(wrapper.text()).toContain("Need Clarification");
    expect(wrapper.text()).toContain("Which recycling case do you mean?");
    expect(wrapper.text()).toContain("Battery case");
    expect(wrapper.text()).toContain("Bottle case");
  });

  it("includes the currently viewed audit attempt in chat payloads", async () => {
    const { fetchAiConversations, fetchAiConversationMessages } = await import("../../src/api/ai/history.js");
    const { fetchAiMemory } = await import("../../src/api/ai/memory.js");
    const { streamAiChat } = await import("../../src/api/ai/chat.js");
    const AiChatView = (await import("../../src/views/ai/AiChatView.vue")).default;

    const requests = [];

    fetchAiConversations.mockResolvedValue(asResponse({
      items: [
        {
          id: 66,
          title: "Audit follow-up chat",
          status: "completed",
          current_pending_action: "none",
          session_context_json: null,
        },
      ],
      total: 1,
      page: 1,
      per_page: 50,
    }));
    fetchAiConversationMessages.mockResolvedValue(asResponse({
      conversation: {
        id: 66,
        title: "Audit follow-up chat",
        status: "completed",
        current_pending_action: "none",
        session_context_json: null,
      },
      items: [
        {
          id: 90,
          role: "assistant",
          message_type: "tool_result",
          content_text: "Nearby e-waste point summary",
          content_json: {
            recycling_case_id: 7,
            nearby_locations: [{ name: "E-waste point", lat: 1, lng: 2 }],
          },
          related_analysis_id: null,
          sequence_no: 1,
          recycling_case: {
            id: 7,
            status: "audit_passed",
            waste_type_predicted: "power bank",
            expected_carbon_points: 4,
            latest_audit_attempt_no: 2,
            audit_attempts: [
              { id: 1, attempt_no: 1, audit_result: "unclear", audit_reason: "Need clearer proof." },
              { id: 2, attempt_no: 2, audit_result: "passed", audit_reason: "Looks correct." },
            ],
          },
        },
      ],
      total: 1,
      pending_recycling_case: null,
    }));
    fetchAiMemory.mockResolvedValue(asResponse({
      summary: {},
      items: [],
    }));
    streamAiChat.mockImplementation(async (payload, handlers) => {
      requests.push(payload);
      handlers.onMeta({
        conversation_id: 66,
        conversation_title: "Audit follow-up chat",
      });
      handlers.onDelta("Explaining the attempt.");
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

    await wrapper.find(".completion-audit-stub").trigger("click");
    await wrapper.find("textarea").setValue("Why did it fail?");
    await wrapper.find("form").trigger("submit.prevent");

    await flushPromises();
    await flushPromises();
    await flushPromises();

    expect(requests).toHaveLength(1);
    expect(requests[0].client_context).toEqual({
      selected_audit_attempt: {
        case_id: 7,
        attempt_no: 1,
        audit_result: "unclear",
      },
    });
  });
});
