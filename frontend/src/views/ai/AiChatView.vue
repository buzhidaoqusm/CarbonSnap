<template>
  <HeaderOnlyLayout
    :is-authenticated="isAuthenticated"
    :avatar-url="avatarUrl"
    :avatar-alt="avatarAlt"
    :avatar-href="avatarHref"
    :user="user"
  >
    <div class="ai-chat-page">
      <aside class="chat-sidebar" :class="{ 'chat-sidebar--open': isSidebarOpen }" data-ai-history-list>
        <div class="chat-sidebar__top">
          <button class="chat-sidebar__new-button" type="button" @click="createNewChat">
            {{ t("ai.newChat") }}
          </button>
          <button
            v-if="isLoggedIn"
            class="chat-sidebar__memory-button"
            type="button"
            @click="toggleMemoryPanel"
          >
            {{ t("ai.memory") }}
          </button>
        </div>

        <ul class="chat-sidebar__list">
          <li
            v-for="chat in sidebarChats"
            :key="chat.id"
            class="chat-sidebar__entry"
            :class="{
              'chat-sidebar__entry--active': chat.id === activeChatId,
              'chat-sidebar__entry--deleting': deletingChatId === chat.id,
            }"
            :data-ai-history-item="chat.id"
          >
            <button
              class="chat-sidebar__item"
              type="button"
              :disabled="deletingChatId === chat.id"
              @click="selectChat(chat.id)"
            >
              <span class="chat-sidebar__item-title">{{ chat.title }}</span>
            </button>
            <button
              class="chat-sidebar__delete"
              type="button"
              :aria-label="t('ai.chatDeleteLabel', { title: chat.title || 'chat' })"
              :data-ai-history-delete="chat.id"
              :disabled="isDeleteDisabled(chat)"
              @click.stop="handleDeleteChat(chat)"
            >
              <span class="material-symbols-outlined" aria-hidden="true">delete</span>
            </button>
          </li>
        </ul>
      </aside>

      <section class="chat-main" data-ai-chat-canvas>
        <header class="chat-main__header">
          <button class="chat-main__menu-button" type="button" @click="toggleSidebar">
            {{ t("ai.chats") }}
          </button>
          <h1 class="chat-main__title">{{ activeChat.title || t("ai.assistant") }}</h1>
        </header>

        <div v-if="isMemoryPanelOpen && isLoggedIn" class="chat-main__memory-panel">
          <MemoryPanel
            :summary="aiMemorySummary"
            :items="aiMemoryItems"
            :loading="memoryLoading"
            :error="memoryError"
            @close="isMemoryPanelOpen = false"
            @delete="handleDeleteMemory"
          />
        </div>

        <div ref="messageContainerRef" class="chat-main__messages" @scroll="handleMessageScroll">
          <p v-if="latestAssistantText" class="chat-main__a11y-summary">{{ latestAssistantText }}</p>

          <section v-if="showWelcomeState" class="chat-welcome-state">
            <div class="chat-welcome-state__hero">
              <div class="chat-welcome-state__icon">AI</div>
              <h2 class="chat-welcome-state__title">{{ welcomeTitle }}</h2>
              <p class="chat-welcome-state__subtitle">
                {{ welcomeSubtitle }}
              </p>
            </div>

            <div class="chat-welcome-state__prompts">
              <button
                v-for="prompt in starterPrompts"
                :key="prompt.label"
                type="button"
                class="chat-welcome-state__prompt"
                @click="applyStarterPrompt(prompt.prompt)"
              >
                <span class="chat-welcome-state__prompt-label">{{ prompt.label }}</span>
                <span class="chat-welcome-state__prompt-copy">{{ prompt.prompt }}</span>
              </button>
            </div>

            <div class="chat-welcome-state__cards">
              <article class="chat-welcome-card">
                <p class="chat-welcome-card__eyebrow">{{ t("ai.whatYouCanDo") }}</p>
                <ul class="chat-welcome-card__list">
                  <li>{{ t("ai.whatYouCanDo1") }}</li>
                  <li>{{ t("ai.whatYouCanDo2") }}</li>
                  <li>{{ t("ai.whatYouCanDo3") }}</li>
                </ul>
              </article>

              <article class="chat-welcome-card">
                <p class="chat-welcome-card__eyebrow">{{ t("ai.recentHistory") }}</p>
                <div v-if="recentChatTitles.length > 0" class="chat-welcome-card__history">
                  <span
                    v-for="title in recentChatTitles"
                    :key="title"
                    class="chat-welcome-card__history-item"
                  >
                    {{ title }}
                  </span>
                </div>
                <p v-else class="chat-welcome-card__empty">
                  {{ t("ai.historyEmpty") }}
                </p>
              </article>
            </div>
          </section>

          <template v-for="message in activeChat.messages" :key="message.id">
            <div
              v-if="message.kind === 'chat'"
              class="chat-message"
              :class="{
                'chat-message--assistant': message.role === 'assistant',
                'chat-message--user': message.role === 'user',
              }"
            >
              <div class="chat-message__bubble">
                <img
                  v-if="message.imageUrl"
                  class="chat-message__image"
                  :src="message.imageUrl"
                  :alt="t('ai.uploadImageAlt')"
                />
                <div
                  v-if="message.role === 'assistant' && message.content"
                  class="chat-message__markdown"
                  v-html="renderAssistantMarkdown(message.content)"
                />
                <div
                  v-else-if="message.role === 'assistant' && shouldShowAssistantThinking(message)"
                  class="chat-message__thinking"
                  :aria-label="getAssistantThinkingTitle(message)"
                  aria-live="polite"
                >
                  <div class="chat-message__thinking-header">
                    <span class="chat-message__thinking-badge">AI Snap</span>
                    <span class="chat-message__thinking-stage">{{ getAssistantThinkingTitle(message) }}</span>
                  </div>
                  <p class="chat-message__thinking-copy">
                    {{ getAssistantThinkingCopy(message) }}
                  </p>
                  <div class="chat-message__thinking-dots" aria-hidden="true">
                    <span />
                    <span />
                    <span />
                  </div>
                </div>
                <p v-else-if="message.content" class="chat-message__text">{{ message.content }}</p>
                <p v-if="message.role === 'assistant' && message.memoryUpdates?.length" class="chat-message__memory-hint">
                  {{ formatMemoryUpdateHint(message.memoryUpdates) }}
                </p>
                <AgentTracePanel
                  v-if="message.role === 'assistant' && message.trace"
                  :trace="message.trace"
                />
                <div
                  v-if="message.role === 'assistant' && message.forumReferences?.length"
                  class="chat-message__sources"
                >
                  <p class="chat-message__sources-title">{{ t("ai.referencedForumPosts") }}</p>
                  <ul class="chat-message__sources-list">
                    <li v-for="reference in message.forumReferences" :key="reference.reference_id || reference.url">
                      <a :href="reference.url" class="chat-message__sources-link">
                        {{ reference.title || reference.url }}
                      </a>
                    </li>
                  </ul>
                </div>
              </div>
            </div>

            <div v-else-if="message.kind === 'location_prompt'" class="chat-card chat-card--location">
              <div class="chat-card__header">
                <h2 class="chat-card__title">{{ t("ai.locationTitle") }}</h2>
                <p class="chat-card__subtitle">
                  {{ t("ai.nearbyStageReady") }}
                </p>
              </div>

              <div v-if="message.resolved" class="chat-card__status">
                {{ message.resolutionText }}
              </div>

              <div v-else class="chat-card__actions">
                <button
                  v-if="canUseBrowserLocation"
                  class="chat-card__button chat-card__button--primary"
                  type="button"
                  :disabled="message.actionInProgress"
                  @click="handleAllowBrowserLocation(message)"
                >
                  {{ t("ai.locationAllow") }}
                </button>
                <button
                  class="chat-card__button"
                  type="button"
                  :disabled="message.actionInProgress"
                  @click="message.showManualArea = !message.showManualArea"
                >
                  {{ t("ai.locationEnterManual") }}
                </button>
                <button
                  class="chat-card__button chat-card__button--ghost"
                  type="button"
                  :disabled="message.actionInProgress"
                  @click="handleSkipNearbySearch(message)"
                >
                  {{ t("ai.locationSkip") }}
                </button>
              </div>

              <div v-if="message.showManualArea && !message.resolved" class="chat-card__manual">
                <input
                  v-model="message.manualAreaInput"
                  class="chat-card__input"
                  type="text"
                  :placeholder="t('ai.locationManualPlaceholder')"
                  :disabled="message.actionInProgress"
                />
                <button
                  class="chat-card__button chat-card__button--primary"
                  type="button"
                  :disabled="message.actionInProgress || !message.manualAreaInput.trim()"
                  @click="handleManualAreaSubmit(message)"
                >
                  {{ t("ai.continueArea") }}
                </button>
              </div>

              <p v-if="message.error" class="chat-card__error">{{ message.error }}</p>
            </div>

            <div v-else-if="message.kind === 'clarification_prompt'" class="chat-card chat-card--location">
              <div class="chat-card__header">
                <h2 class="chat-card__title">{{ t("ai.clarificationTitle") }}</h2>
                <p class="chat-card__subtitle chat-card__subtitle--clarification">{{ message.question }}</p>
              </div>

              <div v-if="message.resolved" class="chat-card__status">
                {{ message.resolutionText }}
              </div>

              <div v-else class="chat-card__actions">
                <button
                  v-for="(option, index) in message.options"
                  :key="`${option.label || 'option'}-${index}`"
                  class="chat-card__button"
                  type="button"
                  :disabled="message.actionInProgress"
                  @click="handleClarificationOption(message, option)"
                >
                  {{ option.label }}
                </button>
              </div>

              <p v-if="message.error" class="chat-card__error">{{ message.error }}</p>
            </div>

            <div v-else-if="message.kind === 'nearby_results'" class="chat-card chat-card--results">
              <div class="chat-card__header">
                <h2 class="chat-card__title">{{ t("ai.nearbyTitle") }}</h2>
                <p class="chat-card__subtitle">
                  {{ getNearbyResultsSubtitle(message) }}
                </p>
              </div>

              <div v-if="message.locations.length > 0" class="chat-card__map">
                <NearbyMapCard
                  :locations="message.locations"
                  @ready="handleNearbyMapReady(message.id)"
                />
              </div>
            </div>

            <div v-else-if="message.kind === 'completion_audit'" class="chat-composer-slot">
              <CompletionAuditComposer
                :key="message.id"
                :case-data="message.caseData || null"
                :busy="isAuditStreaming"
                :error="message.error || ''"
                :feedback="message.feedback || ''"
                :submitted-image-url="message.imageUrl || ''"
                :attempts="message.attempts || []"
                :locked="Boolean(message.locked)"
                @submit="submitCompletionAudit({ ...$event, caseData: message.caseData })"
                @attempt-view-change="handleAuditAttemptViewChange($event)"
              />
            </div>
          </template>

          <p v-if="streamStatusText" class="chat-main__streaming">{{ streamStatusText }}</p>
          <p v-if="streamError" class="chat-main__error">{{ streamError }}</p>
          <p v-if="historyError" class="chat-main__error">{{ historyError }}</p>
        </div>

        <form class="chat-input" @submit.prevent="sendMessage">
          <p v-if="!isLoggedIn" class="chat-input__auth-required">
            {{ t("ai.loginRequired") }}
            <a href="/login">{{ t("auth.signIn") }}</a>
          </p>
          <div v-if="selectedImageDataUrl" class="chat-input__preview">
            <img class="chat-input__preview-image" :src="selectedImageDataUrl" :alt="t('ai.uploadPreviewAlt')" />
            <div class="chat-input__preview-meta">
              <span class="chat-input__preview-name">{{ selectedImageName }}</span>
              <button class="chat-input__remove-image" type="button" @click="clearSelectedImage">
                {{ t("ai.remove") }}
              </button>
            </div>
          </div>

          <div class="chat-input__row">
            <input
              ref="fileInputRef"
              class="chat-input__file"
              type="file"
              accept="image/*"
              :disabled="!isLoggedIn"
              @change="handleImageSelect"
            />
            <button class="chat-input__attach" type="button" :disabled="!isLoggedIn || isStreaming" @click="openFilePicker">
              {{ t("ai.uploadImage") }}
            </button>

            <textarea
              ref="composerTextareaRef"
              v-model="draftMessage"
              class="chat-input__textarea"
              rows="1"
              :placeholder="chatInputPlaceholder"
              :disabled="!isLoggedIn || isStreaming"
              @paste="handleComposerPaste"
              @keydown.enter.exact.prevent="sendMessage"
            />

            <button class="chat-input__send" type="submit" :disabled="isSendDisabled">
              {{ t("ai.send") }}
            </button>
          </div>
        </form>
      </section>
    </div>
  </HeaderOnlyLayout>
</template>

<script setup>
import { computed, nextTick, onMounted, ref, watch } from "vue";
import DOMPurify from "dompurify";
import MarkdownIt from "markdown-it";

import {
  resumeRecyclingAnalysis,
  streamRecyclingAudit,
  streamAiChat,
  submitLocationContext,
} from "../../api/ai/chat";
import {
  deleteAiConversation,
  fetchAiConversationMessages,
  fetchAiConversations,
} from "../../api/ai/history";
import { deleteAiMemoryItem, fetchAiMemory } from "../../api/ai/memory.js";
import AgentTracePanel from "../../components/ai/AgentTracePanel.vue";
import CompletionAuditComposer from "../../components/ai/CompletionAuditComposer.vue";
import MemoryPanel from "../../components/ai/MemoryPanel.vue";
import NearbyMapCard from "../../components/ai/NearbyMapCard.vue";
import { useAuth } from "../../composables/useAuth.js";
import HeaderOnlyLayout from "../../layouts/HeaderOnlyLayout.vue";
import { readCompressedImageDataUrl } from "../../utils/imageDataUrl.js";
import { useI18n } from "../../i18n/index.js";

const markdownRenderer = new MarkdownIt({
  html: false,
  linkify: true,
  breaks: true,
});

const { user, isLoggedIn, updateUser } = useAuth();
const { isChinese, t } = useI18n();

const LOCATION_OPTIONS = [
  { key: "allow_browser_location", labelKey: "ai.locationAllow" },
  { key: "enter_manual_area", labelKey: "ai.locationEnterManual" },
  { key: "skip_nearby_search", labelKey: "ai.locationSkip" },
];
const ASSISTANT_DELTA_DELAY_MS = 4;
const ASSISTANT_DELTA_LARGE_CHUNK_SIZE = 12;
const ASSISTANT_DELTA_SMALL_CHUNK_SIZE = 4;
const CLARIFICATION_TYPING_DELAY_MS = 1;
const CLARIFICATION_TYPING_CHUNK_SIZE = 1000;

function isLocalBrowserHost(hostname) {
  const normalized = String(hostname || "").trim().toLowerCase().replace(/^\[|\]$/g, "");
  return normalized === "localhost" || normalized === "127.0.0.1" || normalized === "::1";
}

function canUseBrowserGeolocation() {
  if (typeof window === "undefined") {
    return false;
  }
  return window.location.protocol === "https:" || isLocalBrowserHost(window.location.hostname);
}

const canUseBrowserLocation = computed(canUseBrowserGeolocation);

function getApiBaseUrl() {
  const configuredBase = import.meta.env.VITE_API_BASE_URL;
  const runtimeBase =
    configuredBase !== undefined
      ? configuredBase
      : import.meta.env.DEV
        ? "http://127.0.0.1:5000"
        : "";
  return runtimeBase.replace(/\/$/, "");
}

function resolveBackendUrl(url) {
  const value = String(url || "").trim();
  if (!value) {
    return "";
  }
  if (value.startsWith("data:") || /^https?:\/\//i.test(value)) {
    return value;
  }
  const baseUrl = getApiBaseUrl();
  if (!baseUrl) {
    return value;
  }
  return `${baseUrl}${value.startsWith("/") ? "" : "/"}${value}`;
}

function parseMaybeJson(value) {
  if (!value) {
    return null;
  }
  if (typeof value === "object") {
    return value;
  }
  if (typeof value !== "string") {
    return null;
  }
  try {
    return JSON.parse(value);
  } catch {
    return null;
  }
}

function generateId() {
  const cryptoApi = globalThis.crypto;
  if (typeof cryptoApi?.randomUUID === "function") {
    return cryptoApi.randomUUID();
  }

  if (typeof cryptoApi?.getRandomValues === "function") {
    const bytes = cryptoApi.getRandomValues(new Uint8Array(16));
    bytes[6] = (bytes[6] & 0x0f) | 0x40;
    bytes[8] = (bytes[8] & 0x3f) | 0x80;

    const hex = Array.from(bytes, (value) => value.toString(16).padStart(2, "0"));
    return [
      hex.slice(0, 4).join(""),
      hex.slice(4, 6).join(""),
      hex.slice(6, 8).join(""),
      hex.slice(8, 10).join(""),
      hex.slice(10, 16).join(""),
    ].join("-");
  }

  return `fallback-${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

function createChat() {
  return {
    id: generateId(),
    title: t("ai.newChatTitle"),
    sessionId: null,
    backendId: null,
    status: "active",
    currentPendingAction: "none",
    sessionContext: null,
    pendingRecyclingCase: null,
    completionAuditCards: [],
    auditViewContext: null,
    loaded: true,
    loading: false,
    messages: [],
  };
}

function ensureAtLeastOneChat() {
  if (chats.value.length > 0) {
    return;
  }
  const fallback = createChat();
  chats.value = [fallback];
  activeChatId.value = fallback.id;
}

function createUserMessage(content, imageUrl = "") {
  return {
    id: generateId(),
    kind: "chat",
    role: "user",
    content,
    imageUrl,
  };
}

function createAssistantMessage(stage = "analysis") {
  return {
    id: generateId(),
    kind: "chat",
    role: "assistant",
    content: "",
    imageUrl: "",
    stage,
    memoryUpdates: [],
    forumReferences: [],
    trace: null,
  };
}

function createLocationPromptMessage(data) {
  return {
    id: generateId(),
    kind: "location_prompt",
    sessionId: data.sessionId || data.session_id || "",
    conversationId: data.conversationId || data.conversation_id || null,
    actionInProgress: false,
    error: "",
    manualAreaInput: "",
    options: (data.location_options || LOCATION_OPTIONS).map((option) => ({
      ...option,
      label: option.label || (option.labelKey ? t(option.labelKey) : ""),
    })),
    resolved: false,
    resolutionText: "",
    showManualArea: false,
  };
}

function createNearbyResultsMessage(payload, options = {}) {
  const locationState = payload.location_state || {};
  const permissionState = String(
    payload.permission_state || locationState.permission_state || "",
  ).toLowerCase();
  const locations = (payload.nearby_locations || []).map((location, index) => ({
    ...location,
    id: location.id || `${location.name || "location"}-${index}`,
    address: location.address || "Address unavailable",
    category: location.category || "Recycling point",
    distance_meters: Number(location.distance_meters || 0),
    lat: Number(location.lat),
    lng: Number(location.lng),
    osm_url: location.osm_url || location.osmUrl || "",
  }));

  return {
    id: generateId(),
    kind: "nearby_results",
    caseId: normalizeCaseId(
      payload.caseId ||
      payload.recycling_case_id ||
      payload.recyclingCaseId ||
      options.fallbackCaseId,
    ),
    mapError: payload.map_error || "",
    skipped: Boolean(payload.skip_nearby_search || locationState.skip_nearby_search),
    permissionDenied: permissionState === "denied",
    mapReady: locations.length === 0,
    suppressCompletionAudit: Boolean(payload.suppress_completion_audit),
    locations,
  };
}

function createAuditAssistantMessage(text, payload) {
  return {
    id: generateId(),
    kind: "chat",
    role: "assistant",
    content: text,
    imageUrl: "",
    stage: payload?.finalized ? "audit_finalize" : "audit",
    messageType: "audit_result",
  };
}

function createCompletionAuditMessage(card) {
  return {
    id: generateId(),
    kind: "completion_audit",
    caseId: normalizeCaseId(card?.caseData?.id),
    caseData: card?.caseData || null,
    feedback: card?.feedback || "",
    imageUrl: card?.imageUrl || "",
    attempts: normalizeAuditAttempts(card?.attempts || card?.caseData?.audit_attempts),
    locked: Boolean(card?.locked),
    error: card?.error || "",
  };
}

function createClarificationPromptMessage(data) {
  return {
    id: generateId(),
    kind: "clarification_prompt",
    question: data.question ?? "Could you clarify?",
    options: Array.isArray(data.options) ? data.options : [],
    actionInProgress: false,
    resolved: false,
    resolutionText: "",
    selectedOptionLabel: "",
    error: "",
  };
}

function updateClarificationPrompt(chat, promptId, patch) {
  const index = chat.messages.findIndex((message) => message.id === promptId);
  if (index === -1) {
    return null;
  }
  const updatedMessage = {
    ...chat.messages[index],
    ...patch,
  };
  chat.messages.splice(index, 1, updatedMessage);
  return updatedMessage;
}

async function appendClarificationQuestion(chat, promptId, question) {
  const text = String(question || "");
  if (!chat || !promptId || !text) {
    debugAiChat("clarification animation skipped", {
      hasChat: Boolean(chat),
      promptId,
      textLength: text.length,
    });
    return;
  }

  debugAiChat("clarification animation start", {
    promptId,
    textLength: text.length,
    text,
  });

  for (let index = 0; index < text.length; index += CLARIFICATION_TYPING_CHUNK_SIZE) {
    const updatedPrompt = updateClarificationPrompt(chat, promptId, {
      question: text.slice(0, index + CLARIFICATION_TYPING_CHUNK_SIZE),
    });
    await nextTick();
    await waitForFrame();
    await delay(CLARIFICATION_TYPING_DELAY_MS);
    debugAiChat("clarification animation step", {
      promptId,
      index: Math.min(index + CLARIFICATION_TYPING_CHUNK_SIZE, text.length),
      currentText: updatedPrompt?.question || "",
      messageIndex: chat.messages.findIndex((message) => message.id === promptId),
    });
  }

  scrollToBottom();
  debugAiChat("clarification animation complete", {
    promptId,
    finalText: text,
  });
}

function normalizeMemoryUpdates(memoryUpdates) {
  if (!Array.isArray(memoryUpdates)) {
    return [];
  }

  return memoryUpdates
    .map((item) => {
      if (!item || typeof item !== "object") {
        return null;
      }
      return {
        id: item.id ?? null,
        memory_type: String(item.memory_type || "").trim(),
        memory_key: String(item.memory_key || "").trim(),
      };
    })
    .filter((item) => item && (item.memory_type || item.memory_key));
}

function normalizeForumReferences(references) {
  if (!Array.isArray(references)) {
    return [];
  }

  return references
    .map((item, index) => {
      if (!item || typeof item !== "object") {
        return null;
      }

      const url = String(item.url || "").trim();
      const title = String(item.title || "").trim();
      if (!url || !title) {
        return null;
      }

      return {
        reference_id: String(item.reference_id || `forum-reference-${index}`).trim(),
        post_id: Number(item.post_id || 0) || null,
        title,
        url,
      };
    })
    .filter(Boolean);
}

function normalizeTrace(trace) {
  if (!trace || typeof trace !== "object" || Array.isArray(trace)) {
    return null;
  }
  return trace;
}

function normalizeCaseId(value) {
  const parsed = Number(value);
  return Number.isInteger(parsed) && parsed > 0 ? parsed : null;
}

function normalizeAuditAttempts(attempts) {
  if (!Array.isArray(attempts)) {
    return [];
  }

  const mergeAttempt = (existingAttempt, incomingAttempt) => ({
    ...existingAttempt,
    ...incomingAttempt,
    id:
      String(incomingAttempt?.id || "").startsWith("audit-attempt-") &&
      !String(existingAttempt?.id || "").startsWith("audit-attempt-")
        ? existingAttempt.id
        : (incomingAttempt?.id ?? existingAttempt?.id),
    audit_reason:
      String(incomingAttempt?.audit_reason || "").trim().length >=
      String(existingAttempt?.audit_reason || "").trim().length
        ? incomingAttempt.audit_reason
        : existingAttempt.audit_reason,
    audit_image_url: incomingAttempt?.audit_image_url || existingAttempt?.audit_image_url || "",
    auditor_confidence: Math.max(
      Number(existingAttempt?.auditor_confidence ?? 0) || 0,
      Number(incomingAttempt?.auditor_confidence ?? 0) || 0,
    ),
    created_at: incomingAttempt?.created_at || existingAttempt?.created_at || null,
  });

  const normalizedAttempts = attempts
    .map((attempt, index) => {
      if (!attempt || typeof attempt !== "object") {
        return null;
      }

      const attemptNo = Number(attempt.attempt_no || index + 1);
      return {
        id: attempt.id ?? `audit-attempt-${attemptNo}`,
        attempt_no: Number.isFinite(attemptNo) && attemptNo > 0 ? attemptNo : index + 1,
        audit_result: String(attempt.audit_result || "unclear").trim().toLowerCase(),
        audit_reason: String(attempt.audit_reason || "").trim(),
        audit_image_url: resolveBackendUrl(attempt.audit_image_url || attempt.image_url || ""),
        auditor_confidence: Number(attempt.auditor_confidence ?? 0) || 0,
        created_at: attempt.created_at || null,
      };
    })
    .filter(Boolean)
    .sort((left, right) => left.attempt_no - right.attempt_no);

  const uniqueAttempts = [];
  const seenKeys = new Map();
  for (const attempt of normalizedAttempts) {
    const hasAttemptNo = Number.isFinite(attempt.attempt_no) && attempt.attempt_no > 0;
    const attemptKey = hasAttemptNo
      ? `no:${attempt.attempt_no}`
      : attempt.id != null
        ? `id:${attempt.id}`
        : `img:${attempt.audit_image_url}`;
    const existingIndex = seenKeys.get(attemptKey);
    if (existingIndex != null) {
      uniqueAttempts[existingIndex] = mergeAttempt(uniqueAttempts[existingIndex], attempt);
      continue;
    }
    seenKeys.set(attemptKey, uniqueAttempts.length);
    uniqueAttempts.push(attempt);
  }
  return uniqueAttempts;
}

function cloneCaseData(caseData) {
  const caseId = normalizeCaseId(caseData?.id);
  if (!caseId) {
    return null;
  }

  return {
    ...caseData,
    id: caseId,
    audit_attempts: normalizeAuditAttempts(caseData?.audit_attempts),
  };
}

function formatMemoryUpdateLabel(update) {
  const memoryType = String(update?.memory_type || "").trim();
  const memoryKey = String(update?.memory_key || "").trim();

  if (memoryType === "response_style") {
    return t("ai.memoryResponseStyle");
  }
  if (memoryType === "recycling_preference") {
    if (memoryKey === "prefer_nearby_options") {
      return t("ai.memoryNearby");
    }
    if (memoryKey === "allow_manual_area_input") {
      return t("ai.memoryManualArea");
    }
    return memoryKey.replace(/_/g, " ") || t("ai.memoryPreference");
  }
  if (memoryType === "topic_interest") {
    return memoryKey.replace(/_/g, " ") || t("ai.memoryTopicInterest");
  }
  if (memoryType === "item_method_preference") {
    return memoryKey.replace(/_/g, " ") || "item method preference";
  }
  return memoryKey.replace(/_/g, " ") || memoryType.replace(/_/g, " ") || t("ai.memoryPreference");
}

function formatMemoryUpdateHint(memoryUpdates) {
  const labels = [...new Set(normalizeMemoryUpdates(memoryUpdates).map(formatMemoryUpdateLabel).filter(Boolean))];
  if (!labels.length) {
    return "";
  }
  return t("ai.memoryHint", { labels: labels.join(", ") });
}

function findLatestNearbyResultsMessage(chat, caseId) {
  return [...(chat?.messages || [])]
    .reverse()
    .find((message) => message.kind === "nearby_results" && message.caseId === caseId);
}

function getNearbyResultsSubtitle(message) {
  if (message?.locations?.length > 0) {
    return t("ai.nearbyFoundSubtitle");
  }
  if (message?.skipped) {
    return t("ai.nearbySkippedSubtitle");
  }
  if (message?.permissionDenied) {
    return t("ai.nearbyPermissionSubtitle");
  }
  return t("ai.nearbyDefaultSubtitle");
}

function shouldShowCompletionAuditCard(chat, card) {
  const caseId = normalizeCaseId(card?.caseData?.id);
  if (!caseId) {
    return false;
  }

  const latestNearbyMessage = findLatestNearbyResultsMessage(chat, caseId);
  return Boolean(latestNearbyMessage);
}

function handleNearbyMapReady(messageId) {
  const chat = activeChat.value;
  const message = (chat?.messages || []).find(
    (item) => item.kind === "nearby_results" && item.id === messageId,
  );

  if (!message || message.mapReady) {
    return;
  }

  message.mapReady = true;
  syncCompletionAuditMessages(chat);
  scrollToBottom();
}

function pushChatMessage(chat, message) {
  chat.messages.push(message);
  return chat.messages[chat.messages.length - 1];
}

function pushAssistantMessage(chat, stage = "analysis") {
  return pushChatMessage(chat, createAssistantMessage(stage));
}

function syncPendingRecyclingCaseCard(chat) {
  const pendingCase = cloneCaseData(chat?.pendingRecyclingCase);
  const caseId = normalizeCaseId(pendingCase?.id);
  if (!caseId) {
    return;
  }

  upsertCompletionAuditCardState(chat, {
    caseData: pendingCase,
    feedback: "",
    imageUrl: "",
    locked: String(pendingCase.status || "").toLowerCase() === "audit_passed",
    error: "",
  });
}

function upsertCompletionAuditCardState(chat, card) {
  const normalizedCard = {
    caseData: cloneCaseData(card?.caseData),
    feedback: card?.feedback || "",
    imageUrl: card?.imageUrl || "",
    attempts: normalizeAuditAttempts(card?.attempts || card?.caseData?.audit_attempts),
    locked: Boolean(card?.locked),
    error: card?.error || "",
  };
  const caseId = normalizeCaseId(normalizedCard.caseData?.id);
  if (!caseId) {
    return;
  }

  const existingIndex = chat.completionAuditCards.findIndex(
    (item) => normalizeCaseId(item?.caseData?.id) === caseId,
  );

  if (existingIndex === -1) {
    chat.completionAuditCards.push(normalizedCard);
    return;
  }

  chat.completionAuditCards.splice(existingIndex, 1, {
    ...chat.completionAuditCards[existingIndex],
    ...normalizedCard,
  });
}

function updateCompletionAuditCardError(chat, caseId, errorMessage = "") {
  const normalizedCaseId = normalizeCaseId(caseId);
  const existingCard = chat.completionAuditCards.find(
    (item) => normalizeCaseId(item?.caseData?.id) === normalizedCaseId,
  );
  if (!existingCard) {
    return;
  }

  upsertCompletionAuditCardState(chat, {
    ...existingCard,
    error: errorMessage,
  });
}

function normalizeAuditViewContext(payload) {
  const caseId = normalizeCaseId(payload?.caseId || payload?.case_id);
  const attemptNo = Number(payload?.attemptNo || payload?.attempt_no);
  if (!caseId || !Number.isFinite(attemptNo) || attemptNo <= 0) {
    return null;
  }

  return {
    caseId,
    attemptNo,
    auditResult: String(payload?.auditResult || payload?.audit_result || "unclear").trim().toLowerCase(),
  };
}

function handleAuditAttemptViewChange(payload) {
  const chat = activeChat.value;
  const normalized = normalizeAuditViewContext(payload);
  if (!chat || !normalized) {
    return;
  }
  chat.auditViewContext = normalized;
}

function syncCompletionAuditMessages(chat) {
  const existingAuditMessages = new Map(
    chat.messages
      .filter((message) => message.kind === "completion_audit")
      .map((message) => [normalizeCaseId(message.caseId || message.caseData?.id), message]),
  );
  const baseMessages = chat.messages.filter((message) => message.kind !== "completion_audit");
  const auditMessagesByAnchorId = new Map();

  for (const card of chat.completionAuditCards || []) {
    if (!shouldShowCompletionAuditCard(chat, card)) {
      continue;
    }

    const caseId = normalizeCaseId(card?.caseData?.id);
    if (!caseId) {
      continue;
    }

    const anchorMessage = findLatestNearbyResultsMessage({ messages: baseMessages }, caseId);
    if (!anchorMessage?.id) {
      continue;
    }

    const existingMessage = existingAuditMessages.get(caseId);
    const nextMessage = existingMessage
      ? {
          ...existingMessage,
          caseId,
          caseData: cloneCaseData(card.caseData),
          feedback: card.feedback || "",
          imageUrl: card.imageUrl || "",
          attempts: normalizeAuditAttempts(card.attempts || card.caseData?.audit_attempts),
          locked: Boolean(card.locked),
          error: card.error || "",
        }
      : createCompletionAuditMessage(card);

    const anchoredMessages = auditMessagesByAnchorId.get(anchorMessage.id) || [];
    anchoredMessages.push(nextMessage);
    auditMessagesByAnchorId.set(anchorMessage.id, anchoredMessages);
  }

  const nextMessages = [];
  for (const message of baseMessages) {
    nextMessages.push(message);
    const anchoredMessages = auditMessagesByAnchorId.get(message.id) || [];
    nextMessages.push(...anchoredMessages);
  }

  chat.messages = nextMessages;
}

const chats = ref([createChat()]);
const activeChatId = ref(chats.value[0].id);
const isSidebarOpen = ref(true);
const isStreaming = ref(false);
const isAuditStreaming = ref(false);
const streamError = ref("");
const historyError = ref("");
const auditError = ref("");
const historyLoading = ref(false);
const historyLoadingChatId = ref(null);
const deletingChatId = ref(null);
const isMemoryPanelOpen = ref(false);
const memoryLoading = ref(false);
const memoryError = ref("");
const aiMemorySummary = ref({});
const aiMemoryItems = ref([]);
let conversationListRequestSeq = 0;

const draftMessage = ref("");
const selectedImageDataUrl = ref("");
const selectedImageName = ref("");
const fileInputRef = ref(null);
const composerTextareaRef = ref(null);
const messageContainerRef = ref(null);
const shouldAutoScroll = ref(true);

const activeChat = computed(() => {
  const found = chats.value.find((chat) => chat.id === activeChatId.value);
  if (found) {
    return found;
  }
  return chats.value[0] || createChat();
});

const sidebarChats = computed(() =>
  chats.value.filter(
    (chat) => chat.backendId || chat.messages.length > 0 || chat.id === activeChatId.value,
  ),
);

const isAuthenticated = computed(() => isLoggedIn.value);
const avatarUrl = computed(() => resolveBackendUrl(user.value?.avatar_url || ""));
const avatarAlt = computed(() => (user.value?.username ? `${user.value.username} avatar` : "User avatar"));
const avatarHref = computed(() => (isLoggedIn.value ? "/profile" : "/login"));
const welcomeTitle = computed(() =>
  user.value?.username ? t("ai.goodMorning", { name: user.value.username }) : t("ai.welcomeTitle"),
);
const welcomeSubtitle = computed(() =>
  isLoggedIn.value
    ? t("ai.welcomeSignedIn")
    : t("ai.welcomeSignedOut"),
);
const chatInputPlaceholder = computed(() =>
  isLoggedIn.value ? t("ai.uploadPlaceholder") : t("ai.loginRequiredPlaceholder"),
);
const starterPrompts = computed(() => [
  { label: t("ai.promptImageAnalysis"), prompt: t("ai.promptImageAnalysisText") },
  { label: t("ai.promptNearby"), prompt: t("ai.promptNearbyText") },
  { label: t("ai.promptBinCheck"), prompt: t("ai.promptBinCheckText") },
]);
const recentChatTitles = computed(() =>
  sidebarChats.value
    .filter((chat) => chat.id !== activeChatId.value)
    .map((chat) => String(chat.title || "").trim())
    .filter(Boolean)
    .slice(0, 3),
);
const latestAssistantText = computed(() => {
  const latest = [...activeChat.value.messages]
    .reverse()
    .find((message) => message.kind === "chat" && message.role === "assistant" && message.content);
  return latest ? latest.content : "";
});
const showWelcomeState = computed(() => {
  const isBlockingHistoryLoad =
    historyLoadingChatId.value === activeChat.value.id &&
    !activeChat.value.loaded &&
    activeChat.value.messages.length === 0;
  return !isBlockingHistoryLoad && activeChat.value.messages.length === 0;
});

const isSendDisabled = computed(() => {
  const textReady = draftMessage.value.trim().length > 0;
  const imageReady = Boolean(selectedImageDataUrl.value);
  const isBlockingHistoryLoad =
    historyLoadingChatId.value === activeChat.value.id &&
    !activeChat.value.loaded &&
    activeChat.value.messages.length === 0;
  return !isLoggedIn.value || isStreaming.value || isAuditStreaming.value || isBlockingHistoryLoad || (!textReady && !imageReady);
});

const streamStatusText = computed(() => {
  if (isAuditStreaming.value) {
    return t("ai.streamAudit");
  }
  if (isStreaming.value) {
    return t("ai.streamTyping");
  }
  if (
    historyLoadingChatId.value === activeChat.value.id &&
    !activeChat.value.loaded &&
    activeChat.value.messages.length === 0
  ) {
    return t("ai.loadingConversation");
  }
  return "";
});

function shouldShowAssistantThinking(message) {
  return (
    message?.role === "assistant" &&
    !message?.content &&
    (isStreaming.value || isAuditStreaming.value)
  );
}

function getAssistantThinkingTitle(message) {
  if (message?.stage === "audit" || isAuditStreaming.value) {
    return t("ai.reviewingUpload");
  }
  if (message?.stage === "nearby") {
    return t("ai.findingNearby");
  }
  if (message?.stage === "forum") {
    return t("ai.thinkingForum");
  }
  return t("ai.thinkingRequest");
}

function getAssistantThinkingCopy(message) {
  if (message?.stage === "audit" || isAuditStreaming.value) {
    return t("ai.thinkingUploadCopy");
  }
  if (message?.stage === "nearby") {
    return t("ai.thinkingNearbyCopy");
  }
  if (message?.stage === "forum") {
    return t("ai.thinkingForumCopy");
  }
  return t("ai.thinkingCopy");
}

function renderAssistantMarkdown(content) {
  const normalizedContent = String(content || "")
    .trim()
    .replace(/^```(?:markdown|md)\s*/i, "")
    .replace(/\s*```$/, "");

  const rawHtml = markdownRenderer.render(normalizedContent);
  return DOMPurify.sanitize(rawHtml, {
    USE_PROFILES: { html: true },
  });
}

function isNearBottom() {
  if (!messageContainerRef.value) {
    return true;
  }

  const container = messageContainerRef.value;
  return container.scrollHeight - container.scrollTop - container.clientHeight < 72;
}

function handleMessageScroll() {
  shouldAutoScroll.value = isNearBottom();
}

function scrollToBottom(force = false) {
  nextTick(() => {
    if (messageContainerRef.value && (force || shouldAutoScroll.value)) {
      messageContainerRef.value.scrollTop = messageContainerRef.value.scrollHeight;
    }
  });
}

function toggleSidebar() {
  isSidebarOpen.value = !isSidebarOpen.value;
}

function applyStarterPrompt(prompt) {
  draftMessage.value = prompt;
  nextTick(() => {
    composerTextareaRef.value?.focus();
  });
}

async function toggleMemoryPanel() {
  const nextState = !isMemoryPanelOpen.value;
  isMemoryPanelOpen.value = nextState;
  if (nextState) {
    await loadAiMemoryState();
  }
}

async function loadAiMemoryState() {
  if (!isLoggedIn.value) {
    aiMemorySummary.value = {};
    aiMemoryItems.value = [];
    memoryError.value = "";
    return;
  }

  memoryLoading.value = true;
  memoryError.value = "";
  try {
    const payload = await fetchAiMemory();
    aiMemorySummary.value = payload.summary || {};
    aiMemoryItems.value = payload.items || [];
  } catch (error) {
    memoryError.value = error.message || t("ai.failedLoadMemory");
  } finally {
    memoryLoading.value = false;
  }
}

async function handleDeleteMemory(itemId) {
  memoryError.value = "";
  try {
    const payload = await deleteAiMemoryItem(itemId);
    aiMemorySummary.value = payload.summary || {};
    aiMemoryItems.value = aiMemoryItems.value.filter((item) => item.id !== itemId);
  } catch (error) {
    memoryError.value = error.message || t("ai.deleteMemoryError");
  }
}

function createNewChat() {
  const existingDraft = chats.value.find((chat) => !chat.backendId && chat.messages.length === 0);
  const chat = existingDraft || createChat();
  if (!existingDraft) {
    chats.value.unshift(chat);
  }
  activeChatId.value = chat.id;
  streamError.value = "";
  historyError.value = "";
  auditError.value = "";
  draftMessage.value = "";
  clearSelectedImage();
  shouldAutoScroll.value = true;
  if (window.innerWidth <= 960) {
    isSidebarOpen.value = false;
  }
}

async function loadChatMessages(chat, { silent = false, force = false } = {}) {
  if (!chat?.backendId || !isLoggedIn.value) {
    return;
  }

  if (chat.loading && !force) {
    return;
  }

  const requestSeq = Number(chat.loadRequestSeq || 0) + 1;
  chat.loadRequestSeq = requestSeq;
  historyLoadingChatId.value = chat.id;

  chat.loading = true;
  chat.loaded = false;
  if (!silent) {
    historyError.value = "";
  }

  try {
    const payload = await fetchAiConversationMessages(chat.backendId);
    if (chat.loadRequestSeq !== requestSeq) {
      return;
    }
    chat.backendId = payload.conversation?.id || chat.backendId;
    chat.title = payload.conversation?.title || chat.title;
    chat.status = payload.conversation?.status || chat.status;
    chat.currentPendingAction = payload.conversation?.current_pending_action || chat.currentPendingAction || "none";
    chat.sessionContext = parseMaybeJson(payload.conversation?.session_context_json) || chat.sessionContext || null;
    chat.sessionId = chat.sessionContext?.session_id || chat.sessionId || null;
    chat.pendingRecyclingCase = payload.pending_recycling_case || null;
    chat.completionAuditCards = deriveCompletionAuditCards(payload.items || []);
    syncPendingRecyclingCaseCard(chat);
    chat.messages = [];

    for (const item of payload.items || []) {
      chat.messages.push(...normalizeUiMessageFromBackend(item));
    }
    syncCompletionAuditMessages(chat);

    if (chat.status === "awaiting_location") {
      chat.messages.push(
        createLocationPromptMessage({
          sessionId: chat.sessionId,
          conversationId: chat.backendId,
        }),
      );
    }
    chat.loaded = true;
  } catch (error) {
    if (chat.loadRequestSeq !== requestSeq) {
      return;
    }
    if (!silent) {
      historyError.value = error.message || t("ai.failedConversationHistory");
    }
  } finally {
    if (chat.loadRequestSeq === requestSeq) {
      chat.loading = false;
      if (historyLoadingChatId.value === chat.id) {
        historyLoadingChatId.value = null;
      }
    }
    if (chat.loadRequestSeq === requestSeq && activeChatId.value === chat.id) {
      scrollToBottom(true);
    }
  }
}

async function selectChat(chatId) {
  const chat = chats.value.find((item) => item.id === chatId);
  if (!chat) {
    return;
  }

  activeChatId.value = chatId;
  streamError.value = "";
  historyError.value = "";
  auditError.value = "";
  shouldAutoScroll.value = true;
  clearSelectedImage();

  if (window.innerWidth <= 960) {
    isSidebarOpen.value = false;
  }

  if (!chat.backendId) {
    historyLoadingChatId.value = null;
  }

  if (chat.backendId) {
    await loadChatMessages(chat, { silent: true, force: true });
  }

  scrollToBottom(true);
}

function isDeleteDisabled(chat) {
  return Boolean(
    deletingChatId.value === chat.id ||
    chat.loading ||
    (chat.id === activeChatId.value && (isStreaming.value || isAuditStreaming.value)),
  );
}

async function removeChatFromState(chatId) {
  const targetIndex = chats.value.findIndex((chat) => chat.id === chatId);
  if (targetIndex === -1) {
    return;
  }

  const wasActive = chats.value[targetIndex].id === activeChatId.value;
  chats.value.splice(targetIndex, 1);

  if (chats.value.length === 0) {
    const fallback = createChat();
    chats.value = [fallback];
    activeChatId.value = fallback.id;
    historyLoadingChatId.value = null;
    scrollToBottom(true);
    return;
  }

  if (!wasActive) {
    return;
  }

  const nextChat = chats.value[Math.min(targetIndex, chats.value.length - 1)] || chats.value[0];
  activeChatId.value = nextChat.id;
  streamError.value = "";
  historyError.value = "";
  auditError.value = "";
  clearSelectedImage();

  if (nextChat.backendId) {
    await loadChatMessages(nextChat, { silent: true });
  } else {
    historyLoadingChatId.value = null;
  }

  scrollToBottom(true);
}

async function handleDeleteChat(chat) {
  if (!chat || isDeleteDisabled(chat)) {
    return;
  }

  const chatLabel = String(chat.title || t("ai.newChatTitle")).trim() || t("ai.newChatTitle");
  if (typeof window !== "undefined") {
    const confirmed = window.confirm(t("ai.chatDeleteConfirm", { title: chatLabel }));
    if (!confirmed) {
      return;
    }
  }

  deletingChatId.value = chat.id;
  historyError.value = "";

  try {
    if (chat.backendId && isLoggedIn.value) {
      await deleteAiConversation(chat.backendId);
    }
    await removeChatFromState(chat.id);
  } catch (error) {
    historyError.value = error.message || t("ai.failedConversationHistory");
  } finally {
    if (deletingChatId.value === chat.id) {
      deletingChatId.value = null;
    }
  }
}

function openFilePicker() {
  if (!isLoggedIn.value) {
    streamError.value = t("ai.loginRequired");
    return;
  }
  fileInputRef.value?.click();
}

function clearSelectedImage() {
  selectedImageDataUrl.value = "";
  selectedImageName.value = "";
  if (fileInputRef.value) {
    fileInputRef.value.value = "";
  }
}

function readFileAsDataUrl(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(reader.result);
    reader.onerror = () => reject(new Error(t("ai.failedReadImage")));
    reader.readAsDataURL(file);
  });
}

async function handleImageSelect(event) {
  if (!isLoggedIn.value) {
    streamError.value = t("ai.loginRequired");
    clearSelectedImage();
    return;
  }

  const file = event.target.files?.[0];
  if (!file) {
    return;
  }

  if (!file.type.startsWith("image/")) {
    streamError.value = t("ai.uploadImageFileError");
    clearSelectedImage();
    return;
  }

  try {
    const dataUrl = await readCompressedImageDataUrl(file);
    selectedImageDataUrl.value = String(dataUrl);
    selectedImageName.value = file.name;
    streamError.value = "";
  } catch (error) {
    streamError.value = error.message;
  }
}

function getFirstImageFromClipboard(event) {
  const items = event?.clipboardData?.items;
  if (!items || !items.length) {
    return null;
  }

  for (const item of items) {
    if (item.kind === "file" && item.type.startsWith("image/")) {
      const file = item.getAsFile();
      if (file) {
        return file;
      }
    }
  }

  return null;
}

async function handleComposerPaste(event) {
  const imageFile = getFirstImageFromClipboard(event);
  if (!imageFile) {
    return;
  }

  event.preventDefault();
  if (!isLoggedIn.value) {
    streamError.value = t("ai.loginRequired");
    return;
  }

  try {
    const dataUrl = await readCompressedImageDataUrl(imageFile);
    selectedImageDataUrl.value = String(dataUrl);
    selectedImageName.value = imageFile.name || t("ai.pastedImage");
    streamError.value = "";
  } catch (error) {
    streamError.value = error.message || t("ai.failedPasteImage");
  }
}

function normalizeUiMessageFromBackend(message) {
  const parsedContent = parseMaybeJson(message.content_json) || {};
  if (message.message_type === "audit_result") {
    return [];
  }
  if (message.message_type === "image" && parsedContent.purpose === "completion_audit") {
    return [];
  }
  if (message.role === "assistant" && parsedContent.stream_stage === "clarification") {
    return [
      createClarificationPromptMessage({
        question: message.content_text || parsedContent.clarification_question || t("ai.needClarifyFallback"),
        options: parsedContent.clarification_options || [],
      }),
    ];
  }

  const imageCandidate = parsedContent.image_url || message.image_url || parsedContent.image_data_url || "";
  const baseMessage = {
    id: `backend-${message.id}`,
    backendMessageId: message.id,
    kind: "chat",
    role: message.role,
    content: message.content_text || "",
    imageUrl: resolveBackendUrl(imageCandidate),
    stage: parsedContent.stream_stage || "",
    messageType: message.message_type,
    contentJson: parsedContent,
    memoryUpdates: normalizeMemoryUpdates(parsedContent.memory_updates),
    forumReferences: normalizeForumReferences(
      parsedContent.forum_references || parsedContent.analysis_payload?.forum_references,
    ),
    trace: normalizeTrace(message.trace || parsedContent.trace),
    relatedAnalysisId: message.related_analysis_id || null,
  };

  const uiMessages = [baseMessage];
  if (
    message.role === "assistant" &&
    message.message_type === "tool_result" &&
    (
      Array.isArray(parsedContent.nearby_locations) ||
      parsedContent.location_state?.skip_nearby_search ||
      parsedContent.location_state?.permission_state === "denied"
    )
  ) {
    uiMessages.push(
      createNearbyResultsMessage({
        nearby_locations: parsedContent.nearby_locations,
        recycling_case_id: parsedContent.recycling_case_id || message.recycling_case?.id,
        location_state: parsedContent.location_state,
        permission_state: parsedContent.location_state?.permission_state,
      }),
    );
  }
  return uiMessages;
}

function deriveCompletionAuditCards(items) {
  const cardsByCaseId = new Map();

  function ensureCard(caseData) {
    const normalizedCase = cloneCaseData(caseData);
    const caseId = normalizeCaseId(normalizedCase?.id);
    if (!caseId) {
      return null;
    }

    const existingCard = cardsByCaseId.get(caseId) || {
      caseData: normalizedCase,
      feedback: "",
      imageUrl: "",
      locked: false,
      error: "",
    };
    if (normalizedCase) {
      existingCard.caseData = {
        ...(existingCard.caseData || {}),
        ...normalizedCase,
      };
    }
    cardsByCaseId.set(caseId, existingCard);
    return existingCard;
  }

  for (const item of items || []) {
    const parsedContent = parseMaybeJson(item.content_json) || {};
    const resolvedCase =
      cloneCaseData(item.recycling_case) || { id: normalizeCaseId(parsedContent.recycling_case_id) };
    const card = ensureCard(resolvedCase);
    if (!card) {
      continue;
    }

    if (item.message_type === "image" && parsedContent.purpose === "completion_audit") {
      card.imageUrl = resolveBackendUrl(parsedContent.image_url || item.image_url || "");
    }

    if (item.message_type === "audit_result") {
      const latestAttempt = parsedContent.audit_attempt || null;
      if (latestAttempt) {
        const nextAttempts = normalizeAuditAttempts([
          ...(card.caseData?.audit_attempts || []),
          latestAttempt,
        ]);
        card.caseData = {
          ...(card.caseData || {}),
          audit_attempts: nextAttempts,
        };
      }
      card.feedback = buildAuditSummaryText(card.caseData, parsedContent);
      if (parsedContent.finalized) {
        card.locked = true;
        card.caseData = {
          ...(card.caseData || {}),
          status: "audit_passed",
        };
      } else {
        card.locked = false;
        card.caseData = {
          ...(card.caseData || {}),
          status: "audit_failed",
        };
      }
    }
  }

  return [...cardsByCaseId.values()]
    .filter((card) => {
      const status = String(card.caseData?.status || "").toLowerCase();
      return ["pending_audit", "audit_failed", "audit_passed"].includes(status);
    })
    .sort((left, right) => normalizeCaseId(left.caseData?.id) - normalizeCaseId(right.caseData?.id));
}

function updateConversationFromStreamMeta(chat, event) {
  if (event.conversation_id) {
    chat.backendId = event.conversation_id;
  }
  if (event.conversation_title) {
    chat.title = event.conversation_title;
  }
  if (event.session_id) {
    chat.sessionId = event.session_id;
  }
}

function applyMemoryUpdatesToAssistantMessage(message, memoryUpdates) {
  if (!message) {
    return;
  }
  message.memoryUpdates = normalizeMemoryUpdates(memoryUpdates);
}

function applyForumReferencesToAssistantMessage(message, forumReferences) {
  if (!message) {
    return;
  }
  message.forumReferences = normalizeForumReferences(forumReferences);
}

function applyTraceToAssistantMessage(message, trace) {
  if (!message) {
    return;
  }
  const normalizedTrace = normalizeTrace(trace);
  if (normalizedTrace) {
    message.trace = normalizedTrace;
  }
}

function removeEmptyAssistantMessage(chat, message) {
  if (!chat || !message || message.role !== "assistant" || message.content.trim()) {
    return;
  }
  chat.messages = chat.messages.filter((item) => item.id !== message.id);
}

function applyAnalysisPayloadToConversation(chat, data) {
  if (!data) {
    return;
  }

  if (data.conversation_id) {
    chat.backendId = data.conversation_id;
  }
  if (data.recycling_case_id) {
    const nextCase = {
      id: data.recycling_case_id,
      status: "pending_audit",
      waste_type_predicted: data.waste_type || "",
      confidence: data.confidence ?? 0,
      estimated_weight_kg: data.estimated_weight_kg ?? 0,
      expected_co2_saved_kg: data.co2_saved_kg ?? 0,
      expected_carbon_points: data.carbon_points ?? 0,
      latest_audit_attempt_no: 0,
      audit_attempts: [],
    };
    chat.pendingRecyclingCase = nextCase;
    upsertCompletionAuditCardState(chat, {
      caseData: nextCase,
      feedback: "",
      imageUrl: "",
      locked: false,
      error: "",
    });
  }
  if (data.stream_stage === "awaiting_location") {
    chat.status = "awaiting_location";
    chat.currentPendingAction = "location_permission";
  } else if (data.stream_stage === "completed") {
    chat.status = "completed";
    chat.currentPendingAction = "none";
  }
}

function buildAuditSummaryText(pendingCase, payload) {
  const auditResult = payload?.audit_result?.audit_result || "unclear";
  const reason = payload?.audit_result?.audit_reason || "";

  if (payload?.finalized) {
    const points = Number(pendingCase?.expected_carbon_points || 0);
    const suffix = reason ? ` ${reason}` : "";
    return t("ai.auditPassed", { points: Math.round(points), suffix });
  }

  if (auditResult === "failed") {
    return t("ai.auditFailed", { reason });
  }

  return t("ai.auditUnclear", { reason });
}

function syncUserTotalsFromAuditPayload(payload) {
  if (!payload || !payload.finalized) {
    return;
  }

  const patch = {};
  const nextPoints = Number(payload.user_points);
  const nextCarbonAmount = Number(payload.user_carbon_amount);

  if (Number.isFinite(nextPoints)) {
    patch.current_points = nextPoints;
  }
  if (Number.isFinite(nextCarbonAmount)) {
    patch.total_carbon_amount = nextCarbonAmount;
  }

  if (Object.keys(patch).length > 0) {
    updateUser?.(patch);
  }
}

function applyConversationSummary(chat, summary) {
  chat.backendId = summary.id;
  chat.title = summary.title || chat.title;
  chat.status = summary.status || chat.status;
  chat.currentPendingAction = summary.current_pending_action || chat.currentPendingAction || "none";
  chat.sessionContext = parseMaybeJson(summary.session_context_json) || chat.sessionContext || null;
  chat.sessionId = chat.sessionContext?.session_id || chat.sessionId || null;
  chat.isDraft = false;
}

async function refreshAuthenticatedConversations({ autoSelectLatest = false } = {}) {
  if (!isLoggedIn.value) {
    return;
  }

  const requestSeq = ++conversationListRequestSeq;
  historyLoading.value = true;
  historyError.value = "";
  const selectedChatIdBefore = activeChatId.value;
  const currentChat = chats.value.find((chat) => chat.id === selectedChatIdBefore) || null;

  try {
    const payload = await fetchAiConversations({ page: 1, perPage: 50 });
    if (requestSeq !== conversationListRequestSeq) {
      return;
    }
    const shouldAutoSelect =
      autoSelectLatest &&
      currentChat &&
      !currentChat.backendId &&
      currentChat.messages.length === 0;

    const localDrafts = chats.value.filter((chat) => !chat.backendId);
    const remoteLookup = new Map(chats.value.filter((chat) => chat.backendId).map((chat) => [chat.backendId, chat]));

    const mergedRemote = (payload.items || []).map((item) => {
      const existing = remoteLookup.get(item.id);
      if (existing) {
        applyConversationSummary(existing, item);
        return existing;
      }

      const sessionContext = parseMaybeJson(item.session_context_json) || null;
      return {
        ...createChat(),
        id: `conversation-${item.id}`,
        backendId: item.id,
        title: item.title || t("ai.newChatTitle"),
        status: item.status || "active",
        currentPendingAction: item.current_pending_action || "none",
        sessionContext,
        sessionId: sessionContext?.session_id || null,
        loaded: false,
        loading: false,
      };
    });

    chats.value = [...localDrafts, ...mergedRemote];

    if (chats.value.length === 0) {
      ensureAtLeastOneChat();
      return;
    }

    const selectedStillExists = chats.value.some((chat) => chat.id === selectedChatIdBefore);
    if (selectedStillExists) {
      activeChatId.value = selectedChatIdBefore;
    } else if (!shouldAutoSelect) {
      activeChatId.value = chats.value[0].id;
    }

    if (
      shouldAutoSelect &&
      mergedRemote.length > 0 &&
      activeChatId.value === selectedChatIdBefore
    ) {
      activeChatId.value = mergedRemote[0].id;
      await loadChatMessages(mergedRemote[0], { silent: true });
      scrollToBottom(true);
    }
  } catch (error) {
    historyError.value = error.message || t("ai.failedConversationHistory");
  } finally {
    if (requestSeq === conversationListRequestSeq) {
      historyLoading.value = false;
    }
  }
}

function buildHistoryForRequest(messages) {
  return messages.flatMap((message) => {
    if (message.kind === "chat" && (message.role === "user" || message.role === "assistant") && message.content.trim()) {
      return [
        {
          role: message.role,
          content: message.content,
        },
      ];
    }

    if (message.kind === "clarification_prompt") {
      const question = String(message.question || "").trim();
      const options = Array.isArray(message.options)
        ? message.options
            .map((option) => String(option?.label || "").trim())
            .filter(Boolean)
        : [];
      const selectedOption = String(message.selectedOptionLabel || "").trim();
  const content = [
        question ? t("ai.sourceQuestion", { question }) : "",
        options.length ? t("ai.sourceOptions", { options: options.join(", ") }) : "",
        selectedOption ? t("ai.sourceOption", { label: selectedOption }) : "",
      ]
        .filter(Boolean)
        .join("\n");

      return content
        ? [
            {
              role: "assistant",
              content,
            },
          ]
        : [];
    }

    return [];
  });
}

function delay(ms) {
  return new Promise((resolve) => {
    setTimeout(resolve, ms);
  });
}

function debugAiChat(label, payload = {}) {
  const timestamp =
    typeof performance !== "undefined" && typeof performance.now === "function"
      ? performance.now().toFixed(1)
      : Date.now();
  console.info(`[CarbonSnap AI view ${timestamp}ms] ${label}`, payload);
}

function waitForFrame() {
  if (typeof window === "undefined" || typeof window.requestAnimationFrame !== "function") {
    return Promise.resolve();
  }
  return new Promise((resolve) => {
    let settled = false;
    const finish = () => {
      if (settled) {
        return;
      }
      settled = true;
      resolve();
    };
    window.requestAnimationFrame(finish);
    window.setTimeout(finish, 32);
  });
}

async function appendAssistantDelta(assistantMessage, delta) {
  const text = String(delta || "");
  if (!text) {
    return;
  }

  const chunkSize =
    text.length > 120 ? ASSISTANT_DELTA_LARGE_CHUNK_SIZE : ASSISTANT_DELTA_SMALL_CHUNK_SIZE;
  for (let index = 0; index < text.length; index += chunkSize) {
    assistantMessage.content += text.slice(index, index + chunkSize);
    await nextTick();
    await waitForFrame();
    scrollToBottom();
    await delay(ASSISTANT_DELTA_DELAY_MS);
  }
}

function removePendingLocationPrompts(chat, preservedPromptId = null) {
  chat.messages = chat.messages.filter(
    (message) =>
      message.kind !== "location_prompt" || message.resolved || message.id === preservedPromptId,
  );
}

function markLocationPromptResolved(chat, promptMessage, resolutionText) {
  const target = chat.messages.find((message) => message.id === promptMessage.id);
  if (!target) {
    return;
  }
  target.resolved = true;
  target.resolutionText = resolutionText;
  target.actionInProgress = false;
  target.error = "";
}

async function streamWorkflowIntoChat(chat, requestRunner, initialAssistantMessage = null, options = {}) {
  let currentAssistantMessage = initialAssistantMessage;
  let pendingNearbyResults = null;

  await requestRunner({
    onMeta(event) {
      updateConversationFromStreamMeta(chat, event);
      applyMemoryUpdatesToAssistantMessage(currentAssistantMessage || initialAssistantMessage, event.memory_updates);
      applyTraceToAssistantMessage(currentAssistantMessage || initialAssistantMessage, event.trace || event.decision?.trace);
    },
    onStageStart(event) {
      if (event.stage !== "analysis") {
        currentAssistantMessage = pushAssistantMessage(chat, event.stage);
        scrollToBottom();
      }
    },
    onStagePayload(event) {
      if (event.stage === "analysis" && event.data?.recycling_case_id) {
        applyAnalysisPayloadToConversation(chat, {
          ...event.data,
          stream_stage: "analysis",
        });
      }
      if (event.stage === "analysis") {
        applyForumReferencesToAssistantMessage(
          currentAssistantMessage || initialAssistantMessage,
          event.data?.forum_references,
        );
      }
    },
    async onDelta(delta) {
      if (!currentAssistantMessage) {
        currentAssistantMessage = pushAssistantMessage(chat);
      }
      await appendAssistantDelta(currentAssistantMessage, delta);
    },
    onAwaitingLocation(event) {
      removePendingLocationPrompts(chat);
      chat.status = "awaiting_location";
      chat.currentPendingAction = "location_permission";
      chat.messages.push(
        createLocationPromptMessage({
          ...(event.data || {}),
          sessionId: event.data?.session_id || chat.sessionId,
          conversationId: chat.backendId,
        }),
      );
      scrollToBottom();
    },
    async onClarification(event) {
      debugAiChat("clarification event received", event);
      if (currentAssistantMessage && !currentAssistantMessage.content.trim()) {
        chat.messages = chat.messages.filter((message) => message.id !== currentAssistantMessage.id);
        currentAssistantMessage = null;
      }
      const promptData = event.data || {};
      const promptMessage = createClarificationPromptMessage({
        ...promptData,
        question: "",
        options: [],
      });
      chat.messages.push(promptMessage);
      debugAiChat("clarification prompt inserted", {
        promptId: promptMessage.id,
        chatMessageCount: chat.messages.length,
        targetQuestion: promptData.question || "",
      });
      scrollToBottom();
      await appendClarificationQuestion(chat, promptMessage.id, promptData.question || "");
      updateClarificationPrompt(chat, promptMessage.id, {
        options: Array.isArray(promptData.options) ? promptData.options : [],
      });
      await nextTick();
      scrollToBottom();
      debugAiChat("clarification options shown", {
        promptId: promptMessage.id,
        optionCount: Array.isArray(promptData.options) ? promptData.options.length : 0,
      });
    },
    onNearbyResults(event) {
      pendingNearbyResults = event.data || {};
    },
    onDone(event) {
      debugAiChat("done event received", {
        stream_stage: event.stream_stage,
        currentAssistantMessageId: currentAssistantMessage?.id || null,
        currentAssistantContentLength: String(currentAssistantMessage?.content || "").length,
      });
      isStreaming.value = false;
      isAuditStreaming.value = false;
      applyForumReferencesToAssistantMessage(
        currentAssistantMessage || initialAssistantMessage,
        event.forum_references,
      );
      applyTraceToAssistantMessage(currentAssistantMessage || initialAssistantMessage, event.trace || event.decision?.trace);
      if (event.stream_stage === "awaiting_location") {
        removeEmptyAssistantMessage(chat, currentAssistantMessage || initialAssistantMessage);
        chat.status = "awaiting_location";
        chat.currentPendingAction = "location_permission";
        return;
      }

      if (event.stream_stage === "clarification") {
        removeEmptyAssistantMessage(chat, currentAssistantMessage || initialAssistantMessage);
        chat.status = "active";
        chat.currentPendingAction = "none";
        return;
      }

      if (event.stream_stage === "completed") {
        chat.status = "completed";
        chat.currentPendingAction = "none";
      }

      const fallbackNearbyResults =
        !pendingNearbyResults && event.stream_stage === "completed"
          ? typeof options.fallbackNearbyResults === "function"
            ? options.fallbackNearbyResults()
            : options.fallbackNearbyResults
          : null;
      const nearbyPayload = pendingNearbyResults || fallbackNearbyResults;

      if (nearbyPayload && event.stream_stage === "completed") {
        const shouldSyncCompletionAudit = !nearbyPayload.suppress_completion_audit;
        if (shouldSyncCompletionAudit && chat.pendingRecyclingCase?.id) {
          syncPendingRecyclingCaseCard(chat);
        }
        const nearbyMessage = createNearbyResultsMessage(nearbyPayload, {
          fallbackCaseId: chat.pendingRecyclingCase?.id || null,
        });
        chat.messages.push(nearbyMessage);
        pendingNearbyResults = null;
        if (shouldSyncCompletionAudit) {
          syncCompletionAuditMessages(chat);
        }
        scrollToBottom();
      }
    },
  });
}

async function sendMessage(options = {}) {
  if (!isLoggedIn.value) {
    streamError.value = t("ai.loginRequired");
    return false;
  }

  const imageData = selectedImageDataUrl.value || null;
  const rawText =
    typeof options.outgoingMessage === "string"
      ? options.outgoingMessage.trim()
      : draftMessage.value.trim();

  if (isStreaming.value || isAuditStreaming.value || (!rawText && !imageData)) {
    return;
  }

  const chat = activeChat.value;
  if (chat.backendId && !chat.loaded && !chat.loading) {
    await loadChatMessages(chat);
  }

  const outgoingMessage = rawText;
  const visibleMessage =
    typeof options.visibleMessage === "string" && options.visibleMessage.trim()
      ? options.visibleMessage.trim()
      : outgoingMessage;
  const history = buildHistoryForRequest(chat.messages);
  let clientContext = chat.auditViewContext
    ? {
        selected_audit_attempt: {
          case_id: chat.auditViewContext.caseId,
          attempt_no: chat.auditViewContext.attemptNo,
          audit_result: chat.auditViewContext.auditResult,
        },
      }
    : null;
  if (isChinese.value) {
    if (clientContext) {
      clientContext.preferred_response_language = "zh-CN";
    } else {
      clientContext = { preferred_response_language: "zh-CN" };
    }
  }

  chat.messages.push(createUserMessage(visibleMessage, imageData || ""));
  removePendingLocationPrompts(chat, options.preservedPromptId || null);

  const stageOneAssistantMessage = pushAssistantMessage(chat);

  draftMessage.value = "";
  clearSelectedImage();
  isStreaming.value = true;
  streamError.value = "";
  shouldAutoScroll.value = true;
  scrollToBottom(true);

  try {
    await streamWorkflowIntoChat(
      chat,
      (handlers) =>
        streamAiChat(
          {
            message: outgoingMessage,
            history,
            image: imageData,
            conversation_id: chat.backendId || null,
            client_context: clientContext,
          },
          handlers,
        ),
      stageOneAssistantMessage,
    );

    if (isLoggedIn.value) {
      await refreshAuthenticatedConversations({ autoSelectLatest: false });
      await loadAiMemoryState();
    }
    return true;
  } catch (error) {
    const message = error.message || "Unknown streaming error.";
    stageOneAssistantMessage.content = t("ai.errorPrefix", { message });
    streamError.value = message;
    return false;
  } finally {
    isStreaming.value = false;
    scrollToBottom();
  }
}

function buildClarificationFollowUp(promptMessage, option) {
  const question = String(promptMessage?.question || "").trim();
  const label = String(option?.label || "").trim();
  const replyText = String(option?.reply_text || "").trim();

  return {
    visibleMessage: label || replyText || t("ai.selectedOption"),
    outgoingMessage: [
      question ? `Clarification question: ${question}` : "",
      label ? `Selected option: ${label}` : "",
      replyText,
    ]
      .filter(Boolean)
      .join("\n"),
  };
}

async function handleClarificationOption(promptMessage, option) {
  const selectedLabel = String(option?.label || option?.reply_text || t("ai.selectedOption")).trim();
  const priorState = {
    actionInProgress: promptMessage.actionInProgress,
    resolved: promptMessage.resolved,
    resolutionText: promptMessage.resolutionText,
    selectedOptionLabel: promptMessage.selectedOptionLabel,
    error: promptMessage.error,
  };
  const followUp = buildClarificationFollowUp(promptMessage, option);

  promptMessage.selectedOptionLabel = selectedLabel;
  promptMessage.actionInProgress = true;
  promptMessage.resolved = true;
  promptMessage.resolutionText = t("ai.selectedResolution", { label: selectedLabel });
  promptMessage.error = "";

  const sent = await sendMessage({
    outgoingMessage: followUp.outgoingMessage,
    visibleMessage: followUp.visibleMessage,
    preservedPromptId: promptMessage.id,
  });

  if (!sent) {
    promptMessage.actionInProgress = priorState.actionInProgress;
    promptMessage.resolved = priorState.resolved;
    promptMessage.resolutionText = priorState.resolutionText;
    promptMessage.selectedOptionLabel = priorState.selectedOptionLabel;
    promptMessage.error = streamError.value || priorState.error;
  }
}

function requestBrowserLocation() {
  return new Promise((resolve, reject) => {
    if (!navigator.geolocation) {
      reject(new Error(t("ai.locationUnavailable")));
      return;
    }

    navigator.geolocation.getCurrentPosition(
      (position) => {
        resolve({
          lat: position.coords.latitude,
          lng: position.coords.longitude,
        });
      },
      (error) => {
        reject(new Error(error.message || t("ai.locationDeniedError")));
      },
      {
        enableHighAccuracy: true,
        timeout: 10000,
        maximumAge: 0,
      },
    );
  });
}

async function continuePausedFlow(chat, promptMessage, resolutionText) {
  markLocationPromptResolved(chat, promptMessage, resolutionText);
  isStreaming.value = true;
  streamError.value = "";
  shouldAutoScroll.value = true;
  scrollToBottom(true);

  try {
    await streamWorkflowIntoChat(chat, (handlers) =>
      resumeRecyclingAnalysis(
        {
          session_id: promptMessage.sessionId || chat.sessionId,
          conversation_id: promptMessage.conversationId || chat.backendId || null,
        },
        handlers,
      ),
      null,
      {
        fallbackNearbyResults: promptMessage.fallbackNearbyResults || null,
      },
    );

    if (isLoggedIn.value) {
      await refreshAuthenticatedConversations({ autoSelectLatest: false });
    }
  } catch (error) {
    streamError.value = error.message || t("ai.failedContinueNearby");
    const assistantMessage = pushAssistantMessage(chat);
    assistantMessage.content = t("ai.errorPrefix", { message: streamError.value });
  } finally {
    isStreaming.value = false;
    scrollToBottom();
  }
}

async function handleAllowBrowserLocation(promptMessage) {
  const chat = activeChat.value;
  promptMessage.actionInProgress = true;
  promptMessage.error = "";

  try {
    const coordinates = await requestBrowserLocation();
    await submitLocationContext({
      session_id: promptMessage.sessionId || chat.sessionId,
      conversation_id: promptMessage.conversationId || chat.backendId || null,
      permission_state: "granted",
      browser_location: coordinates,
    });
    await continuePausedFlow(chat, promptMessage, t("ai.browserLocationShared"));
  } catch (error) {
    try {
      await submitLocationContext({
        session_id: promptMessage.sessionId || chat.sessionId,
        conversation_id: promptMessage.conversationId || chat.backendId || null,
        permission_state: "denied",
      });
      promptMessage.fallbackNearbyResults = {
        nearby_locations: [],
        recycling_case_id: chat.pendingRecyclingCase?.id || null,
        permission_state: "denied",
      };
      await continuePausedFlow(chat, promptMessage, t("ai.browserLocationDenied"));
    } catch (resumeError) {
      promptMessage.actionInProgress = false;
      promptMessage.error = resumeError.message || error.message || t("ai.locationFailed");
    }
  }
}

async function handleManualAreaSubmit(promptMessage) {
  const chat = activeChat.value;
  promptMessage.actionInProgress = true;
  promptMessage.error = "";

  try {
    await submitLocationContext({
      session_id: promptMessage.sessionId || chat.sessionId,
      conversation_id: promptMessage.conversationId || chat.backendId || null,
      permission_state: "granted",
      manual_area: promptMessage.manualAreaInput.trim(),
    });
    await continuePausedFlow(
      chat,
      promptMessage,
      t("ai.locationManualSaved", { area: promptMessage.manualAreaInput.trim() }),
    );
  } catch (error) {
    promptMessage.actionInProgress = false;
    promptMessage.error = error.message || t("ai.locationManualSearchFailed");
  }
}

async function handleSkipNearbySearch(promptMessage) {
  const chat = activeChat.value;
  promptMessage.actionInProgress = true;
  promptMessage.error = "";

  try {
    await submitLocationContext({
      session_id: promptMessage.sessionId || chat.sessionId,
      conversation_id: promptMessage.conversationId || chat.backendId || null,
      skip_nearby_search: true,
      permission_state: "denied",
    });
    promptMessage.fallbackNearbyResults = {
      nearby_locations: [],
      recycling_case_id: chat.pendingRecyclingCase?.id || null,
      skip_nearby_search: true,
      permission_state: "denied",
      location_state: {
        skip_nearby_search: true,
        permission_state: "denied",
      },
    };
    await continuePausedFlow(chat, promptMessage, t("ai.locationSearchSkipped"));
  } catch (error) {
    promptMessage.actionInProgress = false;
    promptMessage.error = error.message || t("ai.skipNearbyError");
  }
}

async function submitCompletionAudit({ imageDataUrl, message, caseData }) {
  const chat = activeChat.value;
  const pendingCase = cloneCaseData(caseData);
  if (!pendingCase || !chat.backendId) {
    auditError.value = t("ai.noRetryCase");
    return;
  }

  isAuditStreaming.value = true;
  auditError.value = "";
  streamError.value = "";
  shouldAutoScroll.value = true;
  const note = message || t("ai.auditDefaultNote");
  upsertCompletionAuditCardState(chat, {
    caseData: pendingCase,
    feedback: "",
    imageUrl: imageDataUrl,
    attempts: pendingCase.audit_attempts || [],
    locked: false,
    error: "",
  });
  syncCompletionAuditMessages(chat);
  scrollToBottom(true);

  try {
    await streamRecyclingAudit(
      {
        conversation_id: chat.backendId,
        recycling_case_id: pendingCase.id,
        message: note,
        image: imageDataUrl,
      },
      {
        onMeta(event) {
          updateConversationFromStreamMeta(chat, event);
        },
        onStagePayload(event) {
          if (!event.data) {
            return;
          }
          const feedback = buildAuditSummaryText(pendingCase, event.data);
          const nextAttempt = {
            ...(event.data.audit_attempt || {}),
            attempt_no: Number(
              event.data.audit_attempt?.attempt_no ||
              Number(pendingCase.latest_audit_attempt_no || 0) + 1,
            ),
            audit_image_url: event.data.audit_attempt?.audit_image_url || imageDataUrl,
            audit_result: event.data.audit_result?.audit_result || "unclear",
            audit_reason: event.data.audit_result?.audit_reason || "",
          };
          const nextAttempts = normalizeAuditAttempts([
            ...(pendingCase.audit_attempts || []),
            nextAttempt,
          ]);

          if (event.data.finalized) {
            syncUserTotalsFromAuditPayload(event.data);
            chat.status = "completed";
            chat.currentPendingAction = "none";
            if (chat.pendingRecyclingCase?.id === pendingCase.id) {
              chat.pendingRecyclingCase = null;
            }
            upsertCompletionAuditCardState(chat, {
              caseData: {
                ...pendingCase,
                status: "audit_passed",
                latest_audit_attempt_no: Number(pendingCase.latest_audit_attempt_no || 0) + 1,
                approved_analysis_id: event.data.analysis_record_id || null,
                audit_attempts: nextAttempts,
              },
              feedback,
              imageUrl: imageDataUrl,
              attempts: nextAttempts,
              locked: true,
              error: "",
            });
          } else {
            const updatedCase = {
              ...pendingCase,
              status: "audit_failed",
              latest_audit_attempt_no: Number(pendingCase.latest_audit_attempt_no || 0) + 1,
              audit_attempts: nextAttempts,
            };
            chat.status = "active";
            chat.currentPendingAction = "none";
            if (chat.pendingRecyclingCase?.id === updatedCase.id) {
              chat.pendingRecyclingCase = updatedCase;
            }
            upsertCompletionAuditCardState(chat, {
              caseData: updatedCase,
              feedback,
              imageUrl: imageDataUrl,
              attempts: nextAttempts,
              locked: false,
              error: "",
            });
          }

          isAuditStreaming.value = false;
          syncCompletionAuditMessages(chat);
          scrollToBottom();
        },
        onDone(event) {
          isAuditStreaming.value = false;
          if (event.stream_stage === "completed") {
            chat.status = "completed";
          }
        },
      },
    );

    if (isLoggedIn.value) {
      await refreshAuthenticatedConversations({ autoSelectLatest: false });
    }
  } catch (error) {
    auditError.value = error.message || t("ai.auditFailedShort");
    updateCompletionAuditCardError(chat, pendingCase.id, auditError.value);
    syncCompletionAuditMessages(chat);
    const assistantMessage = pushAssistantMessage(chat, "audit");
    assistantMessage.content = t("ai.errorPrefix", { message: auditError.value });
  } finally {
    isAuditStreaming.value = false;
    scrollToBottom();
  }
}

async function loadInitialHistoryForAuthState() {
  if (!isLoggedIn.value) {
    const drafts = chats.value.filter((chat) => !chat.backendId);
    chats.value = drafts.length > 0 ? drafts : [createChat()];
    activeChatId.value = chats.value[0].id;
    aiMemorySummary.value = {};
    aiMemoryItems.value = [];
    isMemoryPanelOpen.value = false;
    return;
  }

  await refreshAuthenticatedConversations({ autoSelectLatest: true });
  await loadAiMemoryState();
}

watch(
  () => isLoggedIn.value,
  () => {
    loadInitialHistoryForAuthState();
  },
  {
    immediate: true,
  },
);

onMounted(() => {
  ensureAtLeastOneChat();
  scrollToBottom(true);
});

</script>

<style scoped>
.ai-chat-page {
  --chat-shell-height: calc(100dvh - 156px);
  display: grid;
  flex: 1;
  grid-template-columns: 320px minmax(0, 1fr);
  height: var(--chat-shell-height);
  max-height: var(--chat-shell-height);
  min-height: 0;
  background:
    radial-gradient(circle at top right, rgba(185, 246, 0, 0.15), transparent 28%),
    linear-gradient(180deg, #f3f7f5 0%, #edf2f0 100%);
  overflow: hidden;
  overscroll-behavior: none;
  border: 1px solid var(--cs-outline);
  border-radius: 32px;
  box-shadow: var(--cs-shadow-soft);
}

.chat-sidebar {
  border-right: 1px solid var(--cs-outline);
  background: linear-gradient(180deg, rgba(237, 242, 240, 0.92) 0%, rgba(228, 233, 231, 0.96) 100%);
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 0;
  overflow: hidden;
  padding: 14px;
}

.chat-sidebar__top {
  display: flex;
  flex-direction: column;
  gap: 10px;
  margin-bottom: 12px;
}

.chat-sidebar__new-button {
  width: 100%;
  border: 1px solid transparent;
  border-radius: 999px;
  background: var(--cs-primary);
  color: #d1ffc8;
  font-family: var(--cs-font-heading);
  font-size: 0.95rem;
  font-weight: 700;
  padding: 12px 14px;
  cursor: pointer;
}

.chat-sidebar__memory-button {
  width: 100%;
  border: 1px solid var(--cs-outline);
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.9);
  color: var(--cs-text);
  font-family: var(--cs-font-heading);
  font-size: 0.95rem;
  font-weight: 600;
  padding: 12px 14px;
  cursor: pointer;
}

.chat-sidebar__list {
  list-style: none;
  margin: 0;
  min-height: 0;
  overflow: auto;
  overscroll-behavior: contain;
  padding: 0;
}

.chat-sidebar__entry {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 4px;
  border: 1px solid transparent;
  border-radius: 18px;
  background: transparent;
  transition: background-color 180ms ease, border-color 180ms ease, transform 180ms ease;
}

.chat-sidebar__entry:hover,
.chat-sidebar__entry:focus-within {
  background: rgba(255, 255, 255, 0.62);
  border-color: rgba(38, 104, 41, 0.08);
}

.chat-sidebar__entry--active {
  background: rgba(255, 255, 255, 0.94);
  border-color: rgba(38, 104, 41, 0.18);
}

.chat-sidebar__entry--deleting {
  opacity: 0.62;
}

.chat-sidebar__item {
  flex: 1;
  min-width: 0;
  border: 0;
  background: transparent;
  border-radius: 18px;
  color: var(--cs-text-muted);
  cursor: pointer;
  font-family: var(--cs-font-body);
  font-size: 0.95rem;
  font-weight: 600;
  padding: 12px 14px;
  text-align: left;
}

.chat-sidebar__item:disabled {
  cursor: default;
}

.chat-sidebar__entry:hover .chat-sidebar__item,
.chat-sidebar__entry:focus-within .chat-sidebar__item,
.chat-sidebar__entry--active .chat-sidebar__item {
  color: var(--cs-primary);
}

.chat-sidebar__item-title {
  display: block;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.chat-sidebar__delete {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  width: 32px;
  height: 32px;
  margin-right: 8px;
  border: 0;
  border-radius: 10px;
  background: rgba(255, 255, 255, 0.88);
  color: #66716c;
  cursor: pointer;
  opacity: 0;
  pointer-events: none;
  transform: translateX(4px);
  transition: opacity 160ms ease, transform 160ms ease, background-color 160ms ease, color 160ms ease;
}

.chat-sidebar__delete:hover,
.chat-sidebar__delete:focus-visible {
  background: rgba(255, 241, 241, 0.96);
  color: #a33737;
  outline: none;
}

.chat-sidebar__delete:disabled {
  cursor: default;
  opacity: 0.35;
}

.chat-sidebar__entry:hover .chat-sidebar__delete,
.chat-sidebar__entry:focus-within .chat-sidebar__delete {
  opacity: 1;
  pointer-events: auto;
  transform: translateX(0);
}

@media (prefers-reduced-motion: reduce) {
  .chat-sidebar__entry,
  .chat-sidebar__delete {
    transition: none;
  }
}

.chat-main {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 0;
  overflow: hidden;
  position: relative;
}

.chat-main__memory-panel {
  bottom: 0;
  position: absolute;
  right: 0;
  top: 0;
  width: min(360px, 100%);
  z-index: 6;
}

.chat-main__header {
  border-bottom: 1px solid var(--cs-outline);
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 16px 20px;
  background: rgba(255, 255, 255, 0.5);
}

.chat-main__menu-button {
  display: none;
  border: 1px solid var(--cs-outline);
  border-radius: 999px;
  background: #ffffff;
  color: var(--cs-primary);
  font-weight: 600;
  padding: 8px 12px;
  cursor: pointer;
}

.chat-main__title {
  color: var(--cs-text);
  font-family: var(--cs-font-heading);
  font-size: 1.26rem;
  margin: 0;
}

.chat-main__messages {
  flex: 1;
  min-height: 0;
  overflow: auto;
  overscroll-behavior: contain;
  padding: 18px 20px 32px;
}

.chat-main__a11y-summary {
  position: absolute;
  width: 1px;
  height: 1px;
  margin: -1px;
  padding: 0;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  white-space: nowrap;
  border: 0;
}

.chat-welcome-state {
  display: grid;
  gap: 24px;
  min-height: 100%;
  align-content: center;
  padding: 10px 6px 24px;
}

.chat-welcome-state__hero {
  display: grid;
  justify-items: center;
  gap: 14px;
  text-align: center;
}

.chat-welcome-state__icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 72px;
  height: 72px;
  border-radius: 24px;
  background: var(--cs-primary);
  box-shadow: 0 18px 36px rgba(38, 104, 41, 0.18);
  color: #d1ffc8;
  font-family: var(--cs-font-heading);
  font-size: 1.35rem;
  font-weight: 800;
}

.chat-welcome-state__title {
  font-size: clamp(2rem, 4vw, 3rem);
}

.chat-welcome-state__subtitle {
  max-width: 52ch;
  color: var(--cs-text-muted);
  line-height: 1.7;
}

.chat-welcome-state__prompts {
  display: grid;
  gap: 14px;
  grid-template-columns: repeat(3, minmax(0, 1fr));
}

.chat-welcome-state__prompt {
  display: grid;
  gap: 10px;
  align-content: start;
  border: 1px solid var(--cs-outline);
  border-radius: 24px;
  background: rgba(255, 255, 255, 0.9);
  padding: 18px;
  text-align: left;
  transition: transform 180ms ease, box-shadow 180ms ease, border-color 180ms ease;
}

.chat-welcome-state__prompt:hover,
.chat-welcome-state__prompt:focus-visible {
  transform: translateY(-2px);
  border-color: rgba(38, 104, 41, 0.24);
  box-shadow: var(--cs-shadow-soft);
  outline: none;
}

.chat-welcome-state__prompt-label {
  color: var(--cs-primary);
  font-size: 0.78rem;
  font-weight: 800;
  letter-spacing: 0.18em;
  text-transform: uppercase;
}

.chat-welcome-state__prompt-copy {
  color: var(--cs-text);
  line-height: 1.55;
}

.chat-welcome-state__cards {
  display: grid;
  gap: 18px;
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.chat-welcome-card {
  display: grid;
  gap: 14px;
  border: 1px solid var(--cs-outline);
  border-radius: 28px;
  background: rgba(255, 255, 255, 0.82);
  padding: 22px;
}

.chat-welcome-card__eyebrow {
  color: var(--cs-text-soft);
  font-size: 0.76rem;
  font-weight: 800;
  letter-spacing: 0.18em;
  text-transform: uppercase;
}

.chat-welcome-card__list {
  display: grid;
  gap: 10px;
  margin: 0;
  padding-left: 18px;
  color: var(--cs-text-muted);
  line-height: 1.6;
}

.chat-welcome-card__history {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.chat-welcome-card__history-item {
  border-radius: 999px;
  background: rgba(185, 246, 0, 0.16);
  color: #4f6500;
  padding: 8px 12px;
  font-size: 0.92rem;
  font-weight: 700;
}

.chat-welcome-card__empty {
  color: var(--cs-text-muted);
  line-height: 1.6;
}

.chat-message {
  display: flex;
  margin-bottom: 14px;
}

.chat-message--assistant {
  justify-content: flex-start;
}

.chat-message--user {
  justify-content: flex-end;
}

.chat-message__bubble {
  border-radius: 14px;
  max-width: min(820px, 84%);
  padding: 12px 14px;
  word-break: break-word;
}

.chat-message--assistant .chat-message__bubble {
  background: #ffffff;
  border: 1px solid var(--cs-outline);
  box-shadow: 0 8px 24px rgba(43, 48, 47, 0.05);
  white-space: normal;
}

.chat-message--user .chat-message__bubble {
  background: var(--cs-primary);
  color: #f5fff2;
  white-space: pre-wrap;
}

.chat-message__text {
  margin: 0;
  line-height: 1.55;
}

.chat-message__memory-hint {
  color: rgba(22, 74, 66, 0.72);
  font-size: 0.88rem;
  font-style: italic;
  line-height: 1.45;
  margin: 8px 0 0;
}

.chat-message__sources {
  border-top: 1px solid rgba(15, 118, 110, 0.12);
  margin-top: 10px;
  padding-top: 10px;
}

.chat-message__sources-title {
  color: #365a56;
  font-size: 0.88rem;
  font-weight: 700;
  margin: 0 0 6px;
}

.chat-message__sources-list {
  display: grid;
  gap: 6px;
  list-style: none;
  margin: 0;
  padding: 0;
}

.chat-message__sources-link {
  color: #0f766e;
  font-size: 0.92rem;
  font-weight: 600;
  text-decoration: underline;
  text-underline-offset: 2px;
}

.chat-message__markdown {
  color: inherit;
  line-height: 1.6;
}

.chat-message__markdown :deep(*) {
  margin: 0;
}

.chat-message__markdown :deep(p + p),
.chat-message__markdown :deep(ul),
.chat-message__markdown :deep(ol),
.chat-message__markdown :deep(blockquote),
.chat-message__markdown :deep(pre) {
  margin-top: 10px;
}

.chat-message__markdown :deep(h1),
.chat-message__markdown :deep(h2),
.chat-message__markdown :deep(h3) {
  color: #0b3d35;
  font-family: "Space Grotesk", "Trebuchet MS", sans-serif;
  line-height: 1.3;
  margin-top: 14px;
}

.chat-message__markdown :deep(h1) {
  font-size: 1.4rem;
}

.chat-message__markdown :deep(h2) {
  font-size: 1.22rem;
}

.chat-message__markdown :deep(h3) {
  font-size: 1.08rem;
}

.chat-message__markdown :deep(ul),
.chat-message__markdown :deep(ol) {
  margin-bottom: 0;
  padding-left: 20px;
}

.chat-message__markdown :deep(li) {
  margin-top: 6px;
}

.chat-message__markdown :deep(strong) {
  font-weight: 700;
}

.chat-message__markdown :deep(a) {
  color: #0f766e;
  text-decoration: underline;
  text-underline-offset: 2px;
}

.chat-message__markdown :deep(code) {
  background: rgba(15, 118, 110, 0.12);
  border-radius: 6px;
  font-family: "Consolas", "Courier New", monospace;
  font-size: 0.92em;
  padding: 2px 6px;
}

.chat-message__markdown :deep(pre) {
  background: #0b1f2e;
  border-radius: 10px;
  overflow: auto;
  padding: 12px;
}

.chat-message__markdown :deep(pre code) {
  background: transparent;
  color: #e2ecf7;
  display: block;
  padding: 0;
}

.chat-message__markdown :deep(blockquote) {
  border-left: 3px solid rgba(15, 118, 110, 0.5);
  color: #365a56;
  padding-left: 10px;
}

.chat-message__image {
  display: block;
  border-radius: 10px;
  margin-bottom: 10px;
  max-height: 260px;
  max-width: min(360px, 100%);
  object-fit: cover;
}

.chat-message__thinking {
  min-width: min(420px, 100%);
}

.chat-message__thinking-header {
  align-items: center;
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin-bottom: 10px;
}

.chat-message__thinking-badge {
  border: 1px solid rgba(27, 94, 32, 0.14);
  border-radius: 999px;
  background: rgba(208, 255, 200, 0.6);
  color: var(--cs-primary);
  font-size: 0.78rem;
  font-weight: 800;
  letter-spacing: 0.04em;
  padding: 6px 10px;
  text-transform: uppercase;
}

.chat-message__thinking-stage {
  color: var(--cs-text);
  font-family: var(--cs-font-heading);
  font-size: 1rem;
  font-weight: 700;
}

.chat-message__thinking-copy {
  color: #486560;
  line-height: 1.65;
  margin: 0;
}

.chat-message__thinking-dots {
  align-items: center;
  display: inline-flex;
  gap: 8px;
  margin-top: 14px;
}

.chat-message__thinking-dots span {
  animation: chat-thinking-pulse 1.25s ease-in-out infinite;
  background: linear-gradient(135deg, rgba(27, 94, 32, 0.96), rgba(118, 171, 80, 0.9));
  border-radius: 999px;
  box-shadow: 0 10px 20px rgba(26, 87, 28, 0.16);
  display: inline-block;
  height: 10px;
  width: 10px;
}

.chat-message__thinking-dots span:nth-child(2) {
  animation-delay: 160ms;
}

.chat-message__thinking-dots span:nth-child(3) {
  animation-delay: 320ms;
}

@keyframes chat-thinking-pulse {
  0%,
  80%,
  100% {
    opacity: 0.35;
    transform: translateY(0) scale(0.92);
  }

  40% {
    opacity: 1;
    transform: translateY(-2px) scale(1);
  }
}

.chat-card {
  border: 1px solid var(--cs-outline);
  border-radius: 24px;
  background: rgba(255, 255, 255, 0.92);
  box-shadow: var(--cs-shadow-soft);
  margin-bottom: 14px;
  max-width: min(820px, 84%);
  padding: 16px;
}

.chat-composer-slot {
  margin-bottom: 14px;
  max-width: min(820px, 84%);
}

.chat-card__map {
  margin-bottom: 14px;
}

.chat-card__header {
  margin-bottom: 12px;
}

.chat-card__title {
  color: var(--cs-text);
  font-family: var(--cs-font-heading);
  font-size: 1.06rem;
  margin: 0;
}

.chat-card__subtitle {
  color: #486560;
  line-height: 1.5;
  margin: 6px 0 0;
  max-width: 100%;
  overflow-wrap: anywhere;
  white-space: normal;
  word-break: normal;
}

.chat-card__subtitle--clarification {
  display: block;
  min-height: 1.5em;
  white-space: pre-wrap;
}

.chat-card__actions {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.chat-card__button {
  border: 1px solid var(--cs-outline);
  border-radius: 999px;
  background: #ffffff;
  color: var(--cs-text);
  cursor: pointer;
  font-weight: 700;
  padding: 10px 14px;
}

.chat-card__button--primary {
  border-color: transparent;
  background: var(--cs-primary);
  color: #d1ffc8;
}

.chat-card__button--ghost {
  background: #f6fbfa;
}

.chat-card__manual {
  display: flex;
  gap: 10px;
  margin-top: 12px;
}

.chat-card__input {
  flex: 1;
  border: 1px solid #cad7e7;
  border-radius: 10px;
  font-family: "Source Sans 3", "Segoe UI", sans-serif;
  font-size: 1rem;
  padding: 10px 12px;
}

.chat-card__status {
  color: #0f766e;
  font-weight: 700;
}

.chat-card__error {
  color: #b91c1c;
  font-weight: 600;
  margin: 10px 0 0;
}

.chat-main__streaming {
  color: #0f766e;
  font-weight: 600;
}

.chat-main__error {
  color: #b91c1c;
  font-weight: 600;
}


.chat-input {
  position: sticky;
  bottom: 0;
  border-top: 1px solid var(--cs-outline);
  background: rgba(255, 255, 255, 0.76);
  backdrop-filter: blur(6px);
  flex-shrink: 0;
  padding: 12px 20px 18px;
  z-index: 2;
}

.chat-input__auth-required {
  color: #475569;
  font-weight: 600;
  margin: 0 0 10px;
}

.chat-input__auth-required a {
  color: var(--cs-primary);
  font-weight: 800;
  text-decoration: none;
}

.chat-input__auth-required a:hover {
  text-decoration: underline;
  text-underline-offset: 3px;
}

.chat-input__preview {
  align-items: center;
  background: #ffffff;
  border: 1px solid #d7e2ef;
  border-radius: 12px;
  display: flex;
  gap: 12px;
  margin-bottom: 10px;
  padding: 8px;
}

.chat-input__preview-image {
  border-radius: 8px;
  height: 64px;
  object-fit: cover;
  width: 64px;
}

.chat-input__preview-meta {
  align-items: flex-start;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.chat-input__preview-name {
  color: #1f2937;
  font-weight: 600;
}

.chat-input__remove-image {
  border: none;
  background: transparent;
  color: #b91c1c;
  cursor: pointer;
  font-weight: 600;
  margin: 0;
  padding: 0;
}

.chat-input__row {
  align-items: flex-end;
  display: grid;
  gap: 10px;
  grid-template-columns: auto minmax(0, 1fr) auto;
}

.chat-input__file {
  display: none;
}

.chat-input__attach {
  border: 1px solid var(--cs-outline);
  border-radius: 999px;
  background: #ffffff;
  color: var(--cs-primary);
  font-weight: 700;
  margin: 0;
  padding: 10px 12px;
}

.chat-input__textarea {
  border: 1px solid #cad7e7;
  border-radius: 12px;
  font-family: "Source Sans 3", "Segoe UI", sans-serif;
  font-size: 1rem;
  line-height: 1.5;
  max-height: 180px;
  min-height: 46px;
  padding: 10px 12px;
  resize: vertical;
}

.chat-input__send {
  border: 1px solid transparent;
  border-radius: 999px;
  background: var(--cs-primary);
  color: #d1ffc8;
  font-weight: 700;
  margin: 0;
  padding: 10px 16px;
}

.chat-input__send:disabled {
  cursor: not-allowed;
  opacity: 0.5;
}

.chat-input__attach:disabled,
.chat-input__textarea:disabled {
  cursor: not-allowed;
  opacity: 0.62;
}

@media (max-width: 960px) {
  .ai-chat-page {
    --chat-shell-height: calc(100dvh - 132px);
    grid-template-columns: minmax(0, 1fr);
    position: relative;
  }

  .chat-sidebar {
    bottom: 0;
    left: 0;
    max-width: 280px;
    position: absolute;
    top: 0;
    transform: translateX(-100%);
    transition: transform 200ms ease;
    width: 85%;
    z-index: 5;
  }

  .chat-sidebar--open {
    transform: translateX(0);
  }

  .chat-main__menu-button {
    display: inline-flex;
  }
}

@media (max-width: 640px) {
  .ai-chat-page {
    --chat-shell-height: calc(100dvh - 116px);
    border-radius: 24px;
  }

  .chat-main__messages {
    padding-left: 12px;
    padding-right: 12px;
  }

  .chat-welcome-state__prompts,
  .chat-welcome-state__cards {
    grid-template-columns: 1fr;
  }

  .chat-input {
    padding-left: 12px;
    padding-right: 12px;
  }

  .chat-input__row,
  .chat-card__manual {
    grid-template-columns: 1fr;
    flex-direction: column;
  }

  .chat-input__attach,
  .chat-input__send,
  .chat-card__button {
    width: 100%;
  }

  .chat-message__bubble {
    max-width: 100%;
  }

  .chat-message__thinking {
    min-width: 0;
  }

  .chat-composer-slot {
    max-width: 100%;
  }
}
</style>







