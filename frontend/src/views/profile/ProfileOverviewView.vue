<template>
  <div class="profile-view bg-surface text-on-surface min-h-screen flex flex-col">
    <AppHeader
      :is-authenticated="isLoggedIn"
      :avatar-alt="avatarAlt"
      :avatar-href="avatarTarget"
      :avatar-url="avatarUrl"
      :points-label="`${creditsDisplay} pts`"
    />
    <div class="flex flex-1 flex-col">
      <main class="min-w-0 flex-1 overflow-y-auto p-6 md:p-10 pb-24 md:pb-12">
        <div class="mx-auto w-full max-w-5xl">
          <header class="mb-10">
            <h1 class="text-4xl font-headline font-black text-on-background tracking-tighter">Account Overview</h1>
            <p class="text-on-surface-variant mt-2 font-body">
              A lightweight account surface built only from the profile data that CarbonSnap currently exposes.
            </p>
          </header>
          <p
            v-if="!isLoggedIn"
            class="rounded-[2rem] border border-surface-container-high bg-white/80 p-6 text-sm text-on-surface-variant shadow-sm"
          >
            <RouterLink class="font-bold text-primary" to="/login">Sign in</RouterLink>
            to view your account summary and carbon balance.
          </p>
          <template v-else>
            <div class="grid grid-cols-1 md:grid-cols-12 gap-6">
              <section
                class="md:col-span-5 bg-primary text-on-primary rounded-[2rem] p-8 flex flex-col justify-between shadow-2xl relative overflow-hidden group"
                data-profile-hero
              >
                <div class="absolute -right-10 -top-10 w-40 h-40 bg-secondary-fixed/10 rounded-full blur-3xl group-hover:scale-150 transition-transform duration-700"></div>
                <div class="flex items-center gap-4">
                  <button
                    type="button"
                    class="relative w-20 h-20 rounded-2xl bg-white/10 border border-white/10 overflow-hidden flex items-center justify-center text-2xl font-black font-headline group/avatar cursor-pointer shrink-0"
                    :disabled="avatarUploading"
                    :title="avatarUploading ? 'Uploading…' : 'Change avatar'"
                    @click="triggerAvatarUpload"
                  >
                    <img v-if="avatarUrl" :alt="avatarAlt" class="h-full w-full object-cover" :src="avatarUrl" />
                    <span v-else>{{ avatarInitial }}</span>
                    <span class="absolute inset-0 flex items-center justify-center bg-black/40 opacity-0 group-hover/avatar:opacity-100 transition-opacity">
                      <span v-if="avatarUploading" class="material-symbols-outlined text-white text-base animate-spin">progress_activity</span>
                      <span v-else class="material-symbols-outlined text-white text-base">photo_camera</span>
                    </span>
                  </button>
                  <input
                    ref="avatarInput"
                    type="file"
                    accept="image/png,image/jpeg,image/webp,image/gif"
                    class="hidden"
                    @change="handleAvatarChange"
                  />
                  <div class="min-w-0">
                    <p class="font-headline font-bold uppercase tracking-widest text-xs opacity-70 mb-1">Member Profile</p>
                    <h2 class="text-3xl font-headline font-black leading-tight">{{ user?.username || "CarbonSnap member" }}</h2>
                    <p class="text-sm text-on-primary/80 mt-1 break-all">{{ user?.email || "No email available" }}</p>
                  </div>
                </div>
                <p v-if="avatarError" class="mt-3 text-xs text-red-300">{{ avatarError }}</p>
                <p v-if="user?.bio" class="mt-6 text-sm leading-6 text-on-primary/85">
                  {{ user.bio }}
                </p>
                <p v-else class="mt-6 text-sm leading-6 text-on-primary/85">
                  No bio has been added yet.
                </p>
                <div class="mt-8 flex gap-2">
                  <RouterLink class="flex-1 bg-secondary-fixed text-on-secondary-fixed py-3 rounded-xl font-bold hover:scale-105 transition-transform text-center" to="/ledger">
                    Open Ledger
                  </RouterLink>
                  <RouterLink class="flex-1 bg-white/10 text-on-primary py-3 rounded-xl font-bold hover:bg-white/20 transition-colors text-center" to="/notification">
                    Notifications
                  </RouterLink>
                </div>
              </section>
              <section class="md:col-span-7 bg-surface-container-lowest rounded-[2rem] p-8 shadow-sm">
                <h3 class="font-headline font-bold text-xl mb-6">Verified Account Data</h3>
                <dl class="grid gap-4 sm:grid-cols-2">
                  <div class="rounded-2xl bg-surface-container-low p-4">
                    <dt class="text-[10px] font-black uppercase tracking-widest text-outline">Username</dt>
                    <dd class="mt-2 font-bold text-on-surface break-all">{{ user?.username || "CarbonSnap member" }}</dd>
                  </div>
                  <div class="rounded-2xl bg-surface-container-low p-4">
                    <dt class="text-[10px] font-black uppercase tracking-widest text-outline">Email</dt>
                    <dd class="mt-2 font-bold text-on-surface break-all">{{ user?.email || "No email available" }}</dd>
                  </div>
                  <div class="rounded-2xl bg-surface-container-low p-4">
                    <dt class="text-[10px] font-black uppercase tracking-widest text-outline">Joined</dt>
                    <dd class="mt-2 font-bold text-on-surface">{{ formatJoined(user?.created_at) }}</dd>
                  </div>
                  <div class="rounded-2xl bg-surface-container-low p-4">
                    <dt class="text-[10px] font-black uppercase tracking-widest text-outline">Profile</dt>
                    <dd class="mt-2 font-bold text-on-surface">Public-facing account details</dd>
                  </div>
                </dl>
                <div class="mt-6 rounded-2xl bg-surface-container-low p-4" data-profile-bio-summary>
                  <div class="flex flex-wrap items-center justify-between gap-3">
                    <div>
                      <span class="text-[10px] font-black uppercase tracking-widest text-outline">Bio</span>
                      <p class="mt-1 text-sm text-on-surface-variant">
                        {{ user?.bio ? "Bio is visible on your member profile." : "Add a short public profile bio." }}
                      </p>
                    </div>
                    <button class="rounded-full bg-primary px-5 py-3 text-sm font-bold text-on-primary shadow-sm" type="button" data-profile-edit-bio @click="openBioEditor">
                      Edit Bio
                    </button>
                  </div>
                  <p v-if="bioSuccess" class="mt-3 text-sm font-semibold text-primary">{{ bioSuccess }}</p>
                </div>
              </section>
              <div class="md:col-span-4 bg-surface-container-lowest rounded-[2rem] p-6 shadow-sm">
                <span class="text-[10px] font-black uppercase tracking-widest text-secondary">Current Points</span>
                <h4 class="font-headline font-bold text-2xl mt-2">
                  <span v-if="summaryLoading" class="opacity-40">—</span>
                  <span v-else>{{ creditsDisplay }}</span>
                </h4>
                <p class="text-xs text-on-surface-variant mt-2">
                  <span v-if="summaryError">Could not refresh — showing cached value.</span>
                  <span v-else>Live value synced from your ledger.</span>
                </p>
              </div>
              <div class="md:col-span-4 bg-surface-container rounded-[2rem] p-6">
                <span class="text-[10px] font-black uppercase tracking-widest text-secondary">Total Carbon</span>
                <h4 class="font-headline font-bold text-2xl mt-2">
                  <span v-if="summaryLoading" class="opacity-40">—</span>
                  <span v-else>{{ totalCarbonDisplay }}</span>
                </h4>
                <p class="text-xs text-on-surface-variant mt-2">
                  <span v-if="summaryError">Could not refresh — showing cached value.</span>
                  <span v-else>Live value synced from your ledger.</span>
                </p>
              </div>
              <div class="md:col-span-4 bg-tertiary text-on-tertiary rounded-[2rem] p-6 relative overflow-hidden">
                <span class="material-symbols-outlined absolute -right-4 -bottom-4 text-white/10 text-9xl" data-icon="calendar_today">
                  calendar_today
                </span>
                <span class="text-[10px] font-black uppercase tracking-widest text-on-tertiary/80">Joined</span>
                <h4 class="font-headline font-bold text-2xl mt-2">{{ formatJoined(user?.created_at) }}</h4>
                <p class="text-xs text-on-tertiary/80 mt-2">Member since the date stored on your account.</p>
              </div>
            </div>
          </template>
        </div>
      </main>
    </div>
    <div
      v-if="showBioEditor"
      class="fixed inset-0 z-50 flex items-center justify-center px-4 py-6"
      data-profile-bio-modal
    >
      <div
        aria-label="Close bio editor"
        class="absolute inset-0 bg-black/50"
        role="button"
        tabindex="0"
        @click="cancelBioEditor"
        @keyup.enter="cancelBioEditor"
        @keyup.space.prevent="cancelBioEditor"
      ></div>
      <section
        aria-labelledby="profile-bio-modal-title"
        aria-modal="true"
        class="relative z-10 w-full max-w-xl rounded-[2rem] border border-surface-container-high bg-white p-6 shadow-2xl"
        role="dialog"
      >
        <div class="mb-5 flex items-start justify-between gap-4">
          <div>
            <p class="text-[10px] font-black uppercase tracking-widest text-primary">Profile Bio</p>
            <h2 id="profile-bio-modal-title" class="mt-2 text-2xl font-headline font-black text-on-surface">Edit Bio</h2>
            <p class="mt-2 text-sm text-on-surface-variant">Write a short public note about your recycling goals or community work.</p>
          </div>
          <button class="rounded-full border border-outline-variant/30 px-4 py-2 text-sm font-bold text-on-surface-variant hover:bg-surface-container" type="button" @click="cancelBioEditor">
            Close
          </button>
        </div>

        <form class="grid gap-3" data-profile-bio-form @submit.prevent="saveBio">
          <label class="grid gap-2">
            <span class="text-sm font-bold text-on-surface">Bio</span>
            <textarea
              v-model.trim="bioDraft"
              class="min-h-36 rounded-2xl border border-surface-container-high bg-white/80 px-4 py-3 text-sm font-body text-on-surface outline-none focus:border-primary"
              maxlength="500"
              placeholder="Share a short note about your recycling goals or community work."
            ></textarea>
          </label>
          <div class="flex flex-wrap items-center gap-3">
            <button class="rounded-full bg-primary px-5 py-3 text-sm font-bold text-on-primary shadow-sm disabled:opacity-60" type="submit" :disabled="bioSaving">
              {{ bioSaving ? "Saving..." : "Save Bio" }}
            </button>
            <button class="rounded-full border border-outline-variant/30 px-5 py-3 text-sm font-bold text-on-surface-variant hover:bg-surface-container" type="button" :disabled="bioSaving" @click="cancelBioEditor">
              Cancel
            </button>
            <span class="text-xs text-on-surface-variant">{{ bioDraft.length }}/500</span>
          </div>
          <p v-if="bioError" class="text-sm font-semibold text-error">{{ bioError }}</p>
        </form>
      </section>
    </div>
    <nav class="fixed bottom-0 left-0 w-full z-50 flex justify-around items-end px-4 pb-4 md:hidden bg-[#f3f7f5]/80 backdrop-blur-lg">
      <RouterLink class="flex flex-col items-center justify-center text-[#585c5b] p-2" to="/ledger">
        <span class="material-symbols-outlined">receipt_long</span>
        <span class="font-['Manrope'] text-[10px] font-bold uppercase tracking-widest mt-1">Ledger</span>
      </RouterLink>
      <RouterLink class="flex flex-col items-center justify-center text-[#585c5b] p-2" to="/project">
        <span class="material-symbols-outlined">assignment</span>
        <span class="font-['Manrope'] text-[10px] font-bold uppercase tracking-widest mt-1">Projects</span>
      </RouterLink>
      <RouterLink class="flex flex-col items-center justify-center bg-[#b9f600] text-[#324600] rounded-full p-3 mb-2 scale-110 shadow-lg" to="/ai">
        <span class="material-symbols-outlined">photo_camera</span>
      </RouterLink>
      <RouterLink class="flex flex-col items-center justify-center text-[#585c5b] p-2" to="/forum">
        <span class="material-symbols-outlined">groups</span>
        <span class="font-['Manrope'] text-[10px] font-bold uppercase tracking-widest mt-1">Forum</span>
      </RouterLink>
      <RouterLink class="flex flex-col items-center justify-center text-[#585c5b] p-2" to="/market">
        <span class="material-symbols-outlined">storefront</span>
        <span class="font-['Manrope'] text-[10px] font-bold uppercase tracking-widest mt-1">Market</span>
      </RouterLink>
    </nav>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from "vue";
import { RouterLink } from "vue-router";

import AppHeader from "../../components/common/AppHeader.vue";
import { updateAvatar, updateProfile } from "../../api/auth/auth.js";
import { resolveBackendUrl } from "../../api/http.js";
import { fetchLedgerSummary } from "../../api/ledger/ledger.js";
import { useAuth } from "../../composables/useAuth.js";
import { showErrorToast, showSuccessToast } from "../../composables/useToast.js";

const { isLoggedIn, user, token, updateUser, refreshCurrentUser } = useAuth();

const avatarInput = ref(null);
const avatarUploading = ref(false);
const avatarError = ref("");
const bioDraft = ref("");
const bioSaving = ref(false);
const bioError = ref("");
const bioSuccess = ref("");
const showBioEditor = ref(false);

function triggerAvatarUpload() {
  avatarInput.value?.click();
}

async function handleAvatarChange(event) {
  const file = event.target.files?.[0];
  if (!file) return;

  avatarUploading.value = true;
  avatarError.value = "";

  try {
    const dataUrl = await readFileAsDataUrl(file);
    const result = await updateAvatar(dataUrl, token.value);
    updateUser({ avatar_url: result.avatar_url });
    showSuccessToast("Avatar updated", "Your profile photo has been saved.");
  } catch (err) {
    avatarError.value = err.message || "Upload failed.";
    showErrorToast("Avatar upload failed", avatarError.value);
  } finally {
    avatarUploading.value = false;
    event.target.value = "";
  }
}

function readFileAsDataUrl(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(reader.result);
    reader.onerror = () => reject(new Error("Could not read file."));
    reader.readAsDataURL(file);
  });
}

function openBioEditor() {
  bioDraft.value = user.value?.bio || "";
  bioError.value = "";
  bioSuccess.value = "";
  showBioEditor.value = true;
}

function cancelBioEditor() {
  if (bioSaving.value) {
    return;
  }

  showBioEditor.value = false;
  bioError.value = "";
  bioDraft.value = user.value?.bio || "";
}

const summaryLoading = ref(false);
const summaryError = ref(false);
const realtimePoints = ref(null);
const realtimeCarbon = ref(null);

onMounted(async () => {
  if (!isLoggedIn.value) return;
  await refreshCurrentUser().catch(() => {});
  bioDraft.value = user.value?.bio || "";
  summaryLoading.value = true;
  summaryError.value = false;
  try {
    const data = await fetchLedgerSummary(token.value);
    realtimePoints.value = data.current_points ?? null;
    realtimeCarbon.value = data.total_carbon_amount ?? null;
    updateUser({ current_points: data.current_points, total_carbon_amount: data.total_carbon_amount });
  } catch {
    summaryError.value = true;
  } finally {
    summaryLoading.value = false;
  }
});

async function saveBio() {
  bioSaving.value = true;
  bioError.value = "";
  bioSuccess.value = "";
  try {
    const result = await updateProfile({ bio: bioDraft.value }, token.value);
    const nextUser = result.user || result;
    updateUser({ bio: nextUser.bio || "" });
    bioDraft.value = nextUser.bio || "";
    bioSuccess.value = "Bio saved.";
    showBioEditor.value = false;
    showSuccessToast("Bio saved", "Your profile bio has been updated.");
  } catch (err) {
    bioError.value = err.message || "Failed to save bio.";
    showErrorToast("Bio update failed", bioError.value);
  } finally {
    bioSaving.value = false;
  }
}

const avatarAlt = computed(() => user.value?.username || "User Profile");
const rawAvatarUrl = computed(() => user.value?.avatar_url || "");
const avatarUrl = computed(() => resolveBackendUrl(rawAvatarUrl.value));
const avatarInitial = computed(() => (avatarAlt.value ? avatarAlt.value.charAt(0).toUpperCase() : "U"));
const avatarTarget = computed(() => (isLoggedIn.value ? "/profile" : "/login"));
const creditsDisplay = computed(() => formatNumber(realtimePoints.value ?? user.value?.current_points ?? 0));
const totalCarbonDisplay = computed(() => formatKg(realtimeCarbon.value ?? user.value?.total_carbon_amount ?? 0));

function formatNumber(value) {
  const parsed = Number(value);
  if (Number.isNaN(parsed)) {
    return "0";
  }
  return parsed.toLocaleString();
}

function formatKg(value) {
  const parsed = Number(value);
  if (Number.isNaN(parsed)) {
    return "0.00 kg";
  }
  return `${parsed.toFixed(2)} kg`;
}

function formatJoined(value) {
  if (!value) {
    return "Unknown";
  }
  const parsed = new Date(value);
  return Number.isNaN(parsed.getTime()) ? "Unknown" : parsed.toLocaleDateString();
}
</script>

<style scoped src="../../styles/views/profile-view.css"></style>

