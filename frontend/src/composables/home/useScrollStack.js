import { onBeforeUnmount, onMounted, ref } from "vue";

export function useScrollStack() {
  const activeIndex = ref(0);
  const itemRefs = ref([]);
  let observer = null;

  function setItemRef(el, index) {
    if (!el) {
      return;
    }
    itemRefs.value[index] = el;
  }

  onMounted(() => {
    if (typeof window === "undefined" || typeof window.IntersectionObserver !== "function") {
      return;
    }

    observer = new window.IntersectionObserver(
      (entries) => {
        const visible = entries
          .filter((entry) => entry.isIntersecting)
          .sort((a, b) => b.intersectionRatio - a.intersectionRatio)[0];

        if (!visible) {
          return;
        }

        const index = Number(visible.target?.dataset?.index || 0);
        if (!Number.isNaN(index)) {
          activeIndex.value = index;
        }
      },
      {
        threshold: [0.35, 0.6, 0.85],
      },
    );

    itemRefs.value.forEach((el) => {
      if (el) {
        observer.observe(el);
      }
    });
  });

  onBeforeUnmount(() => {
    observer?.disconnect();
    observer = null;
  });

  return {
    activeIndex,
    setItemRef,
  };
}
