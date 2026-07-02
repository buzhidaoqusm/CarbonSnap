import { nextTick, onBeforeUnmount, onMounted, ref } from "vue";
import { useRouter } from "vue-router";
import { gsap } from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";

gsap.registerPlugin(ScrollTrigger);

export function useHomepageStageMotion(rootRef, headerState) {
  const router = useRouter();
  const loaderProgress = ref(0);
  const loadingComplete = ref(false);
  const introPlaybackComplete = ref(false);
  const isNavigating = ref(false);
  const currentStage = ref("loader");

  let context = null;
  let reduceMotionQuery = null;
  let loaderDone = false;
  let introAdvancing = false;
  let introPlaybackStarted = false;
  let introVisualStarted = false;
  let introVisualTimeline = null;
  let scrollLocked = false;
  let ctaAdvancing = false;
  let touchStartY = null;

  const prefersReducedMotion = () => reduceMotionQuery?.matches === true;

  const lockScroll = () => {
    scrollLocked = true;
    document.documentElement.style.overflowY = "hidden";
    document.body.style.overflowY = "hidden";
    document.documentElement.style.height = "100%";
    document.body.style.height = "100%";
  };

  const unlockScroll = () => {
    scrollLocked = false;
    document.documentElement.style.overflowY = "";
    document.body.style.overflowY = "";
    document.documentElement.style.height = "";
    document.body.style.height = "";
  };

  const preventLockedScroll = (event) => {
    if (!scrollLocked) {
      return;
    }

    event.preventDefault();
  };

  const advanceToCta = () => {
    if (
      ctaAdvancing
      || currentStage.value !== "intro"
      || !introPlaybackComplete.value
      || !rootRef.value
    ) {
      return;
    }

    const ctaStage = rootRef.value.querySelector('[data-home-stage="cta"]');

    if (!ctaStage) {
      return;
    }

    ctaAdvancing = true;
    currentStage.value = "cta";
    lockScroll();
    syncHeaderState(true);
    ctaStage.scrollIntoView({ behavior: prefersReducedMotion() ? "auto" : "smooth", block: "start" });
    window.setTimeout(() => {
      ctaAdvancing = false;
    }, prefersReducedMotion() ? 80 : 850);
  };

  const handleWheel = (event) => {
    if (scrollLocked || currentStage.value === "cta" || currentStage.value === "intro" || event.deltaY <= 0) {
      event.preventDefault();
      return;
    }

    event.preventDefault();
  };

  const preventLockedKeyScroll = (event) => {
    const blockedKeys = [
      "ArrowDown",
      "ArrowUp",
      "PageDown",
      "PageUp",
      "Home",
      "End",
      " ",
    ];

    if (!blockedKeys.includes(event.key)) {
      return;
    }

    if (scrollLocked || currentStage.value === "cta") {
      event.preventDefault();
      return;
    }

    if (event.key === "ArrowDown" || event.key === "PageDown" || event.key === " ") {
      event.preventDefault();
      return;
    }

    event.preventDefault();
  };

  const handleTouchStart = (event) => {
    touchStartY = event.touches?.[0]?.clientY ?? null;
  };

  const handleTouchMove = (event) => {
    const currentY = event.touches?.[0]?.clientY;

    if (touchStartY == null || currentY == null) {
      if (scrollLocked || currentStage.value === "cta") {
        event.preventDefault();
      }
      return;
    }

    const delta = currentY - touchStartY;

    if (scrollLocked || currentStage.value === "cta" || currentStage.value === "intro" || delta >= 0) {
      event.preventDefault();
      return;
    }

    event.preventDefault();
    touchStartY = currentY;
  };

  const finishLoader = () => {
    if (loaderDone) {
      return;
    }

    loaderDone = true;
    loaderProgress.value = 100;
    loadingComplete.value = true;
  };

  const syncHeaderState = (isSolid) => {
    if (!isNavigating.value) {
      headerState.value = isSolid ? "solid" : "overlay";
    }
  };

  const stopIntroVisualSequence = () => {
    introVisualTimeline?.kill();
    introVisualTimeline = null;
  };

  const setIntroVisualPhase = (elements, activePhase) => {
    elements.phases.forEach((phase) => {
      phase.classList.toggle("is-active", phase.dataset.introPhase === activePhase);
    });

    elements.labels.forEach((label) => {
      label.classList.toggle("is-active", label.dataset.introPhaseLabel === activePhase);
    });
  };

  const getIntroVisualElements = (rootElement) => {
    const sequence = rootElement.querySelector("[data-intro-sequence]");

    if (!sequence) {
      return null;
    }

    const sortingPhase = sequence.querySelector('[data-intro-phase="sorting"]');
    const mapPhase = sequence.querySelector('[data-intro-phase="map"]');
    const scorePhase = sequence.querySelector('[data-intro-phase="score"]');

    return {
      sequence,
      phases: sequence.querySelectorAll("[data-intro-phase]"),
      labels: sequence.querySelectorAll("[data-intro-phase-label]"),
      sortingPhase,
      mapPhase,
      scorePhase,
      sortingCard: sortingPhase?.querySelector(".intro-stage__object-card"),
      scanLine: sortingPhase?.querySelector(".intro-stage__scan-line"),
      objectTags: sortingPhase?.querySelectorAll(".intro-stage__object-tag"),
      mapCard: mapPhase?.querySelector(".intro-stage__map-card"),
      mapPins: mapPhase?.querySelectorAll(".intro-stage__map-pin"),
      routePath: sequence.querySelector("[data-intro-route]"),
      scoreCard: scorePhase?.querySelector(".intro-stage__score-card"),
      scoreRing: sequence.querySelector("[data-intro-score-ring]"),
      pointsValue: sequence.querySelector("[data-intro-points]"),
      carbonValue: sequence.querySelector("[data-intro-carbon]"),
    };
  };

  const playIntroVisualSequence = (rootElement) => {
    if (!rootElement || introVisualStarted) {
      return;
    }

    const elements = getIntroVisualElements(rootElement);

    if (!elements || !elements.sortingPhase || !elements.mapPhase || !elements.scorePhase) {
      return;
    }

    stopIntroVisualSequence();
    introVisualStarted = true;

    if (prefersReducedMotion()) {
      setIntroVisualPhase(elements, "sorting");

      if (elements.routePath) {
        gsap.set(elements.routePath, {
          strokeDashoffset: 0,
          opacity: 1,
        });
      }

      if (elements.scoreRing) {
        gsap.set(elements.scoreRing, {
          strokeDashoffset: 86,
          opacity: 1,
        });
      }

      if (elements.pointsValue) {
        elements.pointsValue.textContent = "+24 pts";
      }

      if (elements.carbonValue) {
        elements.carbonValue.textContent = "-1.8 kg";
      }

      return;
    }

    const scoreState = {
      points: 0,
      carbon: 0,
    };

    const setScoreText = () => {
      if (elements.pointsValue) {
        elements.pointsValue.textContent = `+${Math.round(scoreState.points)} pts`;
      }

      if (elements.carbonValue) {
        elements.carbonValue.textContent = `-${scoreState.carbon.toFixed(1)} kg`;
      }
    };

    gsap.set(elements.phases, {
      opacity: 0,
      y: 18,
      scale: 0.975,
    });

    gsap.set(elements.labels, {
      opacity: 0.46,
    });

    gsap.set(elements.sortingPhase, {
      opacity: 1,
      y: 0,
      scale: 1,
    });

    if (elements.scanLine) {
      gsap.set(elements.scanLine, {
        y: 0,
        opacity: 0.72,
      });
    }

    if (elements.objectTags) {
      gsap.set(elements.objectTags, {
        opacity: 0,
        y: 8,
      });
    }

    if (elements.routePath) {
      gsap.set(elements.routePath, {
        strokeDasharray: 300,
        strokeDashoffset: 300,
        opacity: 0.68,
      });
    }

    if (elements.scoreRing) {
      gsap.set(elements.scoreRing, {
        strokeDasharray: 276,
        strokeDashoffset: 276,
      });
    }

    if (elements.pointsValue) {
      elements.pointsValue.textContent = "+0 pts";
    }

    if (elements.carbonValue) {
      elements.carbonValue.textContent = "-0.0 kg";
    }

    const timeline = gsap.timeline({
      defaults: {
        ease: "power2.inOut",
      },
      repeat: -1,
      repeatDelay: 0.45,
    });

    introVisualTimeline = timeline;

    timeline
      .call(() => setIntroVisualPhase(elements, "sorting"))
      .to(elements.sortingPhase, {
        opacity: 1,
        y: 0,
        scale: 1,
        duration: 0.55,
      })
      .to(
        elements.sortingCard,
        {
          y: 0,
          scale: 1,
          rotate: 0,
          duration: 0.55,
        },
        "<",
      )
      .to(
        elements.scanLine,
        {
          y: 128,
          opacity: 1,
          duration: 1.25,
          ease: "power1.inOut",
        },
        "<0.06",
      )
      .to(
        elements.objectTags,
        {
          opacity: 1,
          y: 0,
          stagger: 0.08,
          duration: 0.32,
        },
        "<0.12",
      )
      .to(
        elements.sortingCard,
        {
          y: -4,
          scale: 1.01,
          duration: 0.45,
        },
        ">-0.16",
      )
      .to(
        elements.sortingPhase,
        {
          opacity: 0.22,
          y: -10,
          scale: 0.985,
          duration: 0.42,
        },
        ">-0.06",
      )
      .call(() => setIntroVisualPhase(elements, "map"))
      .to(
        elements.mapPhase,
        {
          opacity: 1,
          y: 0,
          scale: 1,
          duration: 0.56,
        },
        "<",
      )
      .to(
        elements.mapCard,
        {
          y: 0,
          scale: 1,
          rotate: 0,
          duration: 0.58,
        },
        "<",
      )
      .to(
        elements.mapPins,
        {
          scale: 1,
          opacity: 1,
          stagger: 0.1,
          duration: 0.35,
        },
        "<0.1",
      )
      .to(
        elements.routePath,
        {
          strokeDashoffset: 0,
          opacity: 1,
          duration: 1.1,
        },
        "<0.05",
      )
      .to(
        elements.mapCard,
        {
          y: -4,
          scale: 1.01,
          duration: 0.46,
        },
        ">-0.1",
      )
      .to(
        elements.mapPhase,
        {
          opacity: 0.22,
          y: -8,
          scale: 0.985,
          duration: 0.42,
        },
        ">-0.08",
      )
      .call(() => setIntroVisualPhase(elements, "score"))
      .to(
        elements.scorePhase,
        {
          opacity: 1,
          y: 0,
          scale: 1,
          duration: 0.56,
        },
        "<",
      )
      .to(
        elements.scoreCard,
        {
          y: 0,
          scale: 1,
          rotate: 0,
          duration: 0.58,
        },
        "<",
      )
      .to(
        elements.scoreRing,
        {
          strokeDashoffset: 86,
          duration: 1.1,
        },
        "<0.04",
      )
      .to(
        scoreState,
        {
          points: 24,
          carbon: 1.8,
          duration: 1.05,
          ease: "power1.out",
          onUpdate: setScoreText,
        },
        "<0.05",
      )
      .to(
        elements.scoreCard,
        {
          y: -3,
          scale: 1.01,
          duration: 0.46,
        },
        ">-0.08",
      )
      .to(
        elements.scorePhase,
        {
          opacity: 0.26,
          y: -6,
          scale: 0.985,
          duration: 0.4,
        },
        ">-0.08",
      )
      .call(() => setIntroVisualPhase(elements, "sorting"));
  };

  const handleEnterIntro = () => {
    if (!loadingComplete.value || introAdvancing || !rootRef.value) {
      return;
    }

    const introStage = rootRef.value.querySelector('[data-home-stage="intro"]');
    const loaderContent = rootRef.value.querySelector(".loader-stage__content");

    if (!introStage || !loaderContent) {
      return;
    }

    introAdvancing = true;

    if (prefersReducedMotion()) {
      syncHeaderState(true);
      introStage.scrollIntoView({ behavior: "auto", block: "start" });
      currentStage.value = "intro";
      playIntroVisualSequence(rootRef.value);
      introPlaybackComplete.value = true;
      window.setTimeout(() => {
        introAdvancing = false;
      }, 120);
      return;
    }

    const timeline = gsap.timeline({
      defaults: {
        ease: "power2.out",
      },
      onComplete: () => {
        syncHeaderState(true);
        currentStage.value = "intro";
        introStage.scrollIntoView({ behavior: "smooth", block: "start" });
        window.setTimeout(() => {
          playIntroVisualSequence(rootRef.value);
          playIntroStory(rootRef.value);
        }, 680);
        window.setTimeout(() => {
          introAdvancing = false;
        }, 750);
      },
    });

    timeline
      .to(loaderContent, {
        y: -30,
        opacity: 0.14,
        duration: 0.45,
      })
      .to(
        loaderContent,
        {
          y: 0,
          opacity: 1,
          duration: 0.01,
        },
        "+=0.02",
      );
  };

  const playIntroStory = (rootElement) => {
    if (!rootElement || introPlaybackStarted || introPlaybackComplete.value) {
      return;
    }

    const windowElement = rootElement.querySelector("[data-intro-story-window]");
    const trackElement = rootElement.querySelector("[data-intro-story-track]");

    if (!windowElement || !trackElement) {
      introPlaybackComplete.value = true;
      return;
    }

    const viewportHeight = windowElement.clientHeight;
    const contentHeight = trackElement.scrollHeight;
    const maxOffset = Math.max(contentHeight - viewportHeight, 0);

    if (maxOffset <= 6 || prefersReducedMotion()) {
      introPlaybackComplete.value = true;
      return;
    }

    introPlaybackStarted = true;

    gsap.timeline({
      defaults: {
        ease: "power2.inOut",
      },
      onComplete: () => {
        introPlaybackComplete.value = true;
      },
    })
      .to(trackElement, {
        y: -maxOffset,
        duration: 4.8,
        ease: "power1.inOut",
      });
  };

  const handleActivateCta = async () => {
    if (isNavigating.value || !rootRef.value) {
      return;
    }

    isNavigating.value = true;
    headerState.value = "solid";

    const ctaPanel = rootRef.value.querySelector(".cta-stage__panel");
    const page = rootRef.value.querySelector(".home-stage-page");

    if (prefersReducedMotion() || !ctaPanel || !page) {
      await router.push("/start");
      isNavigating.value = false;
      return;
    }

    await new Promise((resolve) => {
      const timeline = gsap.timeline({
        defaults: {
          ease: "power2.inOut",
        },
        onComplete: resolve,
      });

      timeline
        .to(ctaPanel, {
          y: -18,
          scale: 0.985,
          opacity: 0.82,
          duration: 0.32,
        })
        .to(
          page,
          {
            filter: "blur(16px)",
            opacity: 0.28,
            duration: 0.36,
          },
          0,
        );
    });

    await router.push("/start");
    isNavigating.value = false;
  };

  const setupLoaderTimeline = (rootElement) => {
    const loaderStage = rootElement.querySelector('[data-home-stage="loader"]');
    const progressCircle = rootElement.querySelector("[data-loader-progress]");

    if (!progressCircle || !loaderStage) {
      finishLoader();
      return;
    }

    const radius = Number(progressCircle.getAttribute("r")) || 86;
    const circumference = 2 * Math.PI * radius;

    gsap.set(progressCircle, {
      strokeDasharray: circumference,
      strokeDashoffset: circumference,
    });

    if (prefersReducedMotion()) {
      gsap.set(progressCircle, { strokeDashoffset: 0 });
      loaderStage.style.setProperty("--loader-progress", "1");
      finishLoader();
      return;
    }

    gsap.set(loaderStage, {
      "--loader-progress": 0,
    });

    const baseBg = loaderStage.querySelector(".loader-stage__bg--base");
    const midBg = loaderStage.querySelector(".loader-stage__bg--mid");
    const focusBg = loaderStage.querySelector(".loader-stage__bg--focus");
    const depthField = loaderStage.querySelector(".loader-stage__depth-field");
    const focusBloom = loaderStage.querySelector(".loader-stage__focus-bloom");
    const lights = loaderStage.querySelectorAll(".loader-stage__light");
    const mists = loaderStage.querySelectorAll(".loader-stage__mist");
    const particles = loaderStage.querySelectorAll(".loader-stage__particle");

    if (baseBg) {
      gsap.to(baseBg, {
        scale: 1.09,
        xPercent: 1.8,
        yPercent: -1.8,
        duration: 18,
        repeat: -1,
        yoyo: true,
        ease: "sine.inOut",
      });
    }

    if (midBg) {
      gsap.to(midBg, {
        scale: 1.18,
        xPercent: -2.1,
        yPercent: 1.4,
        duration: 24,
        repeat: -1,
        yoyo: true,
        ease: "sine.inOut",
      });
    }

    if (focusBg) {
      gsap.to(focusBg, {
        scale: 1.068,
        yPercent: -0.9,
        filter: "blur(8px)",
        duration: 7.8,
        repeat: -1,
        yoyo: true,
        ease: "sine.inOut",
      });
    }

    if (depthField) {
      gsap.to(depthField, {
        scale: 1.045,
        opacity: 0.34,
        filter: "blur(8px)",
        duration: 9.2,
        repeat: -1,
        yoyo: true,
        ease: "sine.inOut",
      });
    }

    if (focusBloom) {
      gsap.to(focusBloom, {
        scale: 1.035,
        opacity: 0.2,
        duration: 6.4,
        repeat: -1,
        yoyo: true,
        ease: "sine.inOut",
      });
    }

    lights.forEach((light, index) => {
      gsap.to(light, {
        scale: index === 0 ? 1.05 : 1.03,
        opacity: index === 0 ? 0.24 : 0.18,
        duration: index === 0 ? 7.4 : 10.2,
        repeat: -1,
        yoyo: true,
        ease: "sine.inOut",
      });
    });

    mists.forEach((mist, index) => {
      gsap.to(mist, {
        xPercent: index === 0 ? 7 : index === 1 ? -6 : 4,
        yPercent: index === 0 ? -4 : index === 1 ? 5 : -2,
        opacity: index === 0 ? 0.34 : index === 1 ? 0.22 : 0.18,
        duration: 11 + index * 2.3,
        repeat: -1,
        yoyo: true,
        ease: "sine.inOut",
      });
    });

    particles.forEach((particle, index) => {
      gsap.set(particle, {
        xPercent: 0,
        yPercent: 0,
        rotate: index % 2 === 0 ? -8 : 6,
      });

      gsap.to(particle, {
        yPercent: -180 - index * 8,
        xPercent: index % 3 === 0 ? 42 : index % 2 === 0 ? -26 : 30,
        rotate: index % 2 === 0 ? 24 : -18,
        opacity: 0,
        duration: 6.4 + index * 0.45,
        repeat: -1,
        repeatDelay: index * 0.1,
        ease: "none",
      });
    });

    const loaderCounter = { value: 0 };
    const timeline = gsap.timeline({
      defaults: {
        ease: "power2.inOut",
      },
      onComplete: finishLoader,
    });

    timeline
      .to(loaderCounter, {
        value: 100,
        duration: 2.35,
        ease: "power1.inOut",
        onUpdate: () => {
          loaderProgress.value = Math.round(loaderCounter.value);
          loaderStage.style.setProperty(
            "--loader-progress",
            (loaderCounter.value / 100).toFixed(3),
          );
        },
      })
      .to(
        progressCircle,
        {
          strokeDashoffset: 0,
          duration: 2.35,
        },
        0,
      );
  };

  const setupScrollScenes = (rootElement) => {
    const introStage = rootElement.querySelector('[data-home-stage="intro"]');
    const ctaStage = rootElement.querySelector('[data-home-stage="cta"]');

    if (!introStage || !ctaStage) {
      return;
    }

    const introElements = introStage.querySelectorAll('[data-animate="intro"]');
    const ctaElements = ctaStage.querySelectorAll('[data-animate="cta"]');

    if (prefersReducedMotion()) {
      gsap.set([...introElements, ...ctaElements], {
        clearProps: "all",
        opacity: 1,
        y: 0,
      });
      syncHeaderState(false);
      return;
    }

    gsap.to(introElements, {
      opacity: 1,
      y: 0,
      duration: 0.9,
      stagger: 0.1,
      ease: "power3.out",
      scrollTrigger: {
        trigger: introStage,
        start: "top 70%",
      },
    });

    gsap.to(ctaElements, {
      opacity: 1,
      y: 0,
      duration: 0.95,
      ease: "power3.out",
      scrollTrigger: {
        trigger: ctaStage,
        start: "top 72%",
      },
    });

    gsap.to(".intro-stage__frame", {
      yPercent: -5,
      ease: "none",
      scrollTrigger: {
        trigger: introStage,
        start: "top bottom",
        end: "bottom top",
        scrub: 1.1,
      },
    });

    gsap.to(".cta-stage__panel", {
      yPercent: -6,
      ease: "none",
      scrollTrigger: {
        trigger: ctaStage,
        start: "top bottom",
        end: "bottom top",
        scrub: 1.15,
      },
    });

    ScrollTrigger.create({
      trigger: introStage,
      start: "top top+=120",
      end: "bottom top",
      onEnter: () => syncHeaderState(true),
      onEnterBack: () => syncHeaderState(true),
      onLeaveBack: () => syncHeaderState(false),
    });
  };

  onMounted(async () => {
    reduceMotionQuery = window.matchMedia("(prefers-reduced-motion: reduce)");
    lockScroll();
    window.addEventListener("wheel", handleWheel, { passive: false });
    window.addEventListener("touchstart", handleTouchStart, { passive: true });
    window.addEventListener("touchmove", handleTouchMove, { passive: false });
    window.addEventListener("keydown", preventLockedKeyScroll);
    await nextTick();

    if (!rootRef.value) {
      return;
    }

    context = gsap.context(() => {
      setupLoaderTimeline(rootRef.value);
      setupScrollScenes(rootRef.value);
    }, rootRef);
  });

  onBeforeUnmount(() => {
    context?.revert();
    ScrollTrigger.getAll().forEach((trigger) => trigger.kill());
    stopIntroVisualSequence();
    introVisualStarted = false;
    window.removeEventListener("wheel", handleWheel);
    window.removeEventListener("touchstart", handleTouchStart);
    window.removeEventListener("touchmove", handleTouchMove);
    window.removeEventListener("keydown", preventLockedKeyScroll);
    unlockScroll();
  });

  return {
    loaderProgress,
    loadingComplete,
    introPlaybackComplete,
    isNavigating,
    handleEnterIntro,
    handleAdvanceToCta: advanceToCta,
    handleActivateCta,
  };
}
