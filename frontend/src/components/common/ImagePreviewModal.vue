<template>
  <div class="image-preview-modal" data-image-preview-modal>
    <div
      aria-label="Close image preview"
      class="image-preview-modal__scrim"
      role="button"
      tabindex="0"
      @click="$emit('close')"
      @keyup.enter="$emit('close')"
      @keyup.space.prevent="$emit('close')"
    ></div>
    <section
      aria-modal="true"
      class="image-preview-modal__panel"
      role="dialog"
      :aria-label="title || 'Image preview'"
    >
      <div class="image-preview-modal__header">
        <div>
          <p class="image-preview-modal__eyebrow">Image Preview</p>
          <h2>{{ title || "Preview" }}</h2>
          <p v-if="safeImages.length > 1">{{ currentIndex + 1 }} / {{ safeImages.length }}</p>
        </div>
        <button class="image-preview-modal__close" type="button" @click="$emit('close')">
          Close
        </button>
      </div>

      <div class="image-preview-modal__stage">
        <button
          v-if="safeImages.length > 1"
          class="image-preview-modal__nav image-preview-modal__nav--prev"
          type="button"
          aria-label="Show previous image"
          data-image-preview-prev
          @click="showPrevious"
        >
          <span class="material-symbols-outlined">chevron_left</span>
        </button>
        <img
          v-if="activeImage"
          class="image-preview-modal__image"
          :src="activeImage"
          :alt="`${title || 'Preview'} image ${currentIndex + 1}`"
          data-image-preview-active
        />
        <button
          v-if="safeImages.length > 1"
          class="image-preview-modal__nav image-preview-modal__nav--next"
          type="button"
          aria-label="Show next image"
          data-image-preview-next
          @click="showNext"
        >
          <span class="material-symbols-outlined">chevron_right</span>
        </button>
      </div>

      <div v-if="safeImages.length > 1" class="image-preview-modal__thumbs">
        <button
          v-for="(image, index) in safeImages"
          :key="`${image}-${index}`"
          class="image-preview-modal__thumb"
          :class="{ 'image-preview-modal__thumb--active': index === currentIndex }"
          type="button"
          :aria-label="`Show image ${index + 1}`"
          data-image-preview-thumb
          @click="currentIndex = index"
        >
          <img :src="image" :alt="`${title || 'Preview'} thumbnail ${index + 1}`" />
        </button>
      </div>
    </section>
  </div>
</template>

<script setup>
import { computed, ref, watch } from "vue";

const props = defineProps({
  images: {
    type: Array,
    default: () => [],
  },
  initialIndex: {
    type: Number,
    default: 0,
  },
  title: {
    type: String,
    default: "",
  },
});

defineEmits(["close"]);

const currentIndex = ref(0);
const safeImages = computed(() => props.images.filter(Boolean));
const activeImage = computed(() => safeImages.value[currentIndex.value] || "");

watch(
  () => [safeImages.value.length, props.initialIndex],
  () => {
    const maxIndex = Math.max(0, safeImages.value.length - 1);
    currentIndex.value = Math.min(Math.max(0, Number(props.initialIndex) || 0), maxIndex);
  },
  { immediate: true },
);

function showPrevious() {
  if (safeImages.value.length <= 1) {
    return;
  }
  currentIndex.value = (currentIndex.value - 1 + safeImages.value.length) % safeImages.value.length;
}

function showNext() {
  if (safeImages.value.length <= 1) {
    return;
  }
  currentIndex.value = (currentIndex.value + 1) % safeImages.value.length;
}
</script>

<style scoped>
.image-preview-modal {
  position: fixed;
  inset: 0;
  z-index: 120;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px 16px;
  isolation: isolate;
}

.image-preview-modal__scrim {
  position: absolute;
  inset: 0;
  z-index: 0;
  background: rgba(14, 18, 17, 0.72);
}

.image-preview-modal__panel {
  position: relative;
  z-index: 1;
  display: grid;
  gap: 16px;
  width: min(980px, calc(100vw - 32px));
  max-height: calc(100dvh - 48px);
  overflow: hidden;
  border: 1px solid rgba(255, 255, 255, 0.18);
  border-radius: 28px;
  background: #ffffff;
  box-shadow: 0 28px 80px rgba(0, 0, 0, 0.34);
  padding: 18px;
}

.image-preview-modal__header {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  align-items: flex-start;
}

.image-preview-modal__header h2,
.image-preview-modal__header p {
  margin: 0;
}

.image-preview-modal__header h2 {
  color: #123f37;
  font-size: 1.25rem;
}

.image-preview-modal__eyebrow {
  color: #0f766e;
  font-size: 0.68rem;
  font-weight: 900;
  letter-spacing: 0.16em;
  text-transform: uppercase;
}

.image-preview-modal__close {
  border: 1px solid rgba(15, 23, 42, 0.12);
  border-radius: 999px;
  background: #f1f5f3;
  color: #39504b;
  cursor: pointer;
  font-weight: 800;
  padding: 9px 14px;
}

.image-preview-modal__stage {
  position: relative;
  display: grid;
  place-items: center;
  min-height: min(64dvh, 620px);
  overflow: hidden;
  border-radius: 22px;
  background: #111816;
}

.image-preview-modal__image {
  display: block;
  width: 100%;
  max-height: min(64dvh, 620px);
  object-fit: contain;
}

.image-preview-modal__nav {
  position: absolute;
  top: 50%;
  z-index: 2;
  display: grid;
  width: 44px;
  height: 44px;
  transform: translateY(-50%);
  place-items: center;
  border: 0;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.88);
  color: #102f2b;
  cursor: pointer;
  box-shadow: 0 10px 28px rgba(0, 0, 0, 0.24);
}

.image-preview-modal__nav--prev {
  left: 16px;
}

.image-preview-modal__nav--next {
  right: 16px;
}

.image-preview-modal__thumbs {
  display: flex;
  gap: 10px;
  overflow-x: auto;
  padding-bottom: 2px;
}

.image-preview-modal__thumb {
  width: 76px;
  height: 64px;
  flex: 0 0 auto;
  overflow: hidden;
  border: 2px solid transparent;
  border-radius: 14px;
  background: #edf2f0;
  cursor: pointer;
  opacity: 0.72;
  padding: 0;
}

.image-preview-modal__thumb--active {
  border-color: #0f766e;
  opacity: 1;
}

.image-preview-modal__thumb img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

@media (max-width: 640px) {
  .image-preview-modal__panel {
    border-radius: 22px;
    padding: 14px;
  }

  .image-preview-modal__header {
    flex-direction: column;
  }
}
</style>
