<template>
  <AppLayout
    :is-authenticated="isLoggedIn"
    :avatar-alt="avatarAlt"
    :avatar-url="avatarUrl"
    :show-sidebar="false"
    :user="user"
  >
    <section class="project-detail-page">
      <div class="project-detail__back">
        <RouterLink to="/project">Back to projects</RouterLink>
      </div>

      <p v-if="loading" class="panel">Loading project...</p>
      <p v-else-if="error" class="panel error">{{ error }}</p>

      <div v-else-if="project" class="project-detail__grid">
        <article class="panel project-story">
          <div v-if="project.cover_image_url" class="project-story__cover">
            <button class="project-image-preview-trigger" type="button" data-project-detail-cover-preview @click="imagePreviewOpen = true">
              <img :src="project.cover_image_url" :alt="project.title" />
            </button>
          </div>
          <div class="project-story__header">
            <span class="project-badge" :class="statusClass(project)">
              {{ project.is_expired && project.status !== "completed" ? "Expired" : project.status }}
            </span>
            <p class="project-story__eyebrow">Created by {{ project.creator_username }}</p>
            <h1>{{ project.title }}</h1>
            <p class="subtitle">
              Deadline {{ formatDate(project.deadline_at) }} · {{ project.days_left }} day<span v-if="project.days_left !== 1">s</span> left
            </p>
          </div>

          <div class="project-story__body">
            <p style="white-space: pre-wrap">{{ project.description || "No description yet." }}</p>
          </div>

          <section class="project-story__section">
            <h2>Recent support</h2>
            <p v-if="project.recent_contributions?.length === 0" class="subtitle">
              No contributions yet. Be the first supporter.
            </p>
            <ul v-else class="project-contribution-list">
              <li
                v-for="entry in project.recent_contributions"
                :key="entry.id"
                class="project-contribution-list__item"
              >
                <div>
                  <strong>{{ entry.contributor_username }}</strong>
                  <p>{{ formatDate(entry.created_at) }}</p>
                </div>
                <span>{{ entry.points }} pts</span>
              </li>
            </ul>
          </section>
        </article>

        <aside class="panel project-funding">
          <div class="project-funding__summary">
            <p class="project-funding__eyebrow">Funding progress</p>
            <h2>{{ project.points_raised }} / {{ project.points_target }} pts</h2>
            <p class="subtitle">{{ project.points_remaining }} points remaining to reach the target.</p>
          </div>

          <div class="project-progress">
            <div class="project-progress__track">
              <span class="project-progress__fill" :style="{ width: `${progressPercent(project)}%` }"></span>
            </div>
            <div class="project-progress__meta">
              <strong>{{ progressPercent(project) }}% funded</strong>
              <span>{{ project.contributor_count }} supporters</span>
            </div>
          </div>

          <dl class="project-funding__facts">
            <div>
              <dt>Status</dt>
              <dd>{{ project.status }}</dd>
            </div>
            <div>
              <dt>Contributions</dt>
              <dd>{{ project.contribution_count }}</dd>
            </div>
            <div>
              <dt>Your balance</dt>
              <dd>{{ user?.current_points ?? 0 }} pts</dd>
            </div>
          </dl>

          <div class="project-funding__box">
            <p class="project-funding__eyebrow">Support this project</p>
            <div class="project-quick-points">
              <button
                v-for="preset in quickPresets"
                :key="preset"
                type="button"
                class="project-quick-points__btn"
                @click="contributionPoints = preset"
              >
                {{ preset }} pts
              </button>
            </div>

            <label class="project-form__field">
              <span>Custom contribution</span>
              <input v-model.number="contributionPoints" type="number" min="1" step="1" />
            </label>

            <p v-if="actionError" class="error">{{ actionError }}</p>
            <p v-if="actionOk" class="project-feedback project-feedback--success">{{ actionOk }}</p>

            <button type="button" class="project-btn project-btn--block" :disabled="busy || !canContribute" @click="submitContribution">
              {{ busy ? "Contributing..." : contributionCta }}
            </button>
            <p v-if="!isLoggedIn" class="subtitle">Sign in to contribute points.</p>
          </div>
        </aside>
      </div>

      <ImagePreviewModal
        v-if="imagePreviewOpen"
        :images="[project.cover_image_url]"
        :title="project.title"
        @close="imagePreviewOpen = false"
      />
    </section>
  </AppLayout>
</template>

<script setup>
import { computed, onMounted, ref } from "vue";
import { RouterLink, useRoute, useRouter } from "vue-router";

import { fetchCurrentUser } from "../../api/auth/auth.js";
import { contributeToProject, fetchProject } from "../../api/project/project.js";
import ImagePreviewModal from "../../components/common/ImagePreviewModal.vue";
import AppLayout from "../../layouts/AppLayout.vue";
import { useAuth } from "../../composables/useAuth.js";
import { showErrorToast, showSuccessToast } from "../../composables/useToast.js";

const route = useRoute();
const router = useRouter();
const { isLoggedIn, token, user } = useAuth();

const project = ref(null);
const loading = ref(false);
const error = ref("");
const busy = ref(false);
const actionError = ref("");
const actionOk = ref("");
const contributionPoints = ref(25);
const imagePreviewOpen = ref(false);
const quickPresets = [10, 25, 50, 100];

const avatarAlt = computed(() => user.value?.username || "User");
const avatarUrl = computed(() => user.value?.avatar_url || "");

const canContribute = computed(() => {
  if (!isLoggedIn.value || !project.value || busy.value) {
    return false;
  }
  if (project.value.status === "completed" || project.value.is_expired) {
    return false;
  }
  return Number.isInteger(Number(contributionPoints.value)) && Number(contributionPoints.value) > 0;
});

const contributionCta = computed(() => {
  if (!project.value) {
    return "Contribute points";
  }
  if (project.value.status === "completed") {
    return "Project funded";
  }
  if (project.value.is_expired) {
    return "Campaign closed";
  }
  return "Contribute points";
});

function progressPercent(entry) {
  return Math.max(0, Math.min(100, Math.round((entry.progress_ratio || 0) * 100)));
}

function statusClass(entry) {
  if (entry.status === "completed") {
    return "project-badge--completed";
  }
  if (entry.is_expired) {
    return "project-badge--expired";
  }
  return "project-badge--fundraising";
}

function formatDate(value) {
  if (!value) {
    return "Unknown";
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  return new Intl.DateTimeFormat("en-US", {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  }).format(date);
}

async function loadProject() {
  loading.value = true;
  error.value = "";
  try {
    project.value = await fetchProject(route.params.id, token.value || undefined);
  } catch (err) {
    error.value = err instanceof Error ? err.message : "Failed to load project.";
  } finally {
    loading.value = false;
  }
}

async function syncCurrentUser() {
  if (!token.value) {
    return;
  }
  try {
    const data = await fetchCurrentUser(token.value);
    user.value = data.user;
    localStorage.setItem("cs_user", JSON.stringify(data.user));
  } catch {
    // Keep page usable even if auth refresh fails.
  }
}

async function submitContribution() {
  actionError.value = "";
  actionOk.value = "";
  if (!isLoggedIn.value) {
    router.push("/login");
    return;
  }
  if (!project.value) {
    return;
  }
  busy.value = true;
  try {
    const result = await contributeToProject(
      project.value.id,
      { points: Number(contributionPoints.value) },
      token.value,
    );
    project.value = result.project;
    actionOk.value = `Thanks for backing this project with ${result.contribution.points} points.`;
    showSuccessToast("Contribution sent", `You backed this project with ${result.contribution.points} points.`);
    if (user.value) {
      user.value = { ...user.value, current_points: result.viewer_current_points };
      localStorage.setItem("cs_user", JSON.stringify(user.value));
    } else {
      await syncCurrentUser();
    }
  } catch (err) {
    actionError.value = err instanceof Error ? err.message : "Contribution failed.";
    showErrorToast("Contribution failed", actionError.value);
  } finally {
    busy.value = false;
  }
}

onMounted(() => {
  loadProject();
});
</script>

<style scoped src="../../styles/views/project-view.css"></style>
