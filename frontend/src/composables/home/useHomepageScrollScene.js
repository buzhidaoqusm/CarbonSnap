import { computed, onBeforeUnmount, onMounted, ref, unref } from "vue";

const SCENE_WINDOWS = [
  { id: "intro", start: 0, end: 0.18 },
  { id: "dissolve", start: 0.18, end: 0.3 },
  { id: "capture", start: 0.3, end: 0.56 },
  { id: "insight", start: 0.56, end: 0.76 },
  { id: "impact", start: 0.76, end: 0.9 },
  { id: "outro", start: 0.91, end: 1 },
];

function clamp(value, min = 0, max = 1) {
  return Math.min(max, Math.max(min, value));
}

function getWindowProgress(progress, windowRange) {
  const duration = Math.max(windowRange.end - windowRange.start, 0.001);
  return clamp((progress - windowRange.start) / duration);
}

export function useHomepageScrollScene(stageRootRef) {
  const progress = ref(0);
  const isReducedMotion = ref(false);
  const isCompactViewport = ref(false);

  let gsapContext = null;
  let scrollTriggerApi = null;

  const scenePhase = computed(
    () =>
      SCENE_WINDOWS.find(
        (windowRange) =>
          progress.value >= windowRange.start && progress.value <= windowRange.end,
      )?.id ?? "outro",
  );

  const activeChapter = computed(() => {
    if (scenePhase.value === "dissolve") {
      return "intro";
    }

    return scenePhase.value;
  });

  const chapterProgress = computed(() => {
    const currentWindow =
      SCENE_WINDOWS.find((windowRange) => windowRange.id === scenePhase.value) ??
      SCENE_WINDOWS[0];

    return getWindowProgress(progress.value, currentWindow);
  });

  function syncCapabilityFlags() {
    isReducedMotion.value = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    isCompactViewport.value = window.innerWidth < 900;
  }

  async function setupSceneController() {
    const stageRoot = unref(stageRootRef);

    if (!stageRoot) {
      return;
    }

    syncCapabilityFlags();

    if (isReducedMotion.value) {
      progress.value = 0;
      return;
    }

    const [{ default: gsap }, { ScrollTrigger }] = await Promise.all([
      import("gsap"),
      import("gsap/ScrollTrigger"),
    ]);

    scrollTriggerApi = ScrollTrigger;
    gsap.registerPlugin(ScrollTrigger);

    gsapContext = gsap.context(() => {
      ScrollTrigger.create({
        trigger: stageRoot,
        start: "top top",
        end: "bottom bottom",
        scrub: 0.75,
        invalidateOnRefresh: true,
        onUpdate: (self) => {
          progress.value = clamp(self.progress);
        },
      });
    }, stageRoot);
  }

  onMounted(() => {
    setupSceneController();
    window.addEventListener("resize", syncCapabilityFlags, { passive: true });
  });

  onBeforeUnmount(() => {
    window.removeEventListener("resize", syncCapabilityFlags);
    gsapContext?.revert();
    scrollTriggerApi?.getAll().forEach((trigger) => {
      if (trigger.trigger === unref(stageRootRef)) {
        trigger.kill();
      }
    });
  });

  return {
    activeChapter,
    chapterProgress,
    isCompactViewport,
    isReducedMotion,
    progress,
    scenePhase,
  };
}
