<template>
  <div class="forum-shell min-h-screen bg-surface font-body text-on-surface antialiased">
    <AppHeader
      :avatar-alt="avatarAlt"
      avatar-href="/profile"
      :avatar-url="avatarUrl"
      :is-authenticated="isLoggedIn"
      :points-label="pointsLabel"
      position-mode="static"
    />

    <main class="forum-shell__content">
      <section class="forum-detail-page bg-surface text-on-surface min-h-screen">
        <section class="min-w-0 flex-1 space-y-8" data-forum-detail-layout>
          <p v-if="loading" class="rounded-3xl bg-surface-container-lowest px-6 py-4 shadow-sm">Loading post...</p>
          <p v-else-if="error" class="rounded-3xl bg-surface-container-lowest px-6 py-4 text-error shadow-sm">{{ error }}</p>

          <template v-else-if="post">
            <div class="flex flex-col gap-6">
              <div>
                <p class="text-[10px] font-black uppercase tracking-[0.22em] text-primary">Verified Impact Story</p>
                <h1 class="mt-3 text-3xl font-black tracking-tight text-on-surface">Forum Thread</h1>
                <p class="mt-2 text-sm font-medium text-on-surface-variant">View the full conversation, add comments, and join the community discussion.</p>
              </div>

              <article class="group overflow-hidden rounded-3xl bg-surface-container-lowest shadow-[0_8px_32px_rgba(43,48,47,0.04)]">
                <div class="flex flex-col lg:flex-row lg:items-stretch">
                  <div class="relative h-72 overflow-hidden sm:h-80 lg:h-auto lg:min-h-[360px] lg:max-h-[720px] lg:w-1/2 lg:flex-none lg:self-stretch xl:max-h-[780px]" data-forum-detail-gallery>
                    <button v-if="activePostImageUrl" class="h-full w-full cursor-zoom-in p-0" type="button" data-forum-gallery-preview-trigger @click="openPostImagePreview(selectedPostImageIndex)">
                      <img :alt="`${post.title} image ${selectedPostImageIndex + 1}`" class="h-full w-full object-cover transition-transform duration-700 group-hover:scale-105" :src="activePostImageUrl" />
                    </button>
                    <div v-else class="flex h-full w-full items-center justify-center bg-gradient-to-br from-surface-container-high to-surface-container-low">
                      <div class="text-center">
                        <p class="text-xs font-black uppercase tracking-[0.2em] text-primary">Forum post</p>
                        <p class="mt-2 text-3xl font-black text-on-surface">{{ authorInitials(post) }}</p>
                      </div>
                    </div>
                    <template v-if="postImageUrls.length > 1">
                      <button
                        class="absolute left-4 top-1/2 flex h-10 w-10 -translate-y-1/2 items-center justify-center rounded-full bg-black/45 text-white shadow-lg transition-colors hover:bg-black/65"
                        type="button"
                        aria-label="Show previous image"
                        data-forum-gallery-prev
                        @click="showPreviousPostImage"
                      >
                        <span class="material-symbols-outlined">chevron_left</span>
                      </button>
                      <button
                        class="absolute right-4 top-1/2 flex h-10 w-10 -translate-y-1/2 items-center justify-center rounded-full bg-black/45 text-white shadow-lg transition-colors hover:bg-black/65"
                        type="button"
                        aria-label="Show next image"
                        data-forum-gallery-next
                        @click="showNextPostImage"
                      >
                        <span class="material-symbols-outlined">chevron_right</span>
                      </button>
                      <div class="absolute bottom-4 left-1/2 flex max-w-[calc(100%-32px)] -translate-x-1/2 gap-2 overflow-x-auto rounded-2xl bg-black/45 p-2 backdrop-blur">
                        <button
                          v-for="(imageUrl, imageIndex) in postImageUrls"
                          :key="`${imageUrl}-${imageIndex}`"
                          class="h-12 w-12 shrink-0 overflow-hidden rounded-xl border-2 transition-colors"
                          :class="imageIndex === selectedPostImageIndex ? 'border-white' : 'border-white/30 opacity-70 hover:opacity-100'"
                          type="button"
                          :aria-label="`Show image ${imageIndex + 1}`"
                          data-forum-gallery-thumb
                          @click="selectedPostImageIndex = imageIndex"
                        >
                          <img class="h-full w-full object-cover" :src="imageUrl" :alt="`${post.title} thumbnail ${imageIndex + 1}`" />
                        </button>
                      </div>
                    </template>
                  </div>

                  <div class="flex flex-col justify-between p-8 lg:w-1/2">
                    <div>
                      <div class="mb-4 flex items-start justify-between">
                        <div class="flex items-center gap-3">
                          <div class="flex h-10 w-10 items-center justify-center overflow-hidden rounded-full bg-tertiary-container font-black text-on-tertiary-container">
                            <img
                              v-if="authorAvatarUrl(post)"
                              :alt="authorLabel(post)"
                              class="h-full w-full object-cover"
                              :src="authorAvatarUrl(post)"
                            />
                            <span v-else>{{ authorInitials(post) }}</span>
                          </div>
                          <div>
                            <p class="font-bold text-on-surface">{{ authorLabel(post) }}</p>
                            <span class="rounded-md bg-primary-container px-2 py-0.5 text-[10px] font-bold uppercase tracking-tight text-on-primary-container">{{ post.status || "published" }}</span>
                          </div>
                        </div>
                        <span class="text-xs text-on-surface-variant">{{ formatDate(post.created_at) }}</span>
                      </div>

                      <h2 class="text-3xl font-black tracking-tight text-primary">{{ post.title }}</h2>
                      <p class="mt-4 font-body leading-relaxed text-on-surface-variant">{{ post.content }}</p>

                      <div class="mt-6 flex items-center gap-4 rounded-2xl border border-outline-variant/10 bg-surface-container-low p-4">
                        <div class="flex flex-col">
                          <span class="text-[10px] font-bold uppercase tracking-widest text-on-surface-variant">Likes</span>
                          <span class="inline-flex items-center gap-1 text-xl font-black text-secondary">
                            <span class="material-symbols-outlined text-[1.2em]" aria-hidden="true">favorite</span>
                            {{ post.like_count ?? 0 }}
                          </span>
                        </div>
                        <div class="h-8 w-px bg-outline-variant/30"></div>
                        <div class="flex flex-col">
                          <span class="text-[10px] font-bold uppercase tracking-widest text-on-surface-variant">Comments</span>
                          <span class="inline-flex items-center gap-1 text-xl font-black text-primary">
                            <span class="material-symbols-outlined text-[1.2em]" aria-hidden="true">chat_bubble</span>
                            {{ commentTree.length }}
                          </span>
                        </div>
                        <div class="h-8 w-px bg-outline-variant/30"></div>
                        <div class="flex flex-col">
                          <span class="text-[10px] font-bold uppercase tracking-widest text-on-surface-variant">Images</span>
                          <span class="text-xl font-black text-primary">{{ postImageUrls.length }}</span>
                        </div>
                      </div>
                    </div>
                    <div class="mt-8 flex flex-wrap gap-3">
                      <button
                        type="button"
                        class="inline-flex min-h-11 items-center gap-2 rounded-full bg-primary px-5 py-3 text-sm font-bold text-on-primary shadow-md"
                        :aria-label="post.liked_by_user ? 'Unlike post' : 'Like post'"
                        data-forum-detail-like
                        @click="handlePostLike"
                      >
                        <span class="material-symbols-outlined text-xl" :style="post.liked_by_user ? filledIconStyle : null" aria-hidden="true">favorite</span>
                        <span>{{ post.like_count ?? 0 }}</span>
                      </button>
                      <button v-if="isPostAuthor" type="button" class="rounded-full border border-outline-variant/30 px-5 py-3 text-sm font-bold text-on-surface-variant hover:bg-surface-container" @click="openEditPostComposer">Edit post</button>
                      <button v-if="isPostAuthor" type="button" class="rounded-full border border-outline-variant/30 px-5 py-3 text-sm font-bold text-on-surface-variant hover:bg-surface-container" @click="openDeletePostDialog">Delete post</button>
                      <RouterLink class="rounded-full border border-outline-variant/30 px-5 py-3 text-sm font-bold text-on-surface-variant hover:bg-surface-container" to="/forum">Back to forum</RouterLink>
                    </div>
                  </div>
                </div>
              </article>

              <section class="rounded-3xl bg-surface-container-lowest p-6 shadow-sm" data-forum-comments>
                <div class="mb-6 flex items-center justify-between gap-4">
                  <div>
                    <p class="text-[10px] font-black uppercase tracking-[0.22em] text-primary">Discussion</p>
                    <h2 class="mt-2 text-2xl font-black tracking-tight text-on-surface">Comments</h2>
                  </div>
                  <button type="button" class="rounded-full border border-outline-variant/30 px-4 py-2 text-sm font-bold text-on-surface-variant hover:bg-surface-container" @click="loadComments">Refresh Comments</button>
                </div>

                <form class="mb-6 grid gap-4" data-forum-comment-form @submit.prevent="submitComment">
                  <label class="grid gap-2">
                    <span class="text-sm font-bold text-on-surface">Add Comment</span>
                    <textarea v-model.trim="commentDraft" class="min-h-24 rounded-2xl border border-outline-variant/20 bg-surface-container-low px-4 py-3 outline-none focus:border-primary" placeholder="Share your thoughts with the community" required rows="4"></textarea>
                  </label>
                  <p v-if="commentActionError" class="text-sm font-semibold text-error">{{ commentActionError }}</p>
                  <button type="submit" class="w-fit rounded-full bg-primary px-5 py-3 text-sm font-bold text-on-primary shadow-md" :disabled="commentSubmitting">
                    {{ commentSubmitting ? "Submitting..." : "Submit Comment" }}
                  </button>
                </form>

                <p v-if="commentsLoading" class="text-sm text-on-surface-variant">Loading comments...</p>
                <p v-else-if="commentsError" class="text-sm font-semibold text-error">{{ commentsError }}</p>
                <p v-else-if="commentTree.length === 0" class="text-sm text-on-surface-variant">No comments yet.</p>

                <div v-else class="grid gap-4">
                  <article v-for="comment in commentTree" :key="comment.id" class="grid gap-3 rounded-3xl bg-surface-container p-5 shadow-sm" :class="{ 'ml-6': comment.reply_depth > 0 }">
                    <div class="flex items-start gap-3">
                      <div class="flex h-11 w-11 shrink-0 items-center justify-center overflow-hidden rounded-full bg-tertiary-container font-black text-on-tertiary-container">
                        <img
                          v-if="commentAvatarUrl(comment)"
                          :alt="commentAuthorLabel(comment)"
                          class="h-full w-full object-cover"
                          :src="commentAvatarUrl(comment)"
                        />
                        <span v-else>{{ commentInitials(comment) }}</span>
                      </div>
                      <div class="min-w-0">
                        <div class="flex flex-wrap gap-3 text-xs font-bold text-on-surface-variant">
                          <span class="text-on-surface">{{ commentAuthorLabel(comment) }}</span>
                          <span>Comment #{{ comment.id }}</span>
                          <span>{{ formatDate(comment.created_at) }}</span>
                        </div>
                        <p v-if="comment.parent_comment_id !== null" class="mt-1 text-sm text-on-surface-variant">Reply to comment #{{ comment.parent_comment_id }}</p>
                      </div>
                    </div>
                    <p class="text-on-surface">{{ comment.content }}</p>
                    <div class="flex flex-wrap items-center gap-3">
                      <button
                        type="button"
                        class="inline-flex min-h-11 items-center gap-2 rounded-full border border-outline-variant/30 px-4 py-2 text-sm font-bold text-on-surface-variant hover:bg-surface-container"
                        :aria-label="openReplyId === comment.id ? `Cancel reply to comment ${comment.id}` : `Reply to comment ${comment.id}`"
                        data-forum-comment-reply
                        @click="toggleReplyComposer(comment.id)"
                      >
                        <span class="material-symbols-outlined text-lg" aria-hidden="true">
                          {{ openReplyId === comment.id ? "close" : "chat_bubble" }}
                        </span>
                      </button>
                      <button
                        type="button"
                        class="inline-flex min-h-11 items-center gap-2 rounded-full border border-outline-variant/30 px-4 py-2 text-sm font-bold text-on-surface-variant hover:bg-surface-container"
                        :aria-label="comment.liked_by_user ? `Unlike comment ${comment.id}` : `Like comment ${comment.id}`"
                        data-forum-comment-like
                        @click="handleCommentLike(comment)"
                      >
                        <span class="material-symbols-outlined text-lg" :style="comment.liked_by_user ? filledIconStyle : null" aria-hidden="true">favorite</span>
                        <span>{{ comment.like_count ?? 0 }}</span>
                      </button>
                      <button v-if="isCommentAuthor(comment)" type="button" class="rounded-full border border-outline-variant/30 px-4 py-2 text-sm font-bold text-on-surface-variant hover:bg-surface-container" @click="openDeleteCommentDialog(comment)">Delete</button>
                    </div>

                    <form v-if="openReplyId === comment.id" class="grid gap-3 rounded-2xl bg-surface-container-low p-4" @submit.prevent="submitReply(comment)">
                      <label class="grid gap-2">
                        <span class="text-sm font-bold text-on-surface">Reply</span>
                        <textarea v-model.trim="replyDraft" class="min-h-20 rounded-2xl border border-outline-variant/20 bg-surface-container-low px-4 py-3 outline-none focus:border-primary" placeholder="Reply to the discussion" required rows="3"></textarea>
                      </label>
                      <button type="submit" class="w-fit rounded-full bg-primary px-5 py-3 text-sm font-bold text-on-primary shadow-md" :disabled="replySubmitting">
                        {{ replySubmitting ? "Submitting..." : "Submit Reply" }}
                      </button>
                    </form>
                  </article>
                </div>
              </section>
            </div>
          </template>
        </section>
      </section>
    </main>

    <ImagePreviewModal
      v-if="imagePreviewOpen"
      :images="postImageUrls"
      :initial-index="imagePreviewInitialIndex"
      :title="post?.title || 'Forum post'"
      @close="imagePreviewOpen = false"
    />

    <div
      v-if="showEditComposer"
      class="forum-composer-window fixed inset-0 z-50 flex items-center justify-center px-4 py-6"
      data-forum-edit-composer-window
    >
      <div
        aria-label="Close post editor"
        class="forum-composer-window__scrim"
        role="button"
        tabindex="0"
        @click="cancelEditPostComposer"
        @keyup.enter="cancelEditPostComposer"
        @keyup.space.prevent="cancelEditPostComposer"
      ></div>
      <section
        aria-labelledby="forum-edit-composer-title"
        aria-modal="true"
        class="forum-composer-panel max-h-[calc(100dvh-48px)] w-full max-w-2xl overflow-y-auto rounded-3xl p-6 shadow-[0_24px_72px_rgba(43,48,47,0.24)]"
        data-forum-edit-composer
        role="dialog"
      >
        <div class="mb-6 flex items-start justify-between gap-4">
          <div>
            <p class="text-[10px] font-black uppercase tracking-[0.22em] text-primary">Edit Post</p>
            <h2 id="forum-edit-composer-title" class="mt-2 text-2xl font-black tracking-tight text-on-surface">Update your community post</h2>
            <p class="mt-2 text-sm text-on-surface-variant">Edit the text, remove existing images, add new images, and reorder the preview tiles.</p>
          </div>
          <button class="rounded-full border border-outline-variant/30 px-4 py-2 text-sm font-bold text-on-surface-variant hover:bg-surface-container" type="button" @click="cancelEditPostComposer">
            Close
          </button>
        </div>

        <form class="grid gap-4" @submit.prevent="saveEditedPost">
          <label class="grid gap-2">
            <span class="text-sm font-bold text-on-surface">Title</span>
            <input
              v-model.trim="editDraft.title"
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
              v-model.trim="editDraft.content"
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
                @click="editImageInput?.click()"
              >
                Choose images
              </button>
              <span class="text-sm text-on-surface-variant">{{ editImageItems.length }} image{{ editImageItems.length === 1 ? '' : 's' }} selected</span>
            </div>
            <input ref="editImageInput" accept="image/*" multiple type="file" class="hidden" @change="handleEditImageSelection" />
            <div v-if="editImageItems.length > 0" class="forum-image-preview-grid" aria-label="Editable image preview order">
              <article
                v-for="image in editImageItems"
                :key="image.id"
                class="forum-image-preview"
                :class="{ 'forum-image-preview--dragging': editDraggedImageId === image.id }"
                data-forum-edit-image-preview
                draggable="true"
                @dragstart="handleEditImageDragStart(image.id)"
                @dragend="handleEditImageDragEnd"
                @dragenter.prevent="handleEditImageDragOver(image.id)"
                @dragover.prevent="handleEditImageDragOver(image.id)"
                @drop.prevent="handleEditImageDrop"
              >
                <img v-if="image.previewUrl" :alt="`${image.name} preview`" class="forum-image-preview__image" :src="image.previewUrl" />
                <div v-else class="forum-image-preview__fallback">
                  <span class="material-symbols-outlined text-xl">image</span>
                </div>
                <button
                  class="forum-image-preview__delete"
                  type="button"
                  :aria-label="`Remove ${image.name}`"
                  @click="removeEditImage(image.id)"
                >
                  <span class="material-symbols-outlined text-base">close</span>
                </button>
                <span class="forum-image-preview__name" :title="image.name">{{ image.name }}</span>
              </article>
            </div>
          </div>
          <p v-if="editError" class="text-sm font-semibold text-error">{{ editError }}</p>
          <div class="flex flex-wrap gap-3">
            <button class="rounded-full bg-primary px-5 py-3 text-sm font-bold text-on-primary shadow-md transition-transform active:scale-95 disabled:opacity-60" :disabled="editSaving" type="submit">
              {{ editSaving ? "Saving..." : "Save Post" }}
            </button>
            <button class="rounded-full border border-outline-variant/30 px-5 py-3 text-sm font-bold text-on-surface-variant hover:bg-surface-container" :disabled="editSaving" type="button" @click="cancelEditPostComposer">
              Cancel
            </button>
          </div>
        </form>
      </section>
    </div>

    <div
      v-if="showDeletePostDialog"
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
              "{{ post.title }}" will be permanently removed from the community feed.
            </p>
          </div>
        </div>
        <p v-if="commentActionError" class="mt-4 text-sm font-semibold text-error">{{ commentActionError }}</p>
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
      v-if="pendingDeleteComment"
      class="forum-composer-window fixed inset-0 z-50 flex items-center justify-center px-4 py-6"
      data-forum-delete-comment-dialog
    >
      <div
        aria-label="Cancel comment deletion"
        class="forum-composer-window__scrim"
        role="button"
        tabindex="0"
        @click="cancelDeleteComment"
        @keyup.enter="cancelDeleteComment"
        @keyup.space.prevent="cancelDeleteComment"
      ></div>
      <section
        aria-labelledby="forum-delete-comment-title"
        aria-modal="true"
        class="forum-composer-panel w-full max-w-md rounded-3xl p-6 shadow-[0_24px_72px_rgba(43,48,47,0.24)]"
        role="dialog"
      >
        <div class="flex items-start gap-4">
          <div class="flex h-12 w-12 shrink-0 items-center justify-center rounded-full bg-error/10 text-error">
            <span class="material-symbols-outlined text-2xl">delete</span>
          </div>
          <div class="min-w-0">
            <p class="text-[10px] font-black uppercase tracking-[0.22em] text-error">Delete Comment</p>
            <h2 id="forum-delete-comment-title" class="mt-2 text-2xl font-black tracking-tight text-on-surface">Delete this comment?</h2>
            <p class="mt-3 text-sm leading-relaxed text-on-surface-variant">
              Comment #{{ pendingDeleteComment.id }} will be permanently removed from this discussion.
            </p>
          </div>
        </div>
        <p v-if="commentActionError" class="mt-4 text-sm font-semibold text-error">{{ commentActionError }}</p>
        <div class="mt-6 flex flex-wrap justify-end gap-3">
          <button
            class="rounded-full border border-outline-variant/30 px-5 py-3 text-sm font-bold text-on-surface-variant hover:bg-surface-container disabled:opacity-60"
            :disabled="isDeletingComment"
            type="button"
            @click="cancelDeleteComment"
          >
            Cancel
          </button>
          <button
            class="rounded-full bg-[#b31b25] px-5 py-3 text-sm font-bold text-[#ffefee] shadow-md transition-colors hover:bg-[#9f0519] active:scale-95 disabled:opacity-60"
            :disabled="isDeletingComment"
            type="button"
            @click="confirmDeleteComment"
          >
            {{ isDeletingComment ? "Deleting..." : "Delete comment" }}
          </button>
        </div>
      </section>
    </div>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, reactive, ref } from "vue";
import { RouterLink, useRoute, useRouter } from "vue-router";

import {
  createForumComment,
  deleteForumComment,
  deleteForumPost,
  fetchForumComments,
  fetchForumPost,
  parseForumImageUrls,
  trackForumPostLongView,
  toggleForumLike,
  updateForumPost,
  uploadForumImage,
} from "../../api/forum/forum.js";
import { resolveBackendUrl } from "../../api/http.js";
import AppHeader from "../../components/common/AppHeader.vue";
import ImagePreviewModal from "../../components/common/ImagePreviewModal.vue";
import { useAuth } from "../../composables/useAuth.js";
import { showErrorToast, showSuccessToast } from "../../composables/useToast.js";

const FORUM_LONG_VIEW_DELAY_MS = 15000;
const filledIconStyle = { fontVariationSettings: "'FILL' 1" };

const route = useRoute();
const router = useRouter();
const { isLoggedIn, token, user } = useAuth();

const post = ref(null);
const comments = ref([]);
const loading = ref(false);
const error = ref("");
const commentsLoading = ref(false);
const commentsError = ref("");
const commentDraft = ref("");
const commentSubmitting = ref(false);
const commentActionError = ref("");
const openReplyId = ref(null);
const replyDraft = ref("");
const replySubmitting = ref(false);
const showDeletePostDialog = ref(false);
const isDeletingPost = ref(false);
const pendingDeleteComment = ref(null);
const isDeletingComment = ref(false);
const showEditComposer = ref(false);
const editSaving = ref(false);
const editError = ref("");
const editImageInput = ref(null);
const editImageItems = ref([]);
const editDraggedImageId = ref("");
const selectedPostImageIndex = ref(0);
const imagePreviewOpen = ref(false);
const imagePreviewInitialIndex = ref(0);
let editImageIdCounter = 0;
let longViewTimerId = null;
let longViewTrackedPostId = null;

const editDraft = reactive({
  title: "",
  content: "",
});

const avatarAlt = computed(() => user.value?.username || "User avatar");
const avatarUrl = computed(() => resolveBackendUrl(user.value?.avatar_url || ""));
const pointsLabel = computed(() => {
  if (isLoggedIn.value && user.value?.current_points != null) {
    return `${user.value.current_points} pts`;
  }
  return "0 pts";
});

const postImageUrls = computed(() => parseForumImageUrls(post.value?.image_urls_json));
const activePostImageUrl = computed(() => postImageUrls.value[selectedPostImageIndex.value] || "");
const commentTree = computed(() => buildCommentTree(comments.value));
const isPostAuthor = computed(() => {
  if (!post.value || !user.value?.id) {
    return false;
  }

  return Number(user.value.id) === Number(post.value.author_id);
});

function isCommentAuthor(comment) {
  if (!user.value?.id || comment?.user_id == null) {
    return false;
  }

  return Number(user.value.id) === Number(comment.user_id);
}

function authorLabel(currentPost) {
  if (currentPost?.author_username) {
    return currentPost.author_username;
  }
  if (currentPost?.username) {
    return currentPost.username;
  }
  if (user.value?.id && Number(user.value.id) === Number(currentPost?.author_id) && user.value?.username) {
    return user.value.username;
  }
  return `User #${currentPost?.author_id ?? "Unknown"}`;
}

function authorInitials(currentPost) {
  const name = authorLabel(currentPost).replace(/^User #/i, "").trim();
  const parts = name.split(/\s+/).filter(Boolean);
  if (parts.length >= 2) {
    return `${parts[0][0]}${parts[1][0]}`.toUpperCase();
  }
  return name.slice(0, 2).toUpperCase() || "CS";
}

function authorAvatarUrl(currentPost) {
  if (currentPost?.author_avatar_url) {
    return resolveBackendUrl(currentPost.author_avatar_url);
  }
  if (currentPost?.avatar_url) {
    return resolveBackendUrl(currentPost.avatar_url);
  }
  if (user.value?.id && Number(user.value.id) === Number(currentPost?.author_id) && user.value?.avatar_url) {
    return resolveBackendUrl(user.value.avatar_url);
  }
  return "";
}

function commentAuthorLabel(comment) {
  if (comment?.author_username) {
    return comment.author_username;
  }
  if (comment?.username) {
    return comment.username;
  }
  if (user.value?.id && Number(user.value.id) === Number(comment?.user_id) && user.value?.username) {
    return user.value.username;
  }
  return `User #${comment?.user_id ?? "Unknown"}`;
}

function commentInitials(comment) {
  const name = commentAuthorLabel(comment).replace(/^User #/i, "").trim();
  const parts = name.split(/\s+/).filter(Boolean);
  if (parts.length >= 2) {
    return `${parts[0][0]}${parts[1][0]}`.toUpperCase();
  }
  return name.slice(0, 2).toUpperCase() || "CS";
}

function commentAvatarUrl(comment) {
  if (comment?.author_avatar_url) {
    return resolveBackendUrl(comment.author_avatar_url);
  }
  if (comment?.avatar_url) {
    return resolveBackendUrl(comment.avatar_url);
  }
  if (user.value?.id && Number(user.value.id) === Number(comment?.user_id) && user.value?.avatar_url) {
    return resolveBackendUrl(user.value.avatar_url);
  }
  return "";
}

function formatDate(value) {
  if (!value) {
    return "Unknown time";
  }

  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString();
}

function summarize(content, limit = 160) {
  if (!content) {
    return "";
  }

  return content.length > limit ? `${content.slice(0, limit)}...` : content;
}

function buildCommentTree(list) {
  if (!Array.isArray(list)) {
    return [];
  }

  const byParentId = new Map();
  for (const comment of list) {
    const parentId = comment.parent_comment_id ?? null;
    const bucket = byParentId.get(parentId) || [];
    bucket.push(comment);
    byParentId.set(parentId, bucket);
  }

  const walk = (parentId, depth) => {
    const entries = byParentId.get(parentId) || [];
    return entries.flatMap((comment) => [
      {
        ...comment,
        reply_depth: depth,
      },
      ...walk(comment.id, depth + 1),
    ]);
  };

  return walk(null, 0);
}

function requireLogin() {
  if (isLoggedIn.value) {
    return true;
  }

  router.push("/login");
  return false;
}

function normalizeSelectedPostImageIndex() {
  if (selectedPostImageIndex.value >= postImageUrls.value.length) {
    selectedPostImageIndex.value = 0;
  }
}

function showPreviousPostImage() {
  const imageCount = postImageUrls.value.length;
  if (imageCount <= 1) {
    return;
  }
  selectedPostImageIndex.value = (selectedPostImageIndex.value - 1 + imageCount) % imageCount;
}

function showNextPostImage() {
  const imageCount = postImageUrls.value.length;
  if (imageCount <= 1) {
    return;
  }
  selectedPostImageIndex.value = (selectedPostImageIndex.value + 1) % imageCount;
}

function openPostImagePreview(index) {
  imagePreviewInitialIndex.value = index;
  imagePreviewOpen.value = true;
}

function makeEditImageId() {
  editImageIdCounter += 1;
  return `forum-edit-image-${Date.now()}-${editImageIdCounter}`;
}

function createObjectPreviewUrl(file) {
  if (typeof URL === "undefined" || typeof URL.createObjectURL !== "function") {
    return "";
  }
  return URL.createObjectURL(file);
}

function revokeObjectPreviewUrl(previewUrl) {
  if (!previewUrl || typeof URL === "undefined" || typeof URL.revokeObjectURL !== "function") {
    return;
  }
  URL.revokeObjectURL(previewUrl);
}

function existingImageName(url, index) {
  const basename = String(url || "").split("/").filter(Boolean).pop() || "";
  return basename || `existing-image-${index + 1}`;
}

function clearEditImages() {
  editImageItems.value.forEach((image) => {
    if (image.kind === "new") {
      revokeObjectPreviewUrl(image.previewUrl);
    }
  });
  editImageItems.value = [];
  editDraggedImageId.value = "";
}

function hydrateEditImages(currentPost) {
  clearEditImages();
  editImageItems.value = parseForumImageUrls(currentPost?.image_urls_json).map((url, index) => ({
    id: makeEditImageId(),
    kind: "existing",
    url,
    previewUrl: resolveBackendUrl(url),
    name: existingImageName(url, index),
  }));
}

function openEditPostComposer() {
  if (!post.value || !requireLogin() || !isPostAuthor.value) {
    return;
  }

  editError.value = "";
  editDraft.title = post.value.title || "";
  editDraft.content = post.value.content || "";
  hydrateEditImages(post.value);
  showEditComposer.value = true;
}

function cancelEditPostComposer() {
  if (editSaving.value) {
    return;
  }

  showEditComposer.value = false;
  editError.value = "";
  clearEditImages();
  if (editImageInput.value) {
    editImageInput.value.value = "";
  }
}

function handleEditImageSelection(event) {
  const files = Array.from(event.target?.files || []).filter((file) => file.type.startsWith("image/"));
  if (files.length === 0) {
    return;
  }

  editImageItems.value.push(
    ...files.map((file) => ({
      id: makeEditImageId(),
      kind: "new",
      file,
      previewUrl: createObjectPreviewUrl(file),
      name: file.name,
    })),
  );
  if (editImageInput.value) {
    editImageInput.value.value = "";
  }
}

function removeEditImage(imageId) {
  const image = editImageItems.value.find((item) => item.id === imageId);
  if (image?.kind === "new") {
    revokeObjectPreviewUrl(image.previewUrl);
  }
  editImageItems.value = editImageItems.value.filter((item) => item.id !== imageId);
  if (editDraggedImageId.value === imageId) {
    editDraggedImageId.value = "";
  }
}

function handleEditImageDragStart(imageId) {
  editDraggedImageId.value = imageId;
}

function handleEditImageDragEnd() {
  editDraggedImageId.value = "";
}

function handleEditImageDragOver(targetImageId) {
  const sourceImageId = editDraggedImageId.value;
  if (!sourceImageId || sourceImageId === targetImageId) {
    return;
  }

  const nextImages = [...editImageItems.value];
  const sourceIndex = nextImages.findIndex((image) => image.id === sourceImageId);
  const targetIndex = nextImages.findIndex((image) => image.id === targetImageId);
  if (sourceIndex === -1 || targetIndex === -1) {
    return;
  }

  const [movedImage] = nextImages.splice(sourceIndex, 1);
  nextImages.splice(targetIndex, 0, movedImage);
  editImageItems.value = nextImages;
}

function handleEditImageDrop() {
  editDraggedImageId.value = "";
}

function readFileAsDataUrl(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(String(reader.result || ""));
    reader.onerror = () => reject(new Error(`Failed to read ${file.name}.`));
    reader.readAsDataURL(file);
  });
}

async function resolveEditImageUrlsForSave() {
  const urls = [];
  for (const image of editImageItems.value) {
    if (image.kind === "existing") {
      urls.push(image.url);
      continue;
    }

    const imageDataUrl = await readFileAsDataUrl(image.file);
    const result = await uploadForumImage(imageDataUrl, token.value);
    if (result?.url) {
      urls.push(result.url);
    }
  }
  return urls;
}

async function saveEditedPost() {
  if (!post.value || editSaving.value) {
    return;
  }

  editSaving.value = true;
  editError.value = "";
  try {
    const imageUrls = await resolveEditImageUrlsForSave();
    const updated = await updateForumPost(
      {
        postId: post.value.id,
        title: editDraft.title,
        content: editDraft.content,
        imageUrlsJson: imageUrls.length > 0 ? JSON.stringify(imageUrls) : null,
      },
      token.value,
    );
    post.value = { ...post.value, ...updated };
    normalizeSelectedPostImageIndex();
    showEditComposer.value = false;
    clearEditImages();
    showSuccessToast("Post updated", "Your changes have been saved.");
  } catch (err) {
    editError.value = err instanceof Error ? err.message : "Failed to save post.";
    showErrorToast("Update failed", editError.value);
  } finally {
    editSaving.value = false;
  }
}

async function loadPost() {
  loading.value = true;
  error.value = "";
  clearLongViewTimer();
  try {
    post.value = await fetchForumPost(route.params.id, token.value || null);
    selectedPostImageIndex.value = 0;
    scheduleLongViewTracking();
  } catch (err) {
    error.value = err instanceof Error ? err.message : "Failed to load post.";
    post.value = null;
  } finally {
    loading.value = false;
  }
}

async function loadComments() {
  commentsLoading.value = true;
  commentsError.value = "";
  try {
    const payload = await fetchForumComments(route.params.id, token.value || null);
    comments.value = Array.isArray(payload) ? payload : payload?.items || [];
  } catch (err) {
    commentsError.value = err instanceof Error ? err.message : "Failed to load comments.";
    comments.value = [];
  } finally {
    commentsLoading.value = false;
  }
}

function openDeletePostDialog() {
  if (!post.value || !requireLogin()) {
    return;
  }

  commentActionError.value = "";
  showDeletePostDialog.value = true;
}

function cancelDeletePost() {
  if (isDeletingPost.value) {
    return;
  }

  showDeletePostDialog.value = false;
  commentActionError.value = "";
}

async function confirmDeletePost() {
  if (!post.value || isDeletingPost.value) {
    return;
  }

  isDeletingPost.value = true;
  commentActionError.value = "";
  try {
    await deleteForumPost(post.value.id, token.value);
    showDeletePostDialog.value = false;
    showSuccessToast("Post deleted", "The forum post has been removed.");
    router.push("/forum");
  } catch (err) {
    commentActionError.value = err instanceof Error ? err.message : "Failed to delete.";
    showErrorToast("Delete failed", commentActionError.value);
  } finally {
    isDeletingPost.value = false;
  }
}

async function submitComment() {
  commentActionError.value = "";
  if (!requireLogin()) {
    return;
  }

  commentSubmitting.value = true;
  try {
    await createForumComment(
      {
        postId: route.params.id,
        content: commentDraft.value,
      },
      token.value,
    );
    commentDraft.value = "";
    await loadComments();
    showSuccessToast("Comment posted", "Your comment was added to the discussion.");
  } catch (err) {
    commentActionError.value = err instanceof Error ? err.message : "Failed to submit comment.";
    showErrorToast("Comment failed", commentActionError.value);
  } finally {
    commentSubmitting.value = false;
  }
}

function toggleReplyComposer(commentId) {
  if (openReplyId.value === commentId) {
    openReplyId.value = null;
    replyDraft.value = "";
    return;
  }

  openReplyId.value = commentId;
  replyDraft.value = "";
}

async function submitReply(comment) {
  commentActionError.value = "";
  if (!requireLogin()) {
    return;
  }

  replySubmitting.value = true;
  try {
    await createForumComment(
      {
        postId: route.params.id,
        content: replyDraft.value,
        parentCommentId: comment.id,
      },
      token.value,
    );
    openReplyId.value = null;
    replyDraft.value = "";
    await loadComments();
    showSuccessToast("Reply posted", "Your reply was added to the thread.");
  } catch (err) {
    commentActionError.value = err instanceof Error ? err.message : "Failed to submit reply.";
    showErrorToast("Reply failed", commentActionError.value);
  } finally {
    replySubmitting.value = false;
  }
}

async function handlePostLike() {
  commentActionError.value = "";
  if (!requireLogin() || !post.value) {
    return;
  }

  try {
    const result = await toggleForumLike(
      {
        targetType: "post",
        targetId: post.value.id,
      },
      token.value,
    );
    post.value = {
      ...post.value,
      liked_by_user: result.liked,
      like_count: result.like_count ?? Math.max(0, (post.value.like_count || 0) + (result.liked ? 1 : -1)),
    };
  } catch (err) {
    commentActionError.value = err instanceof Error ? err.message : "Failed to update post like.";
  }
}

async function handleCommentLike(comment) {
  commentActionError.value = "";
  if (!requireLogin()) {
    return;
  }

  try {
    const result = await toggleForumLike(
      {
        targetType: "comment",
        targetId: comment.id,
      },
      token.value,
    );
    comments.value = comments.value.map((entry) =>
      entry.id === comment.id
        ? {
            ...entry,
            liked_by_user: result.liked,
            like_count: result.like_count ?? Math.max(0, (entry.like_count || 0) + (result.liked ? 1 : -1)),
          }
        : entry,
    );
  } catch (err) {
    commentActionError.value = err instanceof Error ? err.message : "Failed to update comment like.";
  }
}

function openDeleteCommentDialog(comment) {
  commentActionError.value = "";
  if (!requireLogin()) {
    return;
  }

  pendingDeleteComment.value = comment;
}

function cancelDeleteComment() {
  if (isDeletingComment.value) {
    return;
  }

  pendingDeleteComment.value = null;
  commentActionError.value = "";
}

async function confirmDeleteComment() {
  if (!pendingDeleteComment.value || isDeletingComment.value) {
    return;
  }

  isDeletingComment.value = true;
  commentActionError.value = "";
  try {
    await deleteForumComment(pendingDeleteComment.value.id, token.value);
    pendingDeleteComment.value = null;
    await loadComments();
    showSuccessToast("Comment deleted", "The comment has been removed.");
  } catch (err) {
    commentActionError.value = err instanceof Error ? err.message : "Failed to delete comment.";
    showErrorToast("Delete failed", commentActionError.value);
  } finally {
    isDeletingComment.value = false;
  }
}

function clearLongViewTimer() {
  if (longViewTimerId !== null) {
    window.clearTimeout(longViewTimerId);
    longViewTimerId = null;
  }
}

function scheduleLongViewTracking() {
  clearLongViewTimer();
  if (!post.value || !isLoggedIn.value || isPostAuthor.value) {
    return;
  }

  longViewTimerId = window.setTimeout(async () => {
    if (!post.value || longViewTrackedPostId === post.value.id) {
      return;
    }

    try {
      await trackForumPostLongView(post.value.id, token.value);
      longViewTrackedPostId = post.value.id;
    } catch {
      // Tracking failure should stay silent for the reader.
    } finally {
      longViewTimerId = null;
    }
  }, FORUM_LONG_VIEW_DELAY_MS);
}

onMounted(async () => {
  await Promise.all([loadPost(), loadComments()]);
});

onBeforeUnmount(() => {
  clearLongViewTimer();
  clearEditImages();
});
</script>

<style scoped src="../../styles/views/forum-view.css"></style>
