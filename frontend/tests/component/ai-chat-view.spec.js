import { defineComponent, h, nextTick } from "vue";
import { mount } from "@vue/test-utils";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("../../src/api/ai/history.js", () => ({
  fetchAiConversations: vi.fn(),
  fetchAiConversationMessages: vi.fn(),
  deleteAiConversation: vi.fn(),
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

vi.mock("../../src/utils/imageDataUrl.js", () => ({
  readCompressedImageDataUrl: vi.fn(),
}));

vi.mock("../../src/composables/useAuth.js", () => ({
  useAuth: () => ({
    user: {
      __v_isRef: true,
      value: globalThis.__CARBONSNAP_TEST_USER__ ?? { username: "Alice", avatar_url: "" },
    },
    isLoggedIn: {
      __v_isRef: true,
      value: globalThis.__CARBONSNAP_TEST_IS_LOGGED_IN__ ?? true,
    },
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
    attempts: {
      type: Array,
      default: () => [],
    },
  },
  template: '<div class="completion-audit-stub">Completion audit for {{ caseData?.id }} attempts:{{ attempts.length }}</div>',
});

const NearbyMapCardStub = defineComponent({
  name: "NearbyMapCardStub",
  emits: ["ready"],
  setup(_, { emit }) {
    nextTick(() => emit("ready"));
    return () => h("div", { class: "nearby-map-stub" }, "Nearby map");
  },
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

const waitForStreaming = (ms = 150) => new Promise((resolve) => setTimeout(resolve, ms));

describe("AiChatView", () => {
  beforeEach(() => {
    globalThis.__CARBONSNAP_TEST_IS_LOGGED_IN__ = true;
    globalThis.__CARBONSNAP_TEST_USER__ = { username: "Alice", avatar_url: "" };
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
    window.confirm = vi.fn(() => true);
  });

  afterEach(() => {
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
    delete globalThis.__CARBONSNAP_TEST_IS_LOGGED_IN__;
    delete globalThis.__CARBONSNAP_TEST_USER__;
  });

  it("loads one completion audit card per case and keeps each card anchored after its nearby results", async () => {
    const { fetchAiConversations, fetchAiConversationMessages } = await import("../../src/api/ai/history.js");
    const { fetchAiMemory } = await import("../../src/api/ai/memory.js");
    const AiChatView = (await import("../../src/views/ai/AiChatView.vue")).default;

    const firstCase = {
      id: 44,
      status: "pending_audit",
      waste_type_predicted: "plastic bottle",
      expected_carbon_points: 3,
      latest_audit_attempt_no: 0,
    };
    const secondCase = {
      id: 45,
      status: "audit_failed",
      waste_type_predicted: "battery",
      expected_carbon_points: 5,
      latest_audit_attempt_no: 1,
    };

    fetchAiConversations.mockResolvedValue({
      items: [
        {
          id: 1,
          title: "Stored recycling chat",
          status: "completed",
          current_pending_action: "none",
          session_context_json: null,
        },
      ],
      total: 1,
      page: 1,
      per_page: 50,
    });

    fetchAiConversationMessages.mockResolvedValue({
      conversation: {
        id: 1,
        title: "Stored recycling chat",
        status: "completed",
        current_pending_action: "none",
        session_context_json: null,
      },
      items: [
        {
          id: 10,
          role: "user",
          message_type: "text",
          content_text: "How do I recycle this bottle?",
          content_json: {},
          related_analysis_id: null,
          sequence_no: 1,
          recycling_case: firstCase,
        },
        {
          id: 11,
          role: "assistant",
          message_type: "tool_result",
          content_text: "Bottle nearby summary",
          content_json: {
            recycling_case_id: 44,
            nearby_locations: [{ name: "Bottle point", lat: 1, lng: 2 }],
          },
          related_analysis_id: null,
          sequence_no: 2,
          recycling_case: firstCase,
        },
        {
          id: 12,
          role: "user",
          message_type: "text",
          content_text: "How do I recycle this battery?",
          content_json: {},
          related_analysis_id: null,
          sequence_no: 3,
          recycling_case: secondCase,
        },
        {
          id: 13,
          role: "assistant",
          message_type: "tool_result",
          content_text: "Battery nearby summary",
          content_json: {
            recycling_case_id: 45,
            nearby_locations: [{ name: "Battery point", lat: 3, lng: 4 }],
          },
          related_analysis_id: null,
          sequence_no: 4,
          recycling_case: secondCase,
        },
        {
          id: 14,
          role: "user",
          message_type: "image",
          content_text: "Completion photo uploaded.",
          content_json: {
            purpose: "completion_audit",
            image_url: "/uploads/audit-45.png",
            recycling_case_id: 45,
          },
          related_analysis_id: null,
          sequence_no: 5,
          recycling_case: secondCase,
        },
        {
          id: 15,
          role: "assistant",
          message_type: "audit_result",
          content_text: "Audit failed.",
          content_json: {
            recycling_case_id: 45,
            finalized: false,
            audit_result: {
              audit_result: "failed",
              audit_reason: "Retake photo",
            },
          },
          related_analysis_id: null,
          sequence_no: 6,
          recycling_case: secondCase,
        },
      ],
      total: 6,
      pending_recycling_case: firstCase,
    });
    fetchAiMemory.mockResolvedValue({
      summary: {},
      items: [],
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

    expect(fetchAiConversations).toHaveBeenCalled();
    expect(fetchAiConversationMessages).toHaveBeenCalledWith(1);
    expect(fetchAiMemory).toHaveBeenCalled();
    expect(wrapper.text()).toContain("Stored recycling chat");
    expect(wrapper.text()).toContain("Memory");

    const auditCards = wrapper.findAll(".completion-audit-stub");
    expect(auditCards).toHaveLength(2);
    expect(auditCards[0].text()).toContain("44");
    expect(auditCards[1].text()).toContain("45");

    const initialText = wrapper.text();
    expect(initialText.indexOf("Bottle nearby summary")).toBeLessThan(initialText.indexOf("Completion audit for 44"));
    expect(initialText.indexOf("Battery nearby summary")).toBeLessThan(initialText.indexOf("Completion audit for 45"));

    await wrapper.find(".chat-sidebar__item").trigger("click");
    await flushPromises();
    await flushPromises();

    const refreshedText = wrapper.text();
    expect(refreshedText.indexOf("Bottle nearby summary")).toBeLessThan(refreshedText.indexOf("Completion audit for 44"));
    expect(refreshedText.indexOf("Battery nearby summary")).toBeLessThan(refreshedText.indexOf("Completion audit for 45"));
    expect(wrapper.findAll(".completion-audit-stub")).toHaveLength(2);
  });

  it("keeps the completion audit card visible after nearby results even before the map reports ready", async () => {
    const { fetchAiConversations, fetchAiConversationMessages } = await import("../../src/api/ai/history.js");
    const { fetchAiMemory } = await import("../../src/api/ai/memory.js");
    const AiChatView = (await import("../../src/views/ai/AiChatView.vue")).default;

    const firstCase = {
      id: 101,
      status: "pending_audit",
      waste_type_predicted: "power bank",
      expected_carbon_points: 8,
      latest_audit_attempt_no: 0,
    };

    fetchAiConversations.mockResolvedValue({
      items: [
        {
          id: 1,
          title: "Nearby map ready chat",
          status: "completed",
          current_pending_action: "none",
          session_context_json: null,
        },
      ],
      total: 1,
      page: 1,
      per_page: 50,
    });

    fetchAiConversationMessages.mockResolvedValue({
      conversation: {
        id: 1,
        title: "Nearby map ready chat",
        status: "completed",
        current_pending_action: "none",
        session_context_json: null,
      },
      items: [
        {
          id: 10,
          role: "assistant",
          message_type: "tool_result",
          content_text: "Power bank nearby summary",
          content_json: {
            recycling_case_id: 101,
            nearby_locations: [{ name: "Battery point", lat: 1, lng: 2 }],
          },
          related_analysis_id: null,
          sequence_no: 1,
          recycling_case: firstCase,
        },
      ],
      total: 1,
      pending_recycling_case: firstCase,
    });
    fetchAiMemory.mockResolvedValue({
      summary: {},
      items: [],
    });

    const DelayedNearbyMapCardStub = defineComponent({
      name: "DelayedNearbyMapCardStub",
      emits: ["ready"],
      setup(_, { emit }) {
        return () =>
          h("button", {
            class: "nearby-map-ready-trigger",
            onClick: () => emit("ready"),
          }, "Nearby map");
      },
    });

    const wrapper = mount(AiChatView, {
      global: {
        stubs: {
          HeaderOnlyLayout: HeaderOnlyLayoutStub,
          CompletionAuditComposer: CompletionAuditComposerStub,
          NearbyMapCard: DelayedNearbyMapCardStub,
          MemoryPanel: MemoryPanelStub,
        },
      },
    });

    await flushPromises();
    await flushPromises();

    expect(wrapper.text()).toContain("Power bank nearby summary");
    expect(wrapper.findAll(".completion-audit-stub")).toHaveLength(1);
    expect(wrapper.text()).toContain("Completion audit for 101");

    await wrapper.find(".nearby-map-ready-trigger").trigger("click");
    await flushPromises();
    await flushPromises();

    expect(wrapper.findAll(".completion-audit-stub")).toHaveLength(1);
    expect(wrapper.text()).toContain("Completion audit for 101");
  });

  it("deduplicates audit attempts when the latest audit message repeats an existing attempt number", async () => {
    const { fetchAiConversations, fetchAiConversationMessages } = await import("../../src/api/ai/history.js");
    const { fetchAiMemory } = await import("../../src/api/ai/memory.js");
    const AiChatView = (await import("../../src/views/ai/AiChatView.vue")).default;

    const caseData = {
      id: 202,
      status: "audit_passed",
      waste_type_predicted: "power bank",
      expected_carbon_points: 4,
      latest_audit_attempt_no: 2,
      audit_attempts: [
        {
          id: 2,
          attempt_no: 1,
          audit_result: "unclear",
          audit_reason: "The disposal path is not clear enough.",
          audit_image_url: "/api/uploads/recycling-audit/attempt-1.jpg",
        },
        {
          id: 3,
          attempt_no: 2,
          audit_result: "passed",
          audit_reason: "The photo clearly shows the correct electronics recycling bin.",
          audit_image_url: "/api/uploads/recycling-audit/attempt-2.jpg",
        },
      ],
    };

    fetchAiConversations.mockResolvedValue({
      items: [
        {
          id: 1,
          title: "Duplicate audit attempt chat",
          status: "completed",
          current_pending_action: "none",
          session_context_json: null,
        },
      ],
      total: 1,
      page: 1,
      per_page: 50,
    });

    fetchAiConversationMessages.mockResolvedValue({
      conversation: {
        id: 1,
        title: "Duplicate audit attempt chat",
        status: "completed",
        current_pending_action: "none",
        session_context_json: null,
      },
      items: [
        {
          id: 9,
          role: "assistant",
          message_type: "tool_result",
          content_text: "Nearby e-waste point summary",
          content_json: {
            recycling_case_id: 202,
            nearby_locations: [{ name: "E-waste point", lat: 1, lng: 2 }],
          },
          related_analysis_id: null,
          sequence_no: 1,
          recycling_case: caseData,
        },
        {
          id: 10,
          role: "assistant",
          message_type: "audit_result",
          content_text: "Audit passed. Your recycling case has been verified, and 4 points were awarded.",
          content_json: {
            audit_result: {
              audit_result: "passed",
              audit_reason: "The photo clearly shows the correct electronics recycling bin.",
            },
            audit_attempt: {
              id: 999,
              recycling_case_id: 202,
              attempt_no: 2,
              audit_result: "passed",
              audit_reason: "The photo clearly shows the correct electronics recycling bin.",
              audit_image_url: "/api/uploads/recycling-audit/attempt-2.jpg",
            },
            finalized: true,
            recycling_case_id: 202,
          },
          related_analysis_id: 2,
          sequence_no: 2,
          recycling_case: caseData,
        },
      ],
      total: 2,
      pending_recycling_case: null,
    });
    fetchAiMemory.mockResolvedValue({
      summary: {},
      items: [],
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

    expect(wrapper.text()).toContain("Completion audit for 202 attempts:2");
    expect(wrapper.text()).not.toContain("Completion audit for 202 attempts:3");
  });

  it("hydrates audit attempt history into the completion audit card when loading a stored conversation", async () => {
    const { fetchAiConversations, fetchAiConversationMessages } = await import("../../src/api/ai/history.js");
    const { fetchAiMemory } = await import("../../src/api/ai/memory.js");
    const AiChatView = (await import("../../src/views/ai/AiChatView.vue")).default;

    const auditedCase = {
      id: 808,
      status: "audit_passed",
      waste_type_predicted: "power bank",
      expected_carbon_points: 5,
      latest_audit_attempt_no: 2,
      audit_attempts: [
        {
          id: 91,
          attempt_no: 1,
          audit_result: "unclear",
          audit_reason: "The bin type is not clear enough.",
          audit_image_url: "/api/uploads/recycling-audit/attempt-1.jpg",
        },
        {
          id: 92,
          attempt_no: 2,
          audit_result: "passed",
          audit_reason: "The item is shown at the correct collection point.",
          audit_image_url: "/api/uploads/recycling-audit/attempt-2.jpg",
        },
      ],
    };

    fetchAiConversations.mockResolvedValue({
      items: [
        {
          id: 18,
          title: "Audit history chat",
          status: "completed",
          current_pending_action: "none",
          session_context_json: null,
        },
      ],
      total: 1,
      page: 1,
      per_page: 50,
    });
    fetchAiConversationMessages.mockResolvedValue({
      conversation: {
        id: 18,
        title: "Audit history chat",
        status: "completed",
        current_pending_action: "none",
        session_context_json: null,
      },
      items: [
        {
          id: 61,
          role: "assistant",
          message_type: "tool_result",
          content_text: "Nearby e-waste point summary",
          content_json: {
            recycling_case_id: 808,
            nearby_locations: [{ name: "E-waste point", lat: 1, lng: 2 }],
          },
          related_analysis_id: null,
          sequence_no: 1,
          recycling_case: auditedCase,
        },
      ],
      total: 1,
      pending_recycling_case: null,
    });
    fetchAiMemory.mockResolvedValue({
      summary: {},
      items: [],
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

    expect(wrapper.text()).toContain("Completion audit for 808 attempts:2");
  });

  it("keeps the pending recycle case audit card available when resuming nearby search from awaiting location", async () => {
    const { fetchAiConversations, fetchAiConversationMessages } = await import("../../src/api/ai/history.js");
    const { fetchAiMemory } = await import("../../src/api/ai/memory.js");
    const { resumeRecyclingAnalysis, submitLocationContext } = await import("../../src/api/ai/chat.js");
    const AiChatView = (await import("../../src/views/ai/AiChatView.vue")).default;

    const pendingCase = {
      id: 222,
      status: "pending_audit",
      waste_type_predicted: "plastic bottle",
      expected_carbon_points: 1,
      latest_audit_attempt_no: 0,
    };

    fetchAiConversations.mockResolvedValue({
      items: [
        {
          id: 5,
          title: "Awaiting location chat",
          status: "awaiting_location",
          current_pending_action: "location_permission",
          session_context_json: JSON.stringify({ session_id: "session-222" }),
        },
      ],
      total: 1,
      page: 1,
      per_page: 50,
    });

    fetchAiConversationMessages.mockResolvedValue({
      conversation: {
        id: 5,
        title: "Awaiting location chat",
        status: "awaiting_location",
        current_pending_action: "location_permission",
        session_context_json: JSON.stringify({ session_id: "session-222" }),
      },
      items: [
        {
          id: 20,
          role: "assistant",
          message_type: "text",
          content_text: "Share your location to continue.",
          content_json: {},
          related_analysis_id: null,
          sequence_no: 1,
          recycling_case: null,
        },
      ],
      total: 1,
      pending_recycling_case: pendingCase,
    });
    fetchAiMemory.mockResolvedValue({
      summary: {},
      items: [],
    });
    submitLocationContext.mockResolvedValue({ ok: true });
    resumeRecyclingAnalysis.mockImplementation(async (payload, handlers) => {
      expect(payload.session_id).toBe("session-222");
      handlers.onNearbyResults({
        data: {
          recycling_case_id: 222,
          nearby_locations: [{ name: "Bottle point", lat: 30.1, lng: 104.1 }],
        },
      });
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

    expect(wrapper.text()).toContain("Nearby Recycling Search");

    await wrapper.findAll(".chat-card__button").find((button) => button.text() === "Enter area manually").trigger("click");
    await flushPromises();

    await wrapper.find(".chat-card__input").setValue("Chengdu");
    await wrapper.findAll(".chat-card__button").find((button) => button.text() === "Continue with this area").trigger("click");

    await flushPromises();
    await flushPromises();

    expect(submitLocationContext).toHaveBeenCalledWith({
      session_id: "session-222",
      conversation_id: 5,
      permission_state: "granted",
      manual_area: "Chengdu",
    });
    expect(resumeRecyclingAnalysis).toHaveBeenCalledTimes(1);
    expect(wrapper.text()).toContain("Completion audit for 222");
  });

  it("falls back to the pending recycle case id when streamed nearby results omit recycling_case_id", async () => {
    const { fetchAiConversations, fetchAiConversationMessages } = await import("../../src/api/ai/history.js");
    const { fetchAiMemory } = await import("../../src/api/ai/memory.js");
    const { resumeRecyclingAnalysis, submitLocationContext } = await import("../../src/api/ai/chat.js");
    const AiChatView = (await import("../../src/views/ai/AiChatView.vue")).default;

    const pendingCase = {
      id: 333,
      status: "pending_audit",
      waste_type_predicted: "plastic bottle",
      expected_carbon_points: 1,
      latest_audit_attempt_no: 0,
    };

    fetchAiConversations.mockResolvedValue({
      items: [
        {
          id: 7,
          title: "Missing case id chat",
          status: "awaiting_location",
          current_pending_action: "location_permission",
          session_context_json: JSON.stringify({ session_id: "session-333" }),
        },
      ],
      total: 1,
      page: 1,
      per_page: 50,
    });

    fetchAiConversationMessages.mockResolvedValue({
      conversation: {
        id: 7,
        title: "Missing case id chat",
        status: "awaiting_location",
        current_pending_action: "location_permission",
        session_context_json: JSON.stringify({ session_id: "session-333" }),
      },
      items: [],
      total: 0,
      pending_recycling_case: pendingCase,
    });
    fetchAiMemory.mockResolvedValue({
      summary: {},
      items: [],
    });
    submitLocationContext.mockResolvedValue({ ok: true });
    resumeRecyclingAnalysis.mockImplementation(async (_payload, handlers) => {
      handlers.onNearbyResults({
        data: {
          waste_type: "plastic bottle",
          nearby_locations: [{ name: "Bottle point", lat: 30.1, lng: 104.1 }],
        },
      });
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

    await wrapper.findAll(".chat-card__button").find((button) => button.text() === "Enter area manually").trigger("click");
    await flushPromises();

    await wrapper.find(".chat-card__input").setValue("Chengdu");
    await wrapper.findAll(".chat-card__button").find((button) => button.text() === "Continue with this area").trigger("click");

    await flushPromises();
    await flushPromises();

    expect(wrapper.text()).toContain("Completion audit for 333");
  });

  it("shows a skipped-nearby result card and keeps the completion audit last when the user skips location search", async () => {
    const { fetchAiConversations, fetchAiConversationMessages } = await import("../../src/api/ai/history.js");
    const { fetchAiMemory } = await import("../../src/api/ai/memory.js");
    const { resumeRecyclingAnalysis, submitLocationContext } = await import("../../src/api/ai/chat.js");
    const AiChatView = (await import("../../src/views/ai/AiChatView.vue")).default;

    const pendingCase = {
      id: 444,
      status: "pending_audit",
      waste_type_predicted: "plastic bottle",
      expected_carbon_points: 2,
      latest_audit_attempt_no: 0,
    };

    fetchAiConversations.mockResolvedValue({
      items: [
        {
          id: 8,
          title: "Skipped nearby chat",
          status: "awaiting_location",
          current_pending_action: "location_permission",
          session_context_json: JSON.stringify({ session_id: "session-444" }),
        },
      ],
      total: 1,
      page: 1,
      per_page: 50,
    });

    fetchAiConversationMessages.mockResolvedValue({
      conversation: {
        id: 8,
        title: "Skipped nearby chat",
        status: "awaiting_location",
        current_pending_action: "location_permission",
        session_context_json: JSON.stringify({ session_id: "session-444" }),
      },
      items: [
        {
          id: 30,
          role: "assistant",
          message_type: "text",
          content_text: "Choose whether to search nearby points.",
          content_json: {},
          related_analysis_id: null,
          sequence_no: 1,
          recycling_case: null,
        },
      ],
      total: 1,
      pending_recycling_case: pendingCase,
    });
    fetchAiMemory.mockResolvedValue({
      summary: {},
      items: [],
    });
    submitLocationContext.mockResolvedValue({ ok: true });
    resumeRecyclingAnalysis.mockImplementation(async (_payload, handlers) => {
      handlers.onStageStart({ stage: "completed" });
      handlers.onDelta("Nearby recycling search was skipped at your request.");
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

    await wrapper.findAll(".chat-card__button").find((button) => button.text() === "Skip nearby search").trigger("click");
    await flushPromises();
    await flushPromises();

    expect(submitLocationContext).toHaveBeenCalledWith({
      session_id: "session-444",
      conversation_id: 8,
      skip_nearby_search: true,
      permission_state: "denied",
    });
    expect(wrapper.text()).toContain("Nearby recycling search was skipped at your request. You can continue with the completion audit below.");
    expect(wrapper.text()).toContain("Completion audit for 444");
    expect(wrapper.text().indexOf("Nearby recycling search was skipped at your request. You can continue with the completion audit below.")).toBeLessThan(
      wrapper.text().indexOf("Completion audit for 444"),
    );
  });

  it("deletes a persisted chat from the sidebar and switches the active session", async () => {
    const { fetchAiConversations, fetchAiConversationMessages, deleteAiConversation } = await import("../../src/api/ai/history.js");
    const { fetchAiMemory } = await import("../../src/api/ai/memory.js");
    const AiChatView = (await import("../../src/views/ai/AiChatView.vue")).default;

    fetchAiConversations.mockResolvedValue({
      items: [
        {
          id: 12,
          title: "Newest chat",
          status: "completed",
          current_pending_action: "none",
          session_context_json: null,
        },
        {
          id: 11,
          title: "Older chat",
          status: "completed",
          current_pending_action: "none",
          session_context_json: null,
        },
      ],
      total: 2,
      page: 1,
      per_page: 50,
    });
    fetchAiConversationMessages.mockImplementation(async (conversationId) => ({
      conversation: {
        id: conversationId,
        title: conversationId === 12 ? "Newest chat" : "Older chat",
        status: "completed",
        current_pending_action: "none",
        session_context_json: null,
      },
      items: [
        {
          id: conversationId * 10,
          role: "assistant",
          message_type: "text",
          content_text: conversationId === 12 ? "Newest body" : "Older body",
          content_json: {},
          related_analysis_id: null,
          sequence_no: 1,
          recycling_case: null,
        },
      ],
      total: 1,
      pending_recycling_case: null,
    }));
    deleteAiConversation.mockResolvedValue({ deleted_conversation_id: 12 });
    fetchAiMemory.mockResolvedValue({
      summary: {},
      items: [],
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

    expect(wrapper.find('[data-ai-history-item="conversation-12"]').classes()).toContain("chat-sidebar__entry--active");

    await wrapper.find('[data-ai-history-delete="conversation-12"]').trigger("click");
    await flushPromises();
    await flushPromises();

    expect(window.confirm).toHaveBeenCalled();
    expect(deleteAiConversation).toHaveBeenCalledWith(12);
    expect(wrapper.find('[data-ai-history-item="conversation-12"]').exists()).toBe(false);
    expect(wrapper.find('[data-ai-history-item="conversation-11"]').classes()).toContain("chat-sidebar__entry--active");
    expect(wrapper.text()).toContain("Older body");
  });

  it("renders a low-emphasis memory update hint after a streamed chat reply", async () => {
    const { fetchAiConversations, fetchAiConversationMessages } = await import("../../src/api/ai/history.js");
    const { fetchAiMemory } = await import("../../src/api/ai/memory.js");
    const { streamAiChat } = await import("../../src/api/ai/chat.js");
    const AiChatView = (await import("../../src/views/ai/AiChatView.vue")).default;

    let hasPersistedConversation = false;

    fetchAiConversations.mockImplementation(async () => ({
      items: hasPersistedConversation
        ? [
            {
              id: 88,
              title: "Memory update chat",
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
    fetchAiConversationMessages.mockResolvedValue({
      conversation: {
        id: 88,
        title: "Memory update chat",
        status: "active",
        current_pending_action: "none",
        session_context_json: null,
      },
      items: [],
      total: 0,
      pending_recycling_case: null,
    });
    fetchAiMemory.mockResolvedValue({
      summary: {},
      items: [],
    });
    streamAiChat.mockImplementation(async (payload, handlers) => {
      expect(payload.message).toBe("Please answer concisely from now on.");
      handlers.onMeta({
        conversation_id: 88,
        conversation_title: "Memory update chat",
        memory_updates: [
          {
            id: 1,
            memory_type: "response_style",
            memory_key: "response_style",
          },
        ],
      });
      hasPersistedConversation = true;
      handlers.onDelta("Noted.");
      handlers.onDone({
        stream_stage: "completed",
        trace: {
          schema_version: "graph-agent-trace-v1",
          router: { intent: "general_chat", confidence: 0.9 },
          retrieval: {
            forum: { enabled: false, citations: [] },
            neo4j: { enabled: false, paths: [] },
          },
          guardrails: { fallback_applied: false, reasons: [] },
          prompt_versions: {
            router: "router-v1",
            general_chat_answer: "general-chat-answer-v1",
          },
        },
      });
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

    await wrapper.find("textarea").setValue("Please answer concisely from now on.");
    await wrapper.find("form").trigger("submit.prevent");

    await flushPromises();
    await flushPromises();
    await flushPromises();
    await waitForStreaming();

    expect(streamAiChat).toHaveBeenCalledTimes(1);
    expect(wrapper.text()).toContain("Memory updated: response style");
    expect(wrapper.text()).toContain("Agent Trace");
    expect(wrapper.text()).toContain("general-chat-answer-v1");
    expect(wrapper.find(".chat-message__memory-hint").exists()).toBe(true);
  });

  it("sends a chat request when only an image is selected", async () => {
    const { fetchAiConversations, fetchAiConversationMessages } = await import("../../src/api/ai/history.js");
    const { fetchAiMemory } = await import("../../src/api/ai/memory.js");
    const { streamAiChat } = await import("../../src/api/ai/chat.js");
    const { readCompressedImageDataUrl } = await import("../../src/utils/imageDataUrl.js");
    const AiChatView = (await import("../../src/views/ai/AiChatView.vue")).default;

    const imageDataUrl =
      "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO7Z0vcAAAAASUVORK5CYII=";

    fetchAiConversations.mockResolvedValue({
      items: [],
      total: 0,
      page: 1,
      per_page: 50,
    });
    fetchAiConversationMessages.mockResolvedValue({
      conversation: null,
      items: [],
      total: 0,
      pending_recycling_case: null,
    });
    fetchAiMemory.mockResolvedValue({
      summary: {},
      items: [],
    });
    readCompressedImageDataUrl.mockResolvedValue(imageDataUrl);
    streamAiChat.mockImplementation(async (payload, handlers) => {
      expect(payload.message).toBe("");
      expect(payload.image).toBe(imageDataUrl);
      handlers.onMeta({
        conversation_id: 92,
        conversation_title: "Image discussion",
      });
      handlers.onDelta("I can inspect this image.");
      handlers.onDone({
        stream_stage: "completed",
      });
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

    const fileInput = wrapper.find('input[type="file"]');
    Object.defineProperty(fileInput.element, "files", {
      value: [new File(["image"], "photo.png", { type: "image/png" })],
      configurable: true,
    });
    await fileInput.trigger("change");
    await flushPromises();

    expect(wrapper.find(".chat-input__send").attributes("disabled")).toBeUndefined();

    await wrapper.find("form").trigger("submit.prevent");
    await flushPromises();
    await waitForStreaming();

    expect(streamAiChat).toHaveBeenCalledTimes(1);
  });

  it("blocks signed-out users from sending chat messages", async () => {
    globalThis.__CARBONSNAP_TEST_IS_LOGGED_IN__ = false;
    globalThis.__CARBONSNAP_TEST_USER__ = null;

    const { fetchAiConversations, fetchAiConversationMessages } = await import("../../src/api/ai/history.js");
    const { fetchAiMemory } = await import("../../src/api/ai/memory.js");
    const { streamAiChat } = await import("../../src/api/ai/chat.js");
    const AiChatView = (await import("../../src/views/ai/AiChatView.vue")).default;

    fetchAiConversations.mockResolvedValue({
      items: [],
      total: 0,
      page: 1,
      per_page: 50,
    });
    fetchAiConversationMessages.mockResolvedValue({
      conversation: null,
      items: [],
      total: 0,
      pending_recycling_case: null,
    });
    fetchAiMemory.mockResolvedValue({
      summary: {},
      items: [],
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

    expect(fetchAiConversations).not.toHaveBeenCalled();
    expect(fetchAiMemory).not.toHaveBeenCalled();
    expect(wrapper.text()).toContain("Log in to send messages to CarbonSnap AI.");
    expect(wrapper.find("textarea").attributes("disabled")).toBeDefined();
    expect(wrapper.find(".chat-input__send").attributes("disabled")).toBeDefined();

    await wrapper.find("form").trigger("submit.prevent");
    await flushPromises();

    expect(streamAiChat).not.toHaveBeenCalled();
  });

  it("replays persisted memory update hints when a stored conversation is reloaded", async () => {
    const { fetchAiConversations, fetchAiConversationMessages } = await import("../../src/api/ai/history.js");
    const { fetchAiMemory } = await import("../../src/api/ai/memory.js");
    const AiChatView = (await import("../../src/views/ai/AiChatView.vue")).default;

    fetchAiConversations.mockResolvedValue({
      items: [
        {
          id: 91,
          title: "Stored memory update chat",
          status: "completed",
          current_pending_action: "none",
          session_context_json: null,
        },
      ],
      total: 1,
      page: 1,
      per_page: 50,
    });
    fetchAiConversationMessages.mockResolvedValue({
      conversation: {
        id: 91,
        title: "Stored memory update chat",
        status: "completed",
        current_pending_action: "none",
        session_context_json: null,
      },
      items: [
        {
          id: 301,
          role: "assistant",
          message_type: "text",
          content_text: "Understood! I have made a note to prioritize nearby drop-off suggestions for our conversation going forward.",
          content_json: {
            memory_updates: [
              {
                id: 7,
                memory_type: "recycling_preference",
                memory_key: "prefer_nearby_options",
                value: true,
              },
            ],
          },
          related_analysis_id: null,
          sequence_no: 1,
          recycling_case: null,
        },
      ],
      total: 1,
      pending_recycling_case: null,
    });
    fetchAiMemory.mockResolvedValue({
      summary: {},
      items: [],
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

    expect(wrapper.text()).toContain("Memory updated: nearby options");
    expect(wrapper.find(".chat-message__memory-hint").exists()).toBe(true);
  });

  it("renders structured forum references as clickable post links", async () => {
    const { fetchAiConversations, fetchAiConversationMessages } = await import("../../src/api/ai/history.js");
    const { fetchAiMemory } = await import("../../src/api/ai/memory.js");
    const AiChatView = (await import("../../src/views/ai/AiChatView.vue")).default;

    fetchAiConversations.mockResolvedValue({
      items: [
        {
          id: 91,
          title: "Forum citation chat",
          status: "completed",
          current_pending_action: "none",
          session_context_json: null,
        },
      ],
      total: 1,
      page: 1,
      per_page: 50,
    });
    fetchAiConversationMessages.mockResolvedValue({
      conversation: {
        id: 91,
        title: "Forum citation chat",
        status: "completed",
        current_pending_action: "none",
        session_context_json: null,
      },
      items: [
        {
          id: 1,
          role: "assistant",
          message_type: "text",
          content_text: "You can follow the forum suggestion below.",
          content_json: {
            forum_references: [
              {
                reference_id: "forum-post-12",
                post_id: 12,
                title: "Bottle Sorting Guide",
                url: "/forum/posts/12",
              },
            ],
          },
          related_analysis_id: null,
          sequence_no: 1,
          recycling_case: null,
        },
      ],
      total: 1,
      pending_recycling_case: null,
    });
    fetchAiMemory.mockResolvedValue({
      summary: {},
      items: [],
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

    const sourceLink = wrapper.find(".chat-message__sources-link");
    expect(wrapper.text()).toContain("Referenced forum posts");
    expect(sourceLink.text()).toBe("Bottle Sorting Guide");
    expect(sourceLink.attributes("href")).toBe("/forum/posts/12");
  });

  it("renders a persisted agent trace panel for assistant messages", async () => {
    const { fetchAiConversations, fetchAiConversationMessages } = await import("../../src/api/ai/history.js");
    const { fetchAiMemory } = await import("../../src/api/ai/memory.js");
    const AiChatView = (await import("../../src/views/ai/AiChatView.vue")).default;

    fetchAiConversations.mockResolvedValue({
      items: [
        {
          id: 92,
          title: "Trace chat",
          status: "completed",
          current_pending_action: "none",
          session_context_json: null,
        },
      ],
      total: 1,
      page: 1,
      per_page: 50,
    });
    fetchAiConversationMessages.mockResolvedValue({
      conversation: {
        id: 92,
        title: "Trace chat",
        status: "completed",
        current_pending_action: "none",
        session_context_json: null,
      },
      items: [
        {
          id: 401,
          role: "assistant",
          message_type: "text",
          content_text: "Traceable answer.",
          content_json: {
            trace: {
              schema_version: "graph-agent-trace-v1",
              router: { intent: "general_chat", confidence: 0.82 },
              retrieval: {
                forum: { enabled: true, citations: [{ post_id: 12 }] },
                neo4j: { enabled: false, paths: [] },
              },
              guardrails: { fallback_applied: false, reasons: [] },
              prompt_versions: {
                router: "router-v1",
                general_chat_answer: "general-chat-answer-v1",
              },
            },
          },
          trace: {
            schema_version: "graph-agent-trace-v1",
            router: { intent: "general_chat", confidence: 0.82 },
            retrieval: {
              forum: { enabled: true, citations: [{ post_id: 12 }] },
              neo4j: { enabled: false, paths: [] },
            },
            guardrails: { fallback_applied: false, reasons: [] },
            prompt_versions: {
              router: "router-v1",
              general_chat_answer: "general-chat-answer-v1",
            },
          },
          related_analysis_id: null,
          sequence_no: 1,
          recycling_case: null,
        },
      ],
      total: 1,
      pending_recycling_case: null,
    });
    fetchAiMemory.mockResolvedValue({
      summary: {},
      items: [],
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

    expect(wrapper.text()).toContain("Traceable answer.");
    expect(wrapper.text()).toContain("Agent Trace");
    expect(wrapper.text()).toContain("general_chat");
    expect(wrapper.text()).toContain("router-v1");
    expect(wrapper.text()).toContain("general-chat-answer-v1");
  });
});
