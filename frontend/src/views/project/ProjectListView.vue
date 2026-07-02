<template>
  <AppLayout
    :is-authenticated="isLoggedIn"
    :avatar-alt="avatarAlt"
    :avatar-url="avatarUrl"
    :show-sidebar="false"
    :user="user"
  >
    <section class="project-page">
      <header class="project-hero panel">
        <div class="project-hero__copy">
          <p class="project-hero__eyebrow">{{ t("nav.projects") }}</p>
          <h1>{{ t("project.heroTitle") }}</h1>
          <p class="subtitle">
            {{ t("project.heroSubtitle") }}
          </p>
        </div>

        <div class="project-hero__stats">
          <article class="project-stat">
            <span>{{ t("project.fundraising") }}</span>
            <strong>{{ summary.fundraisingCount }}</strong>
          </article>
          <article class="project-stat">
            <span>{{ t("project.completed") }}</span>
            <strong>{{ summary.completedCount }}</strong>
          </article>
          <article class="project-stat">
            <span>{{ t("project.pointsRaised") }}</span>
            <strong>{{ summary.pointsRaisedTotal }}</strong>
          </article>
          <article v-if="isLoggedIn" class="project-stat">
            <span>{{ t("project.balance") }}</span>
            <strong>{{ user?.current_points ?? 0 }}</strong>
          </article>
        </div>

        <div class="project-hero__actions">
          <button type="button" class="project-btn project-btn--ghost" @click="loadFirstPage">
            {{ t("project.refresh") }}
          </button>
          <button type="button" class="project-btn" @click="handleStartProjectClick">
            {{ t("project.startProject") }}
          </button>
        </div>
      </header>

      <p v-if="loading" class="panel">{{ t("project.loading") }}</p>
      <p v-else-if="error" class="panel error">{{ error }}</p>
      <p v-else-if="projects.length === 0" class="panel">{{ t("project.noProjects") }}</p>

      <div v-else class="project-grid">
        <article v-for="project in projects" :key="project.id" class="project-card">
          <div v-if="project.cover_image_url" class="project-card__cover">
            <button class="project-image-preview-trigger" type="button" :aria-label="`Preview ${project.title} cover image`" data-project-cover-preview-trigger @click="openProjectImagePreview(project)">
              <img :src="project.cover_image_url" :alt="project.title" />
            </button>
          </div>
          <div class="project-card__header">
            <span class="project-badge" :class="statusClass(project)">
              {{ statusLabel(project) }}
            </span>
            <span class="project-card__days">
              {{ daysLeftLabel(project.days_left) }}
            </span>
          </div>

          <RouterLink class="project-card__title-link" :to="`/project/${project.id}`">
            <h2>{{ project.title }}</h2>
          </RouterLink>

          <p class="project-card__description">{{ summarize(project.description) }}</p>

          <div class="project-progress">
            <div class="project-progress__track">
              <span class="project-progress__fill" :style="{ width: `${progressPercent(project)}%` }"></span>
            </div>
            <div class="project-progress__meta">
              <strong>{{ project.points_raised }} / {{ project.points_target }} pts</strong>
              <span>{{ progressPercent(project) }}%</span>
            </div>
          </div>

          <dl class="project-card__meta">
            <div>
              <dt>{{ t("project.creator") }}</dt>
              <dd>{{ project.creator_username }}</dd>
            </div>
            <div>
              <dt>{{ t("project.supporters") }}</dt>
              <dd>{{ project.contributor_count }}</dd>
            </div>
            <div>
              <dt>{{ t("project.contributions") }}</dt>
              <dd>{{ project.contribution_count }}</dd>
            </div>
            <div>
              <dt>{{ t("project.remaining") }}</dt>
              <dd>{{ project.points_remaining }} pts</dd>
            </div>
          </dl>

          <div class="project-card__actions">
            <RouterLink class="project-btn project-btn--small" :to="`/project/${project.id}`">
              {{ t("project.viewProject") }}
            </RouterLink>
          </div>
        </article>
      </div>

      <div v-if="!loading && totalPages > 1" class="project-pagination">
        <button type="button" class="project-btn project-btn--ghost project-btn--icon" :disabled="!hasPrev" @click="prevPage">
          <span class="material-symbols-outlined">chevron_left</span>
        </button>
        <template v-for="item in pageItems" :key="item.key">
          <span v-if="item.ellipsis" class="project-pagination__ellipsis">…</span>
          <button
            v-else
            type="button"
            class="project-btn project-btn--ghost project-btn--page"
            :class="{ 'project-btn--active': item.p === page }"
            @click="goToPage(item.p)"
          >
            {{ item.p }}
          </button>
        </template>
        <button type="button" class="project-btn project-btn--ghost project-btn--icon" :disabled="!hasNext" @click="nextPage">
          <span class="material-symbols-outlined">chevron_right</span>
        </button>
      </div>

      <div
        v-if="showComposer"
        class="project-composer-window"
        data-project-composer-window
      >
        <div
          aria-label="Close project composer"
          class="project-composer-window__scrim"
          role="button"
          tabindex="0"
          @click="cancelComposer"
          @keyup.enter="cancelComposer"
          @keyup.space.prevent="cancelComposer"
        ></div>
        <section
          aria-labelledby="project-composer-title"
          aria-modal="true"
          class="panel project-composer project-composer--modal"
          data-project-composer
          role="dialog"
        >
          <div class="project-composer__header">
            <div>
              <p class="project-hero__eyebrow">{{ t("project.startProject") }}</p>
              <h2 id="project-composer-title">{{ t("project.launch") }}</h2>
              <p class="subtitle">{{ t("project.composerSubtitle") }}</p>
            </div>
            <button type="button" class="project-btn project-btn--ghost" @click="cancelComposer">
              {{ t("project.cancel") }}
            </button>
          </div>

          <form class="project-form" @submit.prevent="submitProject">
            <label class="project-form__field">
              <span>{{ t("project.title") }}</span>
              <input
                v-model.trim="draft.title"
                type="text"
                maxlength="200"
                :placeholder="t('project.titlePlaceholder')"
                required
              />
            </label>

            <label class="project-form__field">
              <span>{{ t("project.description") }}</span>
              <textarea
                v-model.trim="draft.description"
                rows="6"
                :placeholder="t('project.descriptionPlaceholder')"
                required
              ></textarea>
            </label>

            <div class="project-form__field">
              <span>{{ t("project.coverImage") }} <em class="project-form__optional">({{ t("project.optional") }})</em></span>
              <div class="project-cover-upload">
                <div v-if="coverImagePreview" class="project-cover-upload__preview">
                  <img :src="coverImagePreview" :alt="t('project.coverPreview')" />
                  <button type="button" class="project-cover-upload__remove" @click="removeCoverImage">
                    <span class="material-symbols-outlined">close</span>
                  </button>
                  <span v-if="coverImageUploading" class="project-cover-upload__status">{{ t("project.uploading") }}</span>
                </div>
                <label v-else class="project-cover-upload__trigger">
                  <span>{{ coverImageUploading ? t("project.uploading") : t("project.chooseImage") }}</span>
                  <input
                    type="file"
                    accept="image/*"
                    :disabled="coverImageUploading"
                    style="display: none"
                    @change="handleCoverImageChange"
                  />
                </label>
              </div>
            </div>

            <div class="project-form__row">
              <label class="project-form__field">
                <span>{{ t("project.pointsTarget") }}</span>
                <input v-model.number="draft.pointsTarget" type="number" min="1" required />
              </label>
            </div>

            <fieldset class="project-form__field project-deadline-fields">
              <legend>{{ t("project.deadline") }}</legend>
              <div class="project-form__row project-form__row--deadline">
                <label class="project-form__deadline-date">
                  <span>Date</span>
                  <input v-model="deadline.date" type="date" :min="minDeadlineDate" required />
                </label>
                <label>
                  <span>Time</span>
                  <input v-model="deadline.time" type="time" required />
                </label>
              </div>
            </fieldset>

            <p v-if="composerError" class="error">{{ composerError }}</p>

            <div class="project-hero__actions">
              <button type="submit" class="project-btn" :disabled="composerBusy || coverImageUploading">
                {{ composerBusy ? t("project.publishing") : t("project.publish") }}
              </button>
              <button type="button" class="project-btn project-btn--ghost" :disabled="composerBusy" @click="cancelComposer">
                {{ t("project.cancel") }}
              </button>
            </div>
          </form>
        </section>
      </div>

      <ImagePreviewModal
        v-if="imagePreviewOpen"
        :images="imagePreviewImages"
        :initial-index="0"
        :title="imagePreviewTitle"
        @close="imagePreviewOpen = false"
      />
    </section>
  </AppLayout>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from "vue";
import { RouterLink, useRouter } from "vue-router";

import { createProject, fetchProjects, uploadProjectImage } from "../../api/project/project.js";
import ImagePreviewModal from "../../components/common/ImagePreviewModal.vue";
import AppLayout from "../../layouts/AppLayout.vue";
import { useAuth } from "../../composables/useAuth.js";
import { showErrorToast, showSuccessToast } from "../../composables/useToast.js";
import { useI18n } from "../../i18n/index.js";

const router = useRouter();
const { isLoggedIn, token, user } = useAuth();
const { t } = useI18n();

const PER_PAGE = 12;
const defaultDeadline = () => {
  const now = new Date();
  return new Date(now.getFullYear(), now.getMonth(), now.getDate() + 7, 18, 0, 0);
};

function formatDateInput(date) {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

const projects = ref([]);
const page = ref(1);
const total = ref(0);
const loading = ref(false);
const error = ref("");
const showComposer = ref(false);
const coverImagePreview = ref(null);
const coverImageUploading = ref(false);
const composerBusy = ref(false);
const composerError = ref("");
const imagePreviewOpen = ref(false);
const imagePreviewImages = ref([]);
const imagePreviewTitle = ref("");
const summary = reactive({
  fundraisingCount: 0,
  completedCount: 0,
  pointsRaisedTotal: 0,
});
const draft = reactive({
  title: "",
  description: "",
  coverImageUrl: null,
  pointsTarget: 200,
});
const deadline = reactive({
  date: formatDateInput(defaultDeadline()),
  time: "18:00",
});

const avatarAlt = computed(() => user.value?.username || "User");
const avatarUrl = computed(() => user.value?.avatar_url || "");
const totalPages = computed(() => Math.max(1, Math.ceil(total.value / PER_PAGE)));
const hasPrev = computed(() => page.value > 1);
const hasNext = computed(() => page.value < totalPages.value);
const minDeadlineDate = computed(() => formatDateInput(new Date()));

const pageItems = computed(() => {
  const tp = totalPages.value;
  const cur = page.value;
  const items = [];
  if (tp <= 7) {
    for (let i = 1; i <= tp; i++) items.push({ key: i, p: i, ellipsis: false });
    return items;
  }
  const pushPage = (p) => items.push({ key: p, p, ellipsis: false });
  const pushEllipsis = (key) => items.push({ key, p: null, ellipsis: true });
  pushPage(1);
  if (cur > 3) pushEllipsis("e1");
  const start = Math.max(2, cur - 1);
  const end = Math.min(tp - 1, cur + 1);
  for (let i = start; i <= end; i++) pushPage(i);
  if (cur < tp - 2) pushEllipsis("e2");
  pushPage(tp);
  return items;
});

function summarize(value) {
  if (!value) {
    return t("project.noDescription");
  }
  return value.length > 180 ? `${value.slice(0, 180)}...` : value;
}

function daysLeftLabel(count) {
  return t(count === 1 ? "project.dayLeft" : "project.daysLeft", { count });
}

function statusLabel(project) {
  if (project.is_expired && project.status !== "completed") {
    return t("project.expired");
  }
  if (project.status === "completed") {
    return t("project.completed");
  }
  if (project.status === "fundraising") {
    return t("project.fundraising");
  }
  return project.status;
}

function progressPercent(project) {
  return Math.max(0, Math.min(100, Math.round((project.progress_ratio || 0) * 100)));
}

function statusClass(project) {
  if (project.status === "completed") {
    return "project-badge--completed";
  }
  if (project.is_expired) {
    return "project-badge--expired";
  }
  return "project-badge--fundraising";
}

function updateSummary(payload) {
  summary.fundraisingCount = payload?.fundraising_count ?? 0;
  summary.completedCount = payload?.completed_count ?? 0;
  summary.pointsRaisedTotal = payload?.points_raised_total ?? 0;
}

function requireLogin() {
  if (isLoggedIn.value) {
    return true;
  }

  router.push({ name: "login", query: { redirect: "/project" } });
  return false;
}

function resetDeadline() {
  const nextDeadline = defaultDeadline();
  deadline.date = formatDateInput(nextDeadline);
  deadline.time = "18:00";
}

function resetDraft() {
  draft.title = "";
  draft.description = "";
  draft.coverImageUrl = null;
  draft.pointsTarget = 200;
  coverImagePreview.value = null;
  coverImageUploading.value = false;
  composerError.value = "";
  resetDeadline();
}

function handleStartProjectClick() {
  if (!requireLogin()) {
    return;
  }

  composerError.value = "";
  showComposer.value = true;
}

function cancelComposer() {
  if (composerBusy.value) {
    return;
  }

  showComposer.value = false;
  resetDraft();
}

function buildDeadlineIso() {
  const [hourText, minuteText] = String(deadline.time || "").split(":");
  const [yearText, monthText, dayText] = String(deadline.date || "").split("-");
  const date = new Date(
    Number(yearText),
    Number(monthText) - 1,
    Number(dayText),
    Number(hourText),
    Number(minuteText),
    0,
  );

  if (
    Number.isNaN(date.getTime()) ||
    date.getMonth() !== Number(monthText) - 1 ||
    date.getDate() !== Number(dayText) ||
    date.getFullYear() !== Number(yearText)
  ) {
    throw new Error(t("project.errorDeadline"));
  }
  return date.toISOString();
}

async function handleCoverImageChange(event) {
  const file = event.target.files?.[0];
  if (!file) {
    return;
  }

  const reader = new FileReader();
  reader.onload = async (e) => {
    const dataUrl = String(e.target?.result || "");
    coverImagePreview.value = dataUrl;
    coverImageUploading.value = true;
    composerError.value = "";
    try {
      const result = await uploadProjectImage(dataUrl, token.value);
      draft.coverImageUrl = result.url;
    } catch (err) {
      composerError.value = err instanceof Error ? err.message : t("project.errorImageUpload");
      draft.coverImageUrl = null;
      coverImagePreview.value = null;
    } finally {
      coverImageUploading.value = false;
    }
  };
  reader.readAsDataURL(file);
}

function removeCoverImage() {
  draft.coverImageUrl = null;
  coverImagePreview.value = null;
}

function openProjectImagePreview(project) {
  imagePreviewImages.value = [project.cover_image_url].filter(Boolean);
  imagePreviewTitle.value = project.title || "Project image";
  imagePreviewOpen.value = imagePreviewImages.value.length > 0;
}

async function submitProject() {
  composerError.value = "";
  if (!requireLogin()) {
    return;
  }

  composerBusy.value = true;
  try {
    await createProject(
      {
        title: draft.title,
        description: draft.description,
        coverImageUrl: draft.coverImageUrl || null,
        pointsTarget: draft.pointsTarget,
        deadlineAt: buildDeadlineIso(),
      },
      token.value,
    );
    showComposer.value = false;
    resetDraft();
    showSuccessToast("Project started", "Your community project is now listed.");
    await loadFirstPage();
  } catch (err) {
    composerError.value = err instanceof Error ? err.message : t("project.errorCreate");
    showErrorToast("Project failed", composerError.value);
  } finally {
    composerBusy.value = false;
  }
}

async function loadPage(targetPage) {
  loading.value = true;
  error.value = "";
  try {
    const data = await fetchProjects({ page: targetPage, perPage: PER_PAGE, token: token.value || undefined });
    projects.value = data.items || [];
    total.value = data.total ?? projects.value.length;
    page.value = targetPage;
    updateSummary(data.summary);
  } catch (err) {
    error.value = err instanceof Error ? err.message : t("project.errorLoad");
  } finally {
    loading.value = false;
  }
}

async function loadFirstPage() {
  await loadPage(1);
  window.scrollTo({ top: 0, behavior: "smooth" });
}

function goToPage(targetPage) {
  if (targetPage < 1 || targetPage > totalPages.value) return;
  loadPage(targetPage);
  window.scrollTo({ top: 0, behavior: "smooth" });
}

function prevPage() {
  goToPage(page.value - 1);
}

function nextPage() {
  goToPage(page.value + 1);
}

onMounted(() => {
  loadPage(1);
});
</script>

<style scoped src="../../styles/views/project-view.css"></style>
