<template>
  <div class="forum-shell min-h-screen bg-surface font-body text-on-surface antialiased">
    <AppHeader
      :is-authenticated="isLoggedIn"
      :avatar-alt="avatarAlt"
      avatar-href="/profile"
      :avatar-url="avatarUrl"
      :points-label="pointsLabel"
      position-mode="static"
    />

    <main class="forum-shell__content">
      <section class="forum-page bg-surface text-on-surface" data-forum-page>
        <div class="flex gap-8 pb-6">
        <section class="min-w-0 flex-1 space-y-8" data-forum-feed>
          <div class="flex flex-col gap-6">
            <div class="flex items-end justify-between gap-4">
              <div class="min-w-0">
                <h1 class="text-3xl font-black tracking-tight text-on-surface">Community Feed</h1>
                <div class="mt-2 hidden items-center gap-2 text-sm font-medium text-on-surface-variant sm:flex">
                  <span class="material-symbols-outlined text-lg">filter_list</span>
                  <span>Sorted by: Most Impactful</span>
                </div>
              </div>

              <button
                class="inline-flex items-center gap-2 rounded-full bg-surface-container px-4 py-2 text-sm font-bold text-on-surface-variant shadow-sm transition-colors hover:bg-surface-container-high"
                type="button"
                @click="goToPage(1)"
              >
                <span class="material-symbols-outlined text-lg">refresh</span>
                Refresh
              </button>
            </div>

            <div class="scrollbar-hide flex gap-2 overflow-x-auto pb-2">
              <button
                v-for="filter in feedFilters"
                :key="filter.key"
                class="whitespace-nowrap rounded-full px-6 py-2 text-sm font-bold transition-colors"
                :class="activeFilter === filter.key ? 'bg-primary text-on-primary shadow-md' : 'bg-surface-container text-on-surface-variant hover:bg-surface-container-high'"
                type="button"
                @click="setActiveFilter(filter.key)"
              >
                {{ filter.label }}
              </button>
            </div>
          </div>

          <p v-if="submitSuccess" class="rounded-3xl bg-surface-container-lowest px-6 py-4 text-sm font-bold text-primary shadow-sm">{{ submitSuccess }}</p>
          <p v-if="loading" class="rounded-3xl bg-surface-container-lowest px-6 py-4 shadow-sm">Loading posts...</p>
          <p v-else-if="error" class="rounded-3xl bg-surface-container-lowest px-6 py-4 text-error shadow-sm">{{ error }}</p>
          <div v-else-if="filteredPosts.length === 0" class="rounded-3xl bg-surface-container-lowest px-6 py-12 shadow-sm">
            <p class="text-[10px] font-black uppercase tracking-[0.22em] text-primary">Empty Feed</p>
            <h2 class="mt-3 text-2xl font-black text-on-surface">No posts yet</h2>
            <p class="mt-2 max-w-xl text-sm text-on-surface-variant">When the first community stories arrive, they will appear here in this Stitch forum layout.</p>
            <button class="mt-6 rounded-full bg-primary px-5 py-3 text-sm font-bold text-on-primary shadow-md" type="button" @click="handleAddPostClick">
              Create the first post
            </button>
          </div>

          <div v-else class="grid grid-cols-1 gap-6">
            <article
              v-if="featuredPost"
              class="group cursor-pointer overflow-hidden rounded-3xl bg-surface-container-lowest shadow-[0_8px_32px_rgba(43,48,47,0.04)]"
              data-forum-featured-post
              role="link"
              tabindex="0"
              @click="openPostDetail(featuredPost.id)"
              @keyup.enter="openPostDetail(featuredPost.id)"
            >
              <div class="flex flex-col lg:flex-row">
                <div class="relative h-64 overflow-hidden lg:h-auto lg:w-1/2">
                  <img v-if="featuredImageUrl" :alt="`${featuredPost.title} preview image`" class="h-full w-full object-cover transition-transform duration-700 group-hover:scale-105" :src="featuredImageUrl" />
                  <div v-else class="flex h-full min-h-64 w-full items-center justify-center bg-gradient-to-br from-surface-container-high to-surface-container-low">
                    <div class="text-center">
                      <p class="text-xs font-black uppercase tracking-[0.2em] text-primary">Verified story</p>
                      <p class="mt-2 text-2xl font-black text-on-surface">{{ authorInitials(featuredPost) }}</p>
                    </div>
                  </div>
                </div>

                <div class="flex flex-col justify-between p-8 lg:w-1/2">
                  <div>
                    <div class="mb-4 flex items-start justify-between">
                      <div class="flex items-center gap-3">
                        <div class="flex h-10 w-10 items-center justify-center overflow-hidden rounded-full bg-tertiary-container font-black text-on-tertiary-container">
                          <span>{{ authorInitials(featuredPost) }}</span>
                        </div>
                        <div>
                          <p class="font-bold text-on-surface">{{ authorLabel(featuredPost) }}</p>
                          <span class="rounded-md bg-primary-container px-2 py-0.5 text-[10px] font-bold uppercase tracking-tight text-on-primary-container">{{ authorBadge(featuredPost) }}</span>
                        </div>
                      </div>
                      <span class="text-xs text-on-surface-variant">{{ formatDate(featuredPost.created_at) }}</span>
                    </div>

                    <h3 class="mb-3 text-2xl font-bold leading-tight text-primary">{{ featuredPost.title }}</h3>
                    <p class="mb-6 font-body leading-relaxed text-on-surface-variant">{{ summarize(featuredPost.content, 220) }}</p>
                  </div>

                  <div class="mt-8 flex items-center justify-between">
                    <div class="flex -space-x-2">
                      <div class="flex h-8 w-8 items-center justify-center rounded-full border-2 border-surface-container-lowest bg-surface-container-high text-[10px] font-bold">+{{ Math.max(0, secondaryPosts.length) }}</div>
                      <div v-for="post in avatarStackPosts" :key="`featured-avatar-${post.id}`" class="flex h-8 w-8 items-center justify-center overflow-hidden rounded-full border-2 border-surface-container-lowest bg-surface-container-high text-[10px] font-bold">
                        <img
                          v-if="post?.author_avatar_url"
                          :src="post.author_avatar_url"
                          :alt="`${authorLabel(post)} avatar`"
                          class="h-full w-full object-cover"
                        />
                        <span v-else>{{ authorInitials(post) }}</span>
                      </div>
                    </div>

                    <div class="flex gap-4">
                      <span class="flex items-center gap-1.5 text-on-surface-variant" data-forum-featured-like>
                        <span class="material-symbols-outlined text-xl" aria-hidden="true">favorite</span>
                        <span class="text-xs font-bold">{{ featuredPost.like_count ?? 0 }}</span>
                      </span>
                      <span class="flex items-center gap-1.5 text-on-surface-variant" data-forum-featured-comment>
                        <span class="material-symbols-outlined text-xl" aria-hidden="true">chat_bubble</span>
                        <span class="text-xs font-bold">{{ featuredPost.comment_count ?? 0 }}</span>
                      </span>
                      <button
                        v-if="isPostAuthor(featuredPost)"
                        class="rounded-full border border-outline-variant/30 px-4 py-1.5 text-xs font-bold text-on-surface-variant hover:bg-surface-container"
                        type="button"
                        @click.stop="openDeletePostDialog(featuredPost)"
                      >
                        Delete
                      </button>
                    </div>
                  </div>
                </div>
              </div>
            </article>

            <div class="grid grid-cols-1 gap-6 md:grid-cols-2">
              <article
                v-for="post in secondaryPosts"
                :key="post.id"
                class="flex cursor-pointer flex-col justify-between rounded-3xl border border-transparent bg-surface-container p-6 shadow-sm transition-all hover:border-outline-variant/20"
                data-forum-post-card
                role="link"
                tabindex="0"
                @click="openPostDetail(post.id)"
                @keyup.enter="openPostDetail(post.id)"
              >
                <div>
                  <div class="mb-4 flex items-start justify-between">
                    <div class="flex items-center gap-3">
                      <div class="flex h-10 w-10 items-center justify-center rounded-full bg-tertiary-container font-black text-on-tertiary-container">
                        <span>{{ authorInitials(post) }}</span>
                      </div>
                      <div>
                        <p class="font-bold text-on-surface">{{ authorLabel(post) }}</p>
                        <span class="text-[10px] font-bold uppercase tracking-tight text-tertiary">{{ authorBadge(post) }}</span>
                      </div>
                    </div>
                    <span class="text-[10px] font-bold text-on-surface-variant">{{ formatDate(post.created_at) }}</span>
                  </div>
                  <h4 class="mb-2 text-lg font-bold text-on-surface">{{ post.title }}</h4>
                  <p class="mb-6 text-sm font-body text-on-surface-variant">{{ summarize(post.content, 140) }}</p>
                </div>

                <div class="flex items-center justify-between border-t border-outline-variant/10 pt-4">
                  <div class="flex gap-3">
                    <span class="flex items-center gap-1 text-on-surface-variant">
                      <span class="material-symbols-outlined text-lg" aria-hidden="true">favorite</span>
                      <span class="text-xs">{{ post.like_count ?? 0 }}</span>
                    </span>
                    <span class="flex items-center gap-1 text-on-surface-variant">
                      <span class="material-symbols-outlined text-lg" aria-hidden="true">chat_bubble</span>
                      <span class="text-xs">{{ post.comment_count ?? 0 }}</span>
                    </span>
                    <button
                      v-if="isPostAuthor(post)"
                      class="flex items-center gap-1 text-on-surface-variant transition-colors hover:text-primary"
                      type="button"
                      @click.stop="openDeletePostDialog(post)"
                    >
                      <span class="material-symbols-outlined text-lg">delete</span>
                      <span class="text-xs">Delete</span>
                    </button>
                  </div>
                  <span class="rounded-md bg-surface-container-highest px-3 py-1 text-[10px] font-bold uppercase text-on-surface-variant">{{ cardCategory(post) }}</span>
                </div>
              </article>
            </div>

            <!-- Pagination controls -->
            <div v-if="!loading && totalPages > 1" class="flex items-center justify-center gap-2 pt-4">
            <button
              class="flex h-9 w-9 items-center justify-center rounded-full bg-surface-container text-sm font-bold text-on-surface-variant transition-colors hover:bg-surface-container-high disabled:opacity-40"
              type="button"
              :disabled="!hasPrev"
              @click="prevPage"
            >
              <span class="material-symbols-outlined text-lg">chevron_left</span>
            </button>
            <template v-for="item in pageItems" :key="item.key">
              <span v-if="item.ellipsis" class="flex h-9 w-9 items-center justify-center text-sm text-on-surface-variant">…</span>
              <button
                v-else
                class="flex h-9 w-9 items-center justify-center rounded-full text-sm font-bold transition-colors"
                :class="item.p === page ? 'bg-primary text-on-primary shadow-md' : 'bg-surface-container text-on-surface-variant hover:bg-surface-container-high'"
                type="button"
                @click="goToPage(item.p)"
              >
                {{ item.p }}
              </button>
            </template>
            <button
              class="flex h-9 w-9 items-center justify-center rounded-full bg-surface-container text-sm font-bold text-on-surface-variant transition-colors hover:bg-surface-container-high disabled:opacity-40"
              type="button"
              :disabled="!hasNext"
              @click="nextPage"
            >
              <span class="material-symbols-outlined text-lg">chevron_right</span>
            </button>
            </div>
          </div>
        </section>

        <aside class="sticky top-24 hidden h-fit w-80 flex-col space-y-8 xl:flex" data-forum-right-rail>
          <div class="rounded-3xl bg-surface-container-low p-6">
            <h3 class="mb-6 text-lg font-black text-on-surface">Top Contributors</h3>
            <div class="space-y-6">
              <div v-for="contributor in topContributors" :key="contributor.userId" class="flex items-center gap-4">
                <div>
                  <p class="text-sm font-bold text-on-surface">{{ contributor.name }}</p>
                  <p class="text-xs font-black uppercase tracking-wider" :class="contributor.toneClass">{{ contributor.saved }}</p>
                </div>
              </div>
            </div>
          </div>

          <div class="rounded-3xl bg-surface-container p-6">
            <h3 class="mb-4 text-lg font-black text-on-surface">Trending</h3>
            <div class="flex flex-wrap gap-2">
              <button
                v-for="tag in trendingTags"
                :key="tag"
                class="rounded-xl px-4 py-2 text-xs font-bold shadow-sm transition-colors"
                :class="isTrendActive(tag) ? 'bg-primary text-on-primary' : 'bg-surface-container-lowest text-on-surface-variant hover:text-primary'"
                type="button"
                @click="handleTrendClick(tag)"
              >
                {{ tag }}
              </button>
            </div>
          </div>
        </aside>
        </div>

        <button class="group fixed bottom-8 right-8 hidden items-center gap-2 rounded-full bg-[#b9f600] p-5 text-[#324600] shadow-2xl transition-transform hover:scale-105 lg:flex" data-forum-compose-toggle type="button" @click="handleAddPostClick">
          <span class="material-symbols-outlined text-3xl">photo_camera</span>
          <span class="hidden pr-2 text-sm font-black transition-all group-hover:block">SNAP IMPACT</span>
        </button>

        <div
          v-if="pendingDeletePost"
          class="forum-composer-window fixed inset-0 z-50 flex items-center justify-center px-4 py-6"
          data-forum-delete-dialog
        >
          <div
            aria-label="Cancel post deletion"
            class="forum-composer-window__scrim"
            role="button"
            tabindex="0"
            @click="cancelDeletePost"
            @keyup.enter="cancelDeletePost"
            @keyup.space.prevent="cancelDeletePost"
          ></div>
          <section
            aria-labelledby="forum-delete-title"
            aria-modal="true"
            class="forum-composer-panel w-full max-w-md rounded-3xl p-6 shadow-[0_24px_72px_rgba(43,48,47,0.24)]"
            role="dialog"
          >
            <div class="flex items-start gap-4">
              <div class="flex h-12 w-12 shrink-0 items-center justify-center rounded-full bg-error/10 text-error">
                <span class="material-symbols-outlined text-2xl">delete</span>
              </div>
              <div class="min-w-0">
                <p class="text-[10px] font-black uppercase tracking-[0.22em] text-error">Delete Post</p>
                <h2 id="forum-delete-title" class="mt-2 text-2xl font-black tracking-tight text-on-surface">Delete this post?</h2>
                <p class="mt-3 text-sm leading-relaxed text-on-surface-variant">
                  "{{ pendingDeletePost.title }}" will be permanently removed from the community feed.
                </p>
              </div>
            </div>
            <p v-if="submitError" class="mt-4 text-sm font-semibold text-error">{{ submitError }}</p>
            <div class="mt-6 flex flex-wrap justify-end gap-3">
              <button
                class="rounded-full border border-outline-variant/30 px-5 py-3 text-sm font-bold text-on-surface-variant hover:bg-surface-container disabled:opacity-60"
                :disabled="isDeletingPost"
                type="button"
                @click="cancelDeletePost"
              >
                Cancel
              </button>
              <button
                class="rounded-full bg-[#b31b25] px-5 py-3 text-sm font-bold text-[#ffefee] shadow-md transition-colors hover:bg-[#9f0519] active:scale-95 disabled:opacity-60"
                :disabled="isDeletingPost"
                type="button"
                @click="confirmDeletePost"
              >
                {{ isDeletingPost ? "Deleting..." : "Delete post" }}
              </button>
            </div>
          </section>
        </div>

        <div
          v-if="showComposer"
          class="forum-composer-window fixed inset-0 z-50 flex items-center justify-center px-4 py-6"
          data-forum-composer-window
        >
          <div
            aria-label="Close post composer"
            class="forum-composer-window__scrim"
            role="button"
            tabindex="0"
            @click="cancelComposer"
            @keyup.enter="cancelComposer"
            @keyup.space.prevent="cancelComposer"
          ></div>
          <section
            aria-labelledby="forum-composer-title"
            aria-modal="true"
            class="forum-composer-panel max-h-[calc(100dvh-48px)] w-full max-w-2xl overflow-y-auto rounded-3xl p-6 shadow-[0_24px_72px_rgba(43,48,47,0.24)]"
            data-forum-composer
            role="dialog"
          >
            <div class="mb-6 flex items-start justify-between gap-4">
              <div>
                <p class="text-[10px] font-black uppercase tracking-[0.22em] text-primary">New Post</p>
                <h2 id="forum-composer-title" class="mt-2 text-2xl font-black tracking-tight text-on-surface">Publish to the community</h2>
                <p class="mt-2 text-sm text-on-surface-variant">Upload images and post directly into the live forum feed.</p>
              </div>
              <button class="rounded-full border border-outline-variant/30 px-4 py-2 text-sm font-bold text-on-surface-variant hover:bg-surface-container" type="button" @click="cancelComposer">
                Close
              </button>
            </div>

            <form class="grid gap-4" @submit.prevent="submitPost">
              <label class="grid gap-2">
                <span class="text-sm font-bold text-on-surface">Title</span>
                <input
                  v-model.trim="draft.title"
                  class="rounded-2xl border border-outline-variant/20 bg-surface-container-low px-4 py-3 outline-none focus:border-primary"
                  maxlength="200"
                  placeholder="What are you sharing today?"
                  required
                  type="text"
                />
              </label>
              <label class="grid gap-2">
                <span class="text-sm font-bold text-on-surface">Content</span>
                <textarea
                  v-model.trim="draft.content"
                  class="min-h-32 rounded-2xl border border-outline-variant/20 bg-surface-container-low px-4 py-3 outline-none focus:border-primary"
                  placeholder="Add the context, result, or question behind your post."
                  required
                  rows="6"
                ></textarea>
              </label>
              <div class="grid gap-2">
                <span class="text-sm font-bold text-on-surface">Images</span>
                <div class="flex flex-wrap items-center gap-3">
                  <button
                    type="button"
                    class="rounded-2xl border border-outline-variant/20 bg-surface-container-low px-4 py-3 text-sm font-bold text-on-surface transition-colors hover:bg-surface-container-high"
                    @click="imageInput.click()"
                  >
                    Choose images
                  </button>
                  <span class="text-sm text-on-surface-variant">{{ selectedImageNames.length }} file{{ selectedImageNames.length === 1 ? '' : 's' }} selected</span>
                </div>
                <input ref="imageInput" accept="image/*" multiple type="file" class="hidden" @change="handleImageSelection" />
                <div v-if="selectedImages.length > 0" class="forum-image-preview-grid" aria-label="Selected image preview order">
                  <article
                    v-for="image in selectedImages"
                    :key="image.id"
                    class="forum-image-preview"
                    :class="{ 'forum-image-preview--dragging': draggedImageId === image.id }"
                    data-forum-image-preview
                    draggable="true"
                    @dragstart="handleImageDragStart(image.id)"
                    @dragend="handleImageDragEnd"
                    @dragenter.prevent="handleImageDragOver(image.id)"
                    @dragover.prevent="handleImageDragOver(image.id)"
                    @drop.prevent="handleImageDrop"
                  >
                    <img v-if="image.previewUrl" :alt="`${image.file.name} preview`" class="forum-image-preview__image" :src="image.previewUrl" />
                    <div v-else class="forum-image-preview__fallback">
                      <span class="material-symbols-outlined text-xl">image</span>
                    </div>
                    <button
                      class="forum-image-preview__delete"
                      type="button"
                      :aria-label="`Remove ${image.file.name}`"
                      @click="removeSelectedImage(image.id)"
                    >
                      <span class="material-symbols-outlined text-base">close</span>
                    </button>
                    <span class="forum-image-preview__name" :title="image.file.name">{{ image.file.name }}</span>
                  </article>
                </div>
              </div>
              <p v-if="submitError" class="text-sm font-semibold text-error">{{ submitError }}</p>
              <div class="flex flex-wrap gap-3">
                <button class="rounded-full bg-primary px-5 py-3 text-sm font-bold text-on-primary shadow-md transition-transform active:scale-95 disabled:opacity-60" :disabled="submitting" type="submit">
                  {{ submitting ? "Publishing..." : "Publish Post" }}
                </button>
                <button class="rounded-full border border-outline-variant/30 px-5 py-3 text-sm font-bold text-on-surface-variant hover:bg-surface-container" :disabled="submitting" type="button" @click="cancelComposer">
                  Cancel
                </button>
              </div>
            </form>
          </section>
        </div>
      </section>
    </main>
  </div>
</template>

<script setup>
import { computed, onMounted, onUnmounted, reactive, ref } from "vue";
import { useRouter } from "vue-router";

import {
  createForumPostWithImages,
  deleteForumPost,
  fetchForumPosts,
  parseForumImageUrls,
  uploadForumImage,
} from "../../api/forum/forum.js";
import { useAuth } from "../../composables/useAuth.js";
import { showErrorToast, showSuccessToast } from "../../composables/useToast.js";
import AppHeader from "../../components/common/AppHeader.vue";

const router = useRouter();
const { isLoggedIn, token, user } = useAuth();

const FEATURED_POSTS_PER_PAGE = 1;
const SECONDARY_POSTS_PER_PAGE = 4;
const POSTS_PER_PAGE = FEATURED_POSTS_PER_PAGE + SECONDARY_POSTS_PER_PAGE;

const posts = ref([]);
const page = ref(1);
const total = ref(0);
const loading = ref(false);
const error = ref("");
const showComposer = ref(false);
const submitting = ref(false);
const isDeletingPost = ref(false);
const submitError = ref("");
const submitSuccess = ref("");
const pendingDeletePost = ref(null);
const searchQuery = ref("");
const activeFilter = ref("all");
const imageInput = ref(null);
const selectedImages = ref([]);
const draggedImageId = ref("");
const draft = reactive({ title: "", content: "" });
let selectedImageIdCounter = 0;

const paginatedFilteredPosts = computed(() => {
  const start = Math.max((page.value - 1) * POSTS_PER_PAGE, 0);
  return filteredPosts.value.slice(start, start + POSTS_PER_PAGE);
});
const totalPages = computed(() => Math.max(1, Math.ceil(filteredPosts.value.length / POSTS_PER_PAGE)));
const hasPrev = computed(() => page.value > 1);
const hasNext = computed(() => page.value < totalPages.value);

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

const avatarAlt = computed(() => user.value?.username || "User avatar");
const avatarUrl = computed(() => user.value?.avatar_url || "");
const pointsLabel = computed(() => {
  if (isLoggedIn.value && user.value?.current_points != null) {
    return `${user.value.current_points} pts`;
  }
  return "0 pts";
});
const feedFilters = [
  { key: "all", label: "All Posts", keywords: [] },
  { key: "recycling", label: "Recycling Success", keywords: ["recycl", "reuse", "glass", "compost", "waste", "repair"] },
  { key: "hacks", label: "Sustainable Hacks", keywords: ["hack", "tips", "tip", "upcycl", "solar", "apartment"] },
  { key: "qa", label: "Community Q&A", keywords: ["?", "best", "recommend", "help", "how", "should i"] },
];

const sortLabel = computed(() => {
  if (isLoggedIn.value) {
    return "Personalized";
  }
  return "Latest";
});

const trendingTags = computed(() => {
  const tagCandidates = new Map();

  posts.value.forEach((post) => {
    const text = `${post.title || ""} ${post.content || ""}`;
    const rawTags = Array.from(text.matchAll(/#([a-zA-Z0-9_\u4e00-\u9fa5]+)/g)).map((match) => `#${match[1]}`);
    rawTags.forEach((tag) => tagCandidates.set(tag, (tagCandidates.get(tag) || 0) + 1));

    const lowerText = text.toLowerCase();
    if (lowerText.includes("recycl")) {
      tagCandidates.set("#Recycling", (tagCandidates.get("#Recycling") || 0) + 1);
    }
    if (lowerText.includes("upcycl") || lowerText.includes("diy")) {
      tagCandidates.set("#Upcycling", (tagCandidates.get("#Upcycling") || 0) + 1);
    }
    if (lowerText.includes("solar")) {
      tagCandidates.set("#Solar", (tagCandidates.get("#Solar") || 0) + 1);
    }
    if (lowerText.includes("waste") || lowerText.includes("zero waste") || lowerText.includes("zero-waste")) {
      tagCandidates.set("#ZeroWaste", (tagCandidates.get("#ZeroWaste") || 0) + 1);
    }
    if (lowerText.includes("community") || lowerText.includes("share")) {
      tagCandidates.set("#Community", (tagCandidates.get("#Community") || 0) + 1);
    }
  });

  if (tagCandidates.size === 0) {
    return ["#Recycling", "#Upcycling", "#Community", "#Solar", "#ZeroWaste"];
  }

  return Array.from(tagCandidates.entries())
    .sort((a, b) => b[1] - a[1])
    .slice(0, 6)
    .map(([tag]) => tag);
});

const trendToFilterKey = {
  "#ZeroWasteHome": "recycling",
  "#ZeroWaste": "recycling",
  "#GlassHero": "recycling",
  "#Recycling": "recycling",
  "#Upcycling": "hacks",
  "#SolarLife": "hacks",
  "#Solar": "hacks",
  "#OceanGuard": "qa",
  "#Community": "qa",
};

const topContributors = computed(() => {
  const contributorStats = new Map();

  posts.value.forEach((post) => {
    const userId = String(post?.author_id ?? "unknown");
    const username = String(post?.author_username || post?.username || `User #${userId}`).trim();
    const existing = contributorStats.get(userId) ?? {
      userId,
      name: username,
      postCount: 0,
      totalLikes: 0,
      totalImpact: 0,
    };

    existing.postCount += 1;
    existing.totalLikes += Number(post?.like_count || 0);
    existing.totalImpact += Number(readPostImpact(post) || 0);
    contributorStats.set(userId, existing);
  });

  return Array.from(contributorStats.values())
    .sort((a, b) => b.totalLikes - a.totalLikes || b.postCount - a.postCount)
    .slice(0, 3)
    .map((contributor, index) => ({
      userId: contributor.userId,
      initials: authorInitialsFromName(contributor.name),
      name: contributor.name,
      rank: String(index + 1),
      saved: `${contributor.totalLikes} Likes`,
      toneClass: index === 0 ? "text-secondary" : index === 1 ? "text-primary" : "text-tertiary",
    }));
});

const selectedImageNames = computed(() => selectedImages.value.map((image) => image.file.name));
const filteredPosts = computed(() =>
  posts.value.filter((post) => {
    if (!matchesFilter(post, activeFilter.value)) {
      return false;
    }

    const query = searchQuery.value.trim().toLowerCase();
    if (!query) {
      return true;
    }

    return `${post.title || ""} ${post.content || ""}`.toLowerCase().includes(query);
  }),
);

const featuredPost = computed(() => {
  if (paginatedFilteredPosts.value.length === 0) {
    return null;
  }

  return [...paginatedFilteredPosts.value]
    .sort((leftPost, rightPost) => {
      const scoreDiff = scoreFeaturedPost(rightPost) - scoreFeaturedPost(leftPost);
      if (scoreDiff !== 0) {
        return scoreDiff;
      }

      const rightTime = new Date(rightPost?.created_at || 0).getTime();
      const leftTime = new Date(leftPost?.created_at || 0).getTime();
      if (rightTime !== leftTime) {
        return rightTime - leftTime;
      }

      return Number(rightPost?.id || 0) - Number(leftPost?.id || 0);
    })[0];
});
const secondaryPosts = computed(() =>
  paginatedFilteredPosts.value.filter((post) => Number(post?.id) !== Number(featuredPost.value?.id)),
);
const featuredImageUrl = computed(() => (featuredPost.value ? getImageUrls(featuredPost.value)[0] || "" : ""));
const avatarStackPosts = computed(() =>
  secondaryPosts.value.slice(0, Math.min(SECONDARY_POSTS_PER_PAGE, 3)),
);
function isPostAuthor(post) {
  if (!user.value?.id || post?.author_id == null) {
    return false;
  }

  return Number(user.value.id) === Number(post.author_id);
}

function matchesFilter(post, key) {
  if (key === "all") {
    return true;
  }

  const matchedFilter = feedFilters.find((filter) => filter.key === key);
  if (!matchedFilter) {
    return true;
  }

  const haystack = `${post.title || ""} ${post.content || ""}`.toLowerCase();
  return matchedFilter.keywords.some((keyword) => haystack.includes(keyword));
}

function setActiveFilter(key) {
  activeFilter.value = key;
  page.value = 1;
}

function handleTrendClick(tag) {
  setActiveFilter(trendToFilterKey[tag] || "all");
}

function isTrendActive(tag) {
  return activeFilter.value === (trendToFilterKey[tag] || "all");
}

function openPostDetail(postId) {
  router.push(`/forum/posts/${postId}`);
}

function authorLabel(post) {
  const username = String(post?.author_username || post?.username || "").trim();
  if (username) {
    return username;
  }
  return `User #${post?.author_id ?? "Unknown"}`;
}

function authorInitials(post) {
  const username = String(post?.author_username || post?.username || `User #${post?.author_id ?? "CS"}`).trim();
  const parts = username.split(/\s+/).filter(Boolean);
  if (parts.length >= 2) {
    return `${parts[0][0]}${parts[1][0]}`.toUpperCase();
  }
  return username.slice(0, 2).toUpperCase();
}

function authorInitialsFromName(name) {
  const normalized = String(name || "User").trim();
  const parts = normalized.split(/\s+/).filter(Boolean);
  if (parts.length >= 2) {
    return `${parts[0][0]}${parts[1][0]}`.toUpperCase();
  }
  return normalized.slice(0, 2).toUpperCase();
}

function authorBadge(post) {
  const likes = Number(post?.like_count || 0);
  if (likes >= 20) {
    return "Ocean Saver";
  }
  if (likes >= 8) {
    return "Glass Hero";
  }
  return "Seedling";
}

function cardCategory(post) {
  if (matchesFilter(post, "qa")) {
    return "Community Q&A";
  }
  if (matchesFilter(post, "hacks")) {
    return "Sustainable Hacks";
  }
  if (matchesFilter(post, "recycling")) {
    return "Recycling Success";
  }
  return "All Posts";
}

function scoreFeaturedPost(post) {
  const imageScore = getImageUrls(post).length > 0 ? 6 : 0;
  const titleLength = String(post?.title || "").trim().length;
  const contentLength = String(post?.content || "").trim().length;
  const contentScore =
    (titleLength >= 24 ? 2 : titleLength >= 12 ? 1 : 0) +
    (contentLength >= 160 ? 2 : contentLength >= 80 ? 1 : 0);
  const likes = Number(post?.like_count || 0);
  const comments = Number(post?.comment_count || 0);
  const engagementScore = likes + comments * 2;

  const createdAt = new Date(post?.created_at || 0);
  const ageMs = Date.now() - createdAt.getTime();
  const ageDays = Number.isFinite(ageMs) && ageMs >= 0 ? ageMs / 86400000 : 999;
  const recencyScore = ageDays <= 3 ? 2 : ageDays <= 7 ? 1 : 0;

  return imageScore + contentScore + engagementScore + recencyScore;
}

function readPostImpact(post) {
  const rawValue =
    post?.co2_saved_kg ??
    post?.impact_kg ??
    post?.impact_co2e_kg ??
    post?.carbon_reduction_kg;
  const parsed = Number(rawValue);
  return Number.isFinite(parsed) && parsed >= 0 ? parsed : null;
}

function readPostReward(post) {
  const rawValue =
    post?.reward_points ??
    post?.points_awarded ??
    post?.snap_rewards ??
    post?.reward_snap;
  const parsed = Number(rawValue);
  return Number.isFinite(parsed) && parsed >= 0 ? parsed : null;
}

function impactLabel(post) {
  const value = readPostImpact(post);
  return value !== null ? `${value.toFixed(1)}kg CO2e` : "Impact unavailable";
}

function rewardLabel(post) {
  const value = readPostReward(post);
  return value !== null ? `+${value} Snap` : "Reward unavailable";
}

function formatDate(value) {
  if (!value) {
    return "Unknown time";
  }

  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }

  return date.toLocaleString();
}

function summarize(content, limit = 220) {
  if (!content) {
    return "";
  }

  return content.length > limit ? `${content.slice(0, limit)}...` : content;
}

function getImageUrls(post) {
  return parseForumImageUrls(post?.image_urls_json);
}

function requireLogin() {
  if (isLoggedIn.value) {
    return true;
  }

  router.push("/login");
  return false;
}

function resetDraft() {
  draft.title = "";
  draft.content = "";
  clearSelectedImages();
  if (imageInput.value) {
    imageInput.value.value = "";
  }
}

function resetComposerMessages() {
  submitError.value = "";
  submitSuccess.value = "";
}

function handleAddPostClick() {
  resetComposerMessages();
  if (!showComposer.value && !requireLogin()) {
    return;
  }

  showComposer.value = !showComposer.value;
}

function cancelComposer() {
  showComposer.value = false;
  resetDraft();
  resetComposerMessages();
}

function handleImageSelection(event) {
  const fileList = event.target?.files;
  clearSelectedImages();
  selectedImages.value = fileList ? Array.from(fileList).map(createSelectedImage) : [];
}

function createSelectedImage(file) {
  selectedImageIdCounter += 1;
  return {
    id: `selected-image-${Date.now()}-${selectedImageIdCounter}`,
    file,
    previewUrl: createImagePreviewUrl(file),
  };
}

function createImagePreviewUrl(file) {
  if (typeof URL === "undefined" || typeof URL.createObjectURL !== "function") {
    return "";
  }

  return URL.createObjectURL(file);
}

function revokeImagePreviewUrl(previewUrl) {
  if (!previewUrl || typeof URL === "undefined" || typeof URL.revokeObjectURL !== "function") {
    return;
  }

  URL.revokeObjectURL(previewUrl);
}

function clearSelectedImages() {
  selectedImages.value.forEach((image) => revokeImagePreviewUrl(image.previewUrl));
  selectedImages.value = [];
  draggedImageId.value = "";
}

function removeSelectedImage(imageId) {
  const image = selectedImages.value.find((item) => item.id === imageId);
  if (image) {
    revokeImagePreviewUrl(image.previewUrl);
  }

  selectedImages.value = selectedImages.value.filter((item) => item.id !== imageId);
  if (draggedImageId.value === imageId) {
    draggedImageId.value = "";
  }
}

function handleImageDragStart(imageId) {
  draggedImageId.value = imageId;
}

function handleImageDragEnd() {
  draggedImageId.value = "";
}

function handleImageDragOver(targetImageId) {
  const sourceImageId = draggedImageId.value;
  if (!sourceImageId || sourceImageId === targetImageId) {
    return;
  }

  moveSelectedImage(sourceImageId, targetImageId);
}

function handleImageDrop() {
  draggedImageId.value = "";
}

function moveSelectedImage(sourceImageId, targetImageId) {
  const nextImages = [...selectedImages.value];
  const sourceIndex = nextImages.findIndex((image) => image.id === sourceImageId);
  const targetIndex = nextImages.findIndex((image) => image.id === targetImageId);

  if (sourceIndex === -1 || targetIndex === -1) {
    return;
  }

  const [movedImage] = nextImages.splice(sourceIndex, 1);
  nextImages.splice(targetIndex, 0, movedImage);
  selectedImages.value = nextImages;
}

function readFileAsDataUrl(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(String(reader.result || ""));
    reader.onerror = () => reject(new Error(`Failed to read ${file.name}.`));
    reader.readAsDataURL(file);
  });
}

async function uploadSelectedImages() {
  const uploadedUrls = [];
  for (const image of selectedImages.value) {
    const imageDataUrl = await readFileAsDataUrl(image.file);
    const result = await uploadForumImage(imageDataUrl, token.value);
    uploadedUrls.push(result.url);
  }
  return uploadedUrls;
}

async function loadPosts() {
  loading.value = true;
  error.value = "";
  try {
    const data = await fetchForumPosts({ page: 1, perPage: 1000, token: token.value || null });
    posts.value = Array.isArray(data) ? data : data?.items || [];
    total.value = data?.total ?? posts.value.length;
    if (page.value > totalPages.value) {
      page.value = totalPages.value;
    }
  } catch (err) {
    error.value = err instanceof Error ? err.message : "Failed to load posts.";
  } finally {
    loading.value = false;
  }
}

function goToPage(targetPage) {
  if (targetPage < 1 || targetPage > totalPages.value) return;
  page.value = targetPage;
  window.scrollTo({ top: 0, behavior: "smooth" });
}

function prevPage() {
  goToPage(page.value - 1);
}

function nextPage() {
  goToPage(page.value + 1);
}

async function submitPost() {
  resetComposerMessages();
  if (!requireLogin()) {
    return;
  }

  submitting.value = true;
  try {
    const uploadedImageUrls = await uploadSelectedImages();
    const createdPost = await createForumPostWithImages(
      {
        title: draft.title,
        content: draft.content,
        imageUrls: uploadedImageUrls,
      },
      token.value,
    );

    resetDraft();
    showComposer.value = false;
    submitSuccess.value = `Post #${createdPost.id} created successfully.`;
    showSuccessToast("Post published", "Your post is now live in the community feed.");
    page.value = 1;
    await loadPosts();
  } catch (err) {
    submitError.value = err instanceof Error ? err.message : "Failed to create post.";
    showErrorToast("Post failed", submitError.value);
  } finally {
    submitting.value = false;
  }
}

function openDeletePostDialog(post) {
  resetComposerMessages();
  if (!requireLogin()) {
    return;
  }

  pendingDeletePost.value = post;
}

function cancelDeletePost() {
  if (isDeletingPost.value) {
    return;
  }

  pendingDeletePost.value = null;
  submitError.value = "";
}

async function confirmDeletePost() {
  if (!pendingDeletePost.value || isDeletingPost.value) {
    return;
  }

  isDeletingPost.value = true;
  submitError.value = "";
  try {
    await deleteForumPost(pendingDeletePost.value.id, token.value);
    pendingDeletePost.value = null;
    page.value = 1;
    await loadPosts();
    submitSuccess.value = "Post deleted.";
    showSuccessToast("Post deleted", "The forum post has been removed.");
  } catch (err) {
    submitError.value = err instanceof Error ? err.message : "Failed to delete.";
    showErrorToast("Delete failed", submitError.value);
  } finally {
    isDeletingPost.value = false;
  }
}

onMounted(loadPosts);
onUnmounted(clearSelectedImages);
</script>

<style scoped src="../../styles/views/forum-view.css"></style>
