<template>
  <section class="completion-audit-composer" aria-labelledby="completion-audit-composer__title">
    <div class="completion-audit-composer__header">
      <div>
        <p class="completion-audit-composer__eyebrow">{{ t("ai.completionAudit") }}</p>
        <h2 id="completion-audit-composer__title" class="completion-audit-composer__title">
          {{ t("ai.auditTitle") }}
        </h2>
        <p class="completion-audit-composer__subtitle">
          {{ t("ai.auditBody") }}
        </p>
      </div>
      <span class="completion-audit-composer__badge">{{ statusLabel }}</span>
    </div>

    <dl v-if="caseData" class="completion-audit-composer__summary">
      <div>
        <dt>{{ t("ai.auditPredictedWaste") }}</dt>
        <dd>{{ caseData.waste_type_predicted || t("ai.auditUnknown") }}</dd>
      </div>
      <div>
        <dt>{{ t("ai.auditExpectedPoints") }}</dt>
        <dd>{{ formatPoints(caseData.expected_carbon_points) }}</dd>
      </div>
      <div>
        <dt>{{ t("ai.auditAttempts") }}</dt>
        <dd>{{ attemptLabel }}</dd>
      </div>
      <div>
        <dt>{{ t("ai.auditStatus") }}</dt>
        <dd>{{ statusLabel }}</dd>
      </div>
    </dl>

    <div v-if="!locked" class="completion-audit-composer__upload">
      <input
        ref="fileInputRef"
        class="completion-audit-composer__file"
        type="file"
        accept="image/*"
        @change="handleFileChange"
      />

      <button
        class="completion-audit-composer__select-button"
        type="button"
        :disabled="busy"
        @click="openFilePicker"
      >
        {{ t("ai.auditChoosePhoto") }}
      </button>

      <p class="completion-audit-composer__hint">
        {{ t("ai.auditPhotoHint") }}
      </p>
    </div>

    <div v-if="displayImageUrl" class="completion-audit-composer__preview">
      <img class="completion-audit-composer__preview-image" :src="displayImageUrl" :alt="t('ai.uploadPreviewAlt')" />
      <div class="completion-audit-composer__preview-meta">
        <span class="completion-audit-composer__preview-name">{{ previewLabel }}</span>
        <div class="completion-audit-composer__preview-actions">
          <div v-if="showAttemptNavigator" class="completion-audit-composer__attempt-nav">
            <button
              class="completion-audit-composer__attempt-button"
              type="button"
              :disabled="!canViewPreviousAttempt"
              @click="viewPreviousAttempt"
            >
              {{ t("ai.auditPrevious") }}
            </button>
            <span class="completion-audit-composer__attempt-count">{{ attemptCounterLabel }}</span>
            <button
              class="completion-audit-composer__attempt-button"
              type="button"
              :disabled="!canViewNextAttempt"
              @click="viewNextAttempt"
            >
              {{ t("ai.auditNext") }}
            </button>
          </div>
          <button
            v-if="!locked && hasLocalSelection"
            class="completion-audit-composer__remove"
            type="button"
            :disabled="busy"
            @click="clearSelection"
          >
            {{ t("ai.remove") }}
          </button>
        </div>
      </div>
    </div>

    <label v-if="!locked" class="completion-audit-composer__label" for="completion-audit-composer__note">
      {{ t("ai.auditNoteLabel") }}
    </label>
    <textarea
      v-if="!locked"
      id="completion-audit-composer__note"
      v-model="note"
      class="completion-audit-composer__textarea"
      rows="3"
      :placeholder="t('ai.auditNotePlaceholder')"
      :disabled="busy"
    />

    <div v-if="!locked" class="completion-audit-composer__actions">
      <button
        class="completion-audit-composer__submit"
        type="button"
        :disabled="busy || !canSubmitAudit"
        @click="submitAudit"
      >
        {{ busy ? t("ai.auditVerifying") : t("ai.auditSubmit") }}
      </button>
    </div>

    <p v-if="helperText" class="completion-audit-composer__helper">{{ helperText }}</p>
    <div v-if="displayedFeedback" class="completion-audit-composer__feedback">
      <p class="completion-audit-composer__feedback-label">{{ t("ai.auditFeedback") }}</p>
      <p v-if="selectedAttemptMeta" class="completion-audit-composer__attempt-meta">
        Attempt {{ selectedAttemptMeta.attempt_no }} · {{ selectedAttemptMeta.resultLabel }}
      </p>
      <p class="completion-audit-composer__feedback-text">{{ displayedFeedback }}</p>
    </div>
    <p v-if="error" class="completion-audit-composer__error">{{ error }}</p>
  </section>
</template>

<script setup>
import { computed, ref, watch } from "vue";
import { readCompressedImageDataUrl } from "../../utils/imageDataUrl.js";
import { useI18n } from "../../i18n/index.js";

const props = defineProps({
  caseData: {
    type: Object,
    default: null,
  },
  busy: {
    type: Boolean,
    default: false,
  },
  error: {
    type: String,
    default: "",
  },
  feedback: {
    type: String,
    default: "",
  },
  submittedImageUrl: {
    type: String,
    default: "",
  },
  attempts: {
    type: Array,
    default: () => [],
  },
  locked: {
    type: Boolean,
    default: false,
  },
});

const emit = defineEmits(["submit", "attempt-view-change"]);
const { t } = useI18n();

const fileInputRef = ref(null);
const previewUrl = ref("");
const selectedFileName = ref("");
const note = ref("");
const selectedAttemptIndex = ref(0);

function mergeAttempt(existingAttempt, incomingAttempt) {
  return {
    ...existingAttempt,
    ...incomingAttempt,
    id:
      String(incomingAttempt?.id || "").startsWith("attempt-") &&
      !String(existingAttempt?.id || "").startsWith("attempt-")
        ? existingAttempt.id
        : (incomingAttempt?.id ?? existingAttempt?.id),
    audit_reason:
      String(incomingAttempt?.audit_reason || "").trim().length >=
      String(existingAttempt?.audit_reason || "").trim().length
        ? incomingAttempt.audit_reason
        : existingAttempt.audit_reason,
    audit_image_url: incomingAttempt?.audit_image_url || existingAttempt?.audit_image_url || "",
  };
}

const normalizedAttempts = computed(() =>
  ((Array.isArray(props.attempts) ? props.attempts : [])
    .map((attempt, index) => {
      if (!attempt || typeof attempt !== "object") {
        return null;
      }

      const attemptNo = Number(attempt.attempt_no || index + 1);
      const auditResult = String(attempt.audit_result || "unclear").trim().toLowerCase();
      return {
        id: attempt.id ?? `attempt-${attemptNo}`,
        attempt_no: Number.isFinite(attemptNo) && attemptNo > 0 ? attemptNo : index + 1,
        audit_result: auditResult,
        audit_reason: String(attempt.audit_reason || "").trim(),
        audit_image_url: String(attempt.audit_image_url || "").trim(),
      };
    })
    .filter(Boolean)
    .reduce((uniqueAttempts, attempt) => {
      const hasAttemptNo = Number.isFinite(attempt.attempt_no) && attempt.attempt_no > 0;
      const attemptKey = hasAttemptNo
        ? `no:${attempt.attempt_no}`
        : attempt.id != null
          ? `id:${attempt.id}`
          : `img:${attempt.audit_image_url}`;
      const existingIndex = uniqueAttempts.findIndex((existingAttempt) => {
        const existingHasAttemptNo =
          Number.isFinite(existingAttempt.attempt_no) && existingAttempt.attempt_no > 0;
        const existingKey = existingHasAttemptNo
          ? `no:${existingAttempt.attempt_no}`
          : existingAttempt.id != null
            ? `id:${existingAttempt.id}`
            : `img:${existingAttempt.audit_image_url}`;
        return existingKey === attemptKey;
      });

      if (existingIndex >= 0) {
        uniqueAttempts.splice(
          existingIndex,
          1,
          mergeAttempt(uniqueAttempts[existingIndex], attempt),
        );
        return uniqueAttempts;
      }

      uniqueAttempts.push(attempt);
      return uniqueAttempts;
    }, []))
    .sort((left, right) => left.attempt_no - right.attempt_no),
);

const statusLabel = computed(() => {
  const status = String(props.caseData?.status || "").toLowerCase();
  if (status === "audit_failed") {
    return t("ai.statusRetryable");
  }
  if (status === "pending_audit") {
    return t("ai.statusPending");
  }
  if (status === "audit_passed") {
    return t("ai.statusVerified");
  }
  return t("ai.statusReady");
});

const attemptLabel = computed(() => {
  const latestAttemptNo = Number(props.caseData?.latest_audit_attempt_no || 0);
  const countedAttempts = Math.max(latestAttemptNo, normalizedAttempts.value.length);
  return `${countedAttempts}`;
});

const selectedAttempt = computed(() => normalizedAttempts.value[selectedAttemptIndex.value] || null);

const showAttemptNavigator = computed(() => normalizedAttempts.value.length > 1);

const canViewPreviousAttempt = computed(() => selectedAttemptIndex.value > 0);

const canViewNextAttempt = computed(() => selectedAttemptIndex.value < normalizedAttempts.value.length - 1);

const attemptCounterLabel = computed(() => {
  if (!normalizedAttempts.value.length) {
    return "";
  }
  return `${selectedAttemptIndex.value + 1}/${normalizedAttempts.value.length}`;
});

const helperText = computed(() => {
  if (!props.caseData) {
    return t("ai.auditReadyHint");
  }

  if (String(props.caseData.status || "") === "audit_passed") {
    return t("ai.auditCompleteHint");
  }

  if (String(props.caseData.status || "") === "audit_failed") {
    return t("ai.auditHelperRetry");
  }

  return t("ai.auditHelperDefault");
});

const displayImageUrl = computed(
  () => previewUrl.value || selectedAttempt.value?.audit_image_url || props.submittedImageUrl || "",
);
const hasLocalSelection = computed(() => Boolean(previewUrl.value));
const canSubmitAudit = computed(() => Boolean(previewUrl.value));

const previewLabel = computed(() => {
  if (selectedFileName.value) {
    return selectedFileName.value;
  }
  if (selectedAttempt.value) {
    return t("ai.auditAttemptPhoto", { attempt: selectedAttempt.value.attempt_no });
  }
  if (props.locked) {
    return t("ai.auditVerifiedPhoto");
  }
  if (props.submittedImageUrl) {
    return t("ai.uploadedCompletionPhoto");
  }
  return "";
});

const selectedAttemptMeta = computed(() => {
  if (!selectedAttempt.value) {
    return null;
  }

  const result = String(selectedAttempt.value.audit_result || "unclear").toLowerCase();
  let resultLabel = t("ai.auditResultUnclear");
  if (result === "passed") {
    resultLabel = t("ai.auditResultPassed");
  } else if (result === "failed") {
    resultLabel = t("ai.auditResultFailed");
  }

  return {
    attempt_no: selectedAttempt.value.attempt_no,
    resultLabel,
  };
});

const displayedFeedback = computed(() => {
  if (!selectedAttempt.value) {
    return props.feedback || "";
  }

  const isViewingLatestAttempt = selectedAttemptIndex.value === normalizedAttempts.value.length - 1;
  if (props.feedback && isViewingLatestAttempt && selectedAttempt.value.audit_result === "passed") {
    return props.feedback;
  }

  const reason = selectedAttempt.value.audit_reason || t("ai.noDetailedFeedback");
  const auditResult = selectedAttempt.value.audit_result;
  if (auditResult === "failed") {
    return t("ai.auditFailed", { reason });
  }
  if (auditResult === "passed") {
    return t("ai.auditPassedReason", { reason });
  }
  return t("ai.auditUnclear", { reason });
});

watch(
  normalizedAttempts,
  (attempts, previousAttempts) => {
    const previousLength = Array.isArray(previousAttempts) ? previousAttempts.length : 0;
    if (!attempts.length) {
      selectedAttemptIndex.value = 0;
      return;
    }

    if (attempts.length !== previousLength || selectedAttemptIndex.value >= attempts.length) {
      selectedAttemptIndex.value = attempts.length - 1;
    }
  },
  { immediate: true },
);

watch(
  selectedAttempt,
  (attempt) => {
    if (!attempt || !props.caseData?.id) {
      return;
    }
    emit("attempt-view-change", {
      caseId: Number(props.caseData.id),
      attemptNo: Number(attempt.attempt_no),
      auditResult: String(attempt.audit_result || "unclear"),
    });
  },
  { immediate: true },
);

function formatPoints(value) {
  const numeric = Number(value || 0);
  if (!Number.isFinite(numeric)) {
    return "0";
  }
  return `${numeric.toFixed(Number.isInteger(numeric) ? 0 : 1)} pts`;
}

function openFilePicker() {
  fileInputRef.value?.click();
}

function clearSelection() {
  previewUrl.value = "";
  selectedFileName.value = "";
  note.value = "";
  if (fileInputRef.value) {
    fileInputRef.value.value = "";
  }
}

function readFileAsDataUrl(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(String(reader.result || ""));
    reader.onerror = () => reject(new Error(t("ai.failedReadCompletionPhoto")));
    reader.readAsDataURL(file);
  });
}

async function handleFileChange(event) {
  const file = event.target.files?.[0];
  if (!file) {
    return;
  }

  if (!file.type.startsWith("image/")) {
    clearSelection();
    return;
  }

  try {
    previewUrl.value = await readCompressedImageDataUrl(file);
    selectedFileName.value = file.name;
  } catch {
    clearSelection();
  }
}

function submitAudit() {
  if (!previewUrl.value) {
    return;
  }

  emit("submit", {
    imageDataUrl: previewUrl.value,
    message: note.value.trim(),
  });
}

function viewPreviousAttempt() {
  if (!canViewPreviousAttempt.value) {
    return;
  }
  selectedAttemptIndex.value -= 1;
}

function viewNextAttempt() {
  if (!canViewNextAttempt.value) {
    return;
  }
  selectedAttemptIndex.value += 1;
}
</script>

<style scoped>
.completion-audit-composer {
  border: 1px solid rgba(15, 118, 110, 0.14);
  border-radius: 22px;
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.96) 0%, rgba(239, 252, 247, 0.95) 100%);
  box-shadow: 0 18px 36px rgba(15, 23, 42, 0.08);
  padding: 18px 20px 20px;
}

.completion-audit-composer__header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
}

.completion-audit-composer__eyebrow {
  margin: 0 0 4px;
  color: #0f766e;
  font-size: 0.76rem;
  font-weight: 800;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.completion-audit-composer__title {
  margin: 0;
  color: #102a43;
  font-family: "Space Grotesk", "Trebuchet MS", sans-serif;
  font-size: 1.08rem;
}

.completion-audit-composer__subtitle {
  margin: 8px 0 0;
  color: #486581;
  line-height: 1.55;
}

.completion-audit-composer__badge {
  flex: 0 0 auto;
  border-radius: 999px;
  background: rgba(15, 118, 110, 0.12);
  color: #0f766e;
  font-size: 0.78rem;
  font-weight: 700;
  padding: 7px 12px;
}

.completion-audit-composer__summary {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12px;
  margin: 16px 0 0;
}

.completion-audit-composer__summary div {
  border: 1px solid rgba(148, 163, 184, 0.16);
  border-radius: 16px;
  background: rgba(255, 255, 255, 0.78);
  padding: 12px 14px;
}

.completion-audit-composer__summary dt {
  color: #64748b;
  font-size: 0.74rem;
  font-weight: 700;
  text-transform: uppercase;
}

.completion-audit-composer__summary dd {
  margin: 6px 0 0;
  color: #102a43;
  font-weight: 700;
}

.completion-audit-composer__upload {
  display: grid;
  grid-template-columns: auto 1fr;
  gap: 10px 12px;
  align-items: center;
  margin-top: 16px;
}

.completion-audit-composer__file {
  position: absolute;
  width: 1px;
  height: 1px;
  padding: 0;
  margin: -1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  border: 0;
}

.completion-audit-composer__select-button,
.completion-audit-composer__submit,
.completion-audit-composer__remove {
  border: 1px solid rgba(15, 118, 110, 0.18);
  border-radius: 14px;
  background: #ffffff;
  color: #0f766e;
  cursor: pointer;
  font-family: "Space Grotesk", "Trebuchet MS", sans-serif;
  font-weight: 700;
  padding: 10px 14px;
}

.completion-audit-composer__select-button:hover,
.completion-audit-composer__remove:hover {
  background: rgba(15, 118, 110, 0.06);
}

.completion-audit-composer__select-button:disabled,
.completion-audit-composer__submit:disabled,
.completion-audit-composer__remove:disabled {
  cursor: not-allowed;
  opacity: 0.65;
}

.completion-audit-composer__hint {
  grid-column: 2;
  margin: 0;
  color: #64748b;
  line-height: 1.45;
}

.completion-audit-composer__preview {
  margin-top: 16px;
  border: 1px solid rgba(148, 163, 184, 0.16);
  border-radius: 18px;
  overflow: hidden;
  background: rgba(255, 255, 255, 0.86);
}

.completion-audit-composer__preview-image {
  display: block;
  width: 100%;
  height: auto;
  max-height: none;
  object-fit: contain;
  background: rgba(241, 245, 249, 0.92);
}

.completion-audit-composer__preview-meta {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 12px 14px;
}

.completion-audit-composer__preview-name {
  color: #102a43;
  font-weight: 700;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.completion-audit-composer__preview-actions {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 10px;
}

.completion-audit-composer__attempt-nav {
  display: flex;
  align-items: center;
  gap: 8px;
}

.completion-audit-composer__attempt-button {
  border: 1px solid rgba(148, 163, 184, 0.22);
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.92);
  color: #0f766e;
  cursor: pointer;
  font: inherit;
  font-weight: 700;
  padding: 7px 12px;
}

.completion-audit-composer__attempt-button:disabled {
  cursor: not-allowed;
  opacity: 0.45;
}

.completion-audit-composer__attempt-count {
  min-width: 42px;
  color: #486581;
  font-size: 0.88rem;
  font-weight: 700;
  text-align: center;
}

.completion-audit-composer__label {
  display: block;
  margin-top: 16px;
  color: #102a43;
  font-size: 0.92rem;
  font-weight: 700;
}

.completion-audit-composer__textarea {
  width: 100%;
  margin-top: 10px;
  border: 1px solid rgba(148, 163, 184, 0.22);
  border-radius: 16px;
  background: rgba(255, 255, 255, 0.92);
  color: #0f172a;
  font: inherit;
  padding: 12px 14px;
  resize: vertical;
}

.completion-audit-composer__actions {
  display: flex;
  justify-content: flex-end;
  margin-top: 14px;
}

.completion-audit-composer__submit {
  background: #0f766e;
  color: #ffffff;
}

.completion-audit-composer__submit:hover {
  background: #115e59;
}

.completion-audit-composer__helper {
  margin: 14px 0 0;
  color: #486581;
  line-height: 1.55;
}

.completion-audit-composer__feedback {
  margin-top: 14px;
  border-top: 1px solid rgba(148, 163, 184, 0.18);
  padding-top: 14px;
}

.completion-audit-composer__feedback-label {
  margin: 0 0 6px;
  color: #0f766e;
  font-size: 0.76rem;
  font-weight: 800;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.completion-audit-composer__attempt-meta {
  margin: 0 0 8px;
  color: #486581;
  font-size: 0.88rem;
  font-weight: 700;
}

.completion-audit-composer__feedback-text {
  margin: 0;
  color: #102a43;
  line-height: 1.6;
}

.completion-audit-composer__error {
  margin: 12px 0 0;
  color: #b91c1c;
  font-weight: 700;
}

@media (max-width: 960px) {
  .completion-audit-composer__summary {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .completion-audit-composer__preview-meta {
    flex-direction: column;
    align-items: flex-start;
  }

  .completion-audit-composer__preview-actions {
    width: 100%;
    justify-content: space-between;
  }
}

@media (max-width: 640px) {
  .completion-audit-composer__header,
  .completion-audit-composer__upload {
    grid-template-columns: 1fr;
    display: grid;
  }

  .completion-audit-composer__badge {
    justify-self: start;
  }

  .completion-audit-composer__hint {
    grid-column: 1;
  }
}
</style>
