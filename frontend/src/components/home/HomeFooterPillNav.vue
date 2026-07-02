<template>
  <footer class="home-footer-pill bg-surface-container-low px-6 py-16" data-home-footer>
    <div class="mx-auto flex max-w-5xl flex-col gap-5">
      <section
        v-if="activeItem"
        class="home-pill-panel"
        role="tabpanel"
        :aria-labelledby="`footer-pill-${activeItem.key}`"
      >
        <div class="grid gap-6 lg:grid-cols-[minmax(0,1.2fr)_minmax(0,0.9fr)] lg:items-start">
          <div class="space-y-4">
            <p class="text-[11px] font-black uppercase tracking-[0.2em] text-primary/55">
              {{ activeItem.eyebrow }}
            </p>
            <h3 class="font-headline text-2xl font-black tracking-tight text-on-surface sm:text-3xl">
              {{ activeItem.title }}
            </h3>
            <p class="text-base leading-7 text-on-surface-variant">
              {{ activeItem.description }}
            </p>
          </div>

          <div class="grid gap-4">
            <article
              v-for="detail in activeItem.details"
              :key="detail.label"
              class="home-pill-panel__card"
            >
              <p class="text-[11px] font-black uppercase tracking-[0.18em] text-primary/55">
                {{ detail.label }}
              </p>
              <p class="mt-3 text-sm leading-6 text-on-surface-variant">
                {{ detail.copy }}
              </p>
            </article>
          </div>
        </div>
      </section>

      <div
        class="flex flex-col items-center justify-between gap-4 border-t border-primary/8 pt-8 text-xs font-black uppercase tracking-widest text-on-surface-variant/50 md:flex-row"
      >
        <span>&copy; 2026 CarbonSnap Laboratory. All actions verified.</span>
        <div class="home-pill-nav-wrap home-pill-nav-wrap--footer">
          <div class="home-pill-nav" role="tablist" aria-label="Footer information tabs">
            <button
              v-for="item in items"
              :key="item.key"
              class="home-pill-nav__item"
              :class="{ 'home-pill-nav__item--active': modelValue === item.key }"
              :aria-selected="modelValue === item.key"
              :tabindex="modelValue === item.key ? 0 : -1"
              role="tab"
              type="button"
              @click="$emit('update:modelValue', modelValue === item.key ? '' : item.key)"
            >
              {{ item.label }}
            </button>
          </div>
        </div>
      </div>
    </div>
  </footer>
</template>

<script setup>
import { computed } from "vue";

const props = defineProps({
  brand: {
    type: Object,
    required: true,
  },
  items: {
    type: Array,
    required: true,
  },
  modelValue: {
    type: String,
    required: true,
  },
});

defineEmits(["update:modelValue"]);

const activeItem = computed(() => {
  return props.items.find((item) => item.key === props.modelValue) ?? null;
});
</script>
