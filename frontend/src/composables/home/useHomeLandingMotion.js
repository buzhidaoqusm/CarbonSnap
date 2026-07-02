import { onBeforeUnmount, onMounted, ref } from "vue";
import { gsap } from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";

gsap.registerPlugin(ScrollTrigger);

export function useHomeLandingMotion() {
  const rootRef = ref(null);
  let context = null;
  let resizeHandler = null;

  onMounted(() => {
    const root = rootRef.value;

    if (!root) {
      return;
    }

    const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

    if (reduceMotion) {
      root.dataset.reducedMotion = "true";
      root.querySelectorAll("[data-impact-card], [data-analysis-card], [data-audit-panel]").forEach((element) => {
        element.style.opacity = "1";
        element.style.transform = "none";
      });
      return;
    }

    context = gsap.context(() => {
      const sceneOne = root.querySelector("[data-scene-one]");
      const sceneTwo = root.querySelector("[data-scene-two]");
      const sceneThree = root.querySelector("[data-scene-three]");
      const sharedBottle = root.querySelector("[data-shared-bottle]");
      const auditFrontFixed = root.querySelector("[data-audit-front-fixed]");
      const CAMERA_CARD_BOTTLE_OPACITY = 0.34;
      const NORMAL_BOTTLE_OPACITY = 1;
      const ANALYSIS_BOTTLE_VISUAL_CENTER_OFFSET = 18;
      const analysisShadowBottleX = (bottleWidth, fallbackX) => {
        const shadow = sceneTwo?.querySelector("[data-analysis-shadow]");
        const rect = shadow?.getBoundingClientRect();

        if (!rect || rect.width === 0) {
          return fallbackX;
        }

        return rect.left + rect.width / 2 - bottleWidth / 2 + ANALYSIS_BOTTLE_VISUAL_CENTER_OFFSET;
      };

      const bottleState = (state) => {
        const vw = window.innerWidth;
        const vh = window.innerHeight;

        if (state === "analysis") {
          const width = Math.min(150, vw * 0.12);
          const height = Math.min(340, vh * 0.54);

          return {
            x: analysisShadowBottleX(width, vw * 0.2),
            y: vh * 0.24,
            width,
            height,
            rotate: -8,
            autoAlpha: 1,
          };
        }

        if (state === "analysisDrop") {
          const width = Math.min(150, vw * 0.12);
          const height = Math.min(340, vh * 0.54);

          return {
            x: analysisShadowBottleX(width, vw * 0.2),
            y: vh * 0.3,
            width,
            height,
            rotate: -10,
            autoAlpha: 1,
          };
        }

        if (state === "audit") {
          return {
            x: vw * 0.225,
            y: vh * 0.3,
            width: Math.min(140, vw * 0.11),
            height: Math.min(330, vh * 0.52),
            rotate: -8,
            autoAlpha: 1,
          };
        }

        if (state === "bin") {
          return {
            x: vw * 0.225,
            y: vh * 0.39,
            width: Math.min(112, vw * 0.09),
            height: Math.min(260, vh * 0.42),
            rotate: 6,
            autoAlpha: 0.76,
          };
        }

        return {
          x: vw * 0.34,
          y: vh * 0.515,
          width: Math.min(74, vw * 0.052),
          height: Math.min(244, vh * 0.32),
          rotate: 0,
          autoAlpha: 1,
        };
      };

      const heroCopy = root.querySelector("[data-hero-copy]");
      const heroCamera = root.querySelector("[data-hero-camera]");
      const shutterFlash = root.querySelector("[data-shutter-flash]");
      const shutterRing = root.querySelector("[data-shutter-ring]");
      const impactCards = gsap.utils.toArray("[data-impact-card]");
      const captureCaption = root.querySelector("[data-capture-caption]");

      const cameraBottleState = () => {
        const source = root.querySelector(".phone-camera__item--shared-source");
        const rect = source?.getBoundingClientRect();

        if (!rect || rect.width === 0 || rect.height === 0) {
          return bottleState("camera");
        }

        const height = rect.height;
        const width = height * (64 / 210);

        return {
          x: rect.left + rect.width / 2 - width / 2,
          y: rect.bottom - height + 7,
          width,
          height,
          rotate: 0,
          autoAlpha: 1,
        };
      };

      const syncSharedBottleToCamera = () => {
        gsap.set(sharedBottle, cameraBottleState());
      };

      const syncImpactCardsToWaste = () => {
        impactCards.forEach((card) => {
          const id = card.dataset.impactCard;
          const anchor =
            id === "plastic"
              ? sharedBottle
              : root.querySelector(`.phone-camera__item--${id} .waste-object`);
          const parent = card.offsetParent;

          if (!anchor || !parent) {
            return;
          }

          const anchorRect = anchor.getBoundingClientRect();
          const parentRect = parent.getBoundingClientRect();
          const cardWidth = card.offsetWidth || 150;
          const cardHeight = card.offsetHeight || 104;

          card.style.left = `${anchorRect.left + anchorRect.width / 2 - parentRect.left - cardWidth / 2}px`;
          card.style.top = `${anchorRect.top + anchorRect.height * 0.38 - parentRect.top - cardHeight / 2}px`;
        });
      };

      resizeHandler = () => {
        syncSharedBottleToCamera();
        syncImpactCardsToWaste();
      };
      window.addEventListener("resize", resizeHandler);

      gsap.set(impactCards, { autoAlpha: 0, scale: 0.94 });
      gsap.set(captureCaption, { autoAlpha: 0, y: 18 });
      gsap.set(shutterFlash, { autoAlpha: 0 });
      gsap.set(shutterRing, { autoAlpha: 0, scale: 0.45 });
      gsap.set(sharedBottle, { "--shared-bottle-image-opacity": NORMAL_BOTTLE_OPACITY });
      syncSharedBottleToCamera();
      syncImpactCardsToWaste();

      if (sceneOne) {
        const captureTimeline = gsap.timeline({
          defaults: { ease: "power2.inOut" },
          onUpdate: () => {
            syncSharedBottleToCamera();
            syncImpactCardsToWaste();
          },
          scrollTrigger: {
            trigger: sceneOne,
            start: "top top",
            end: "+=260%",
            pin: true,
            scrub: 0.9,
            anticipatePin: 1,
          },
        });

        captureTimeline
          .to(heroCopy, { autoAlpha: 0, y: -96, duration: 0.32 }, 0.04)
          .to(heroCamera, { y: -54, scale: 1.13, duration: 0.54 }, 0.03)
          .to(shutterFlash, { autoAlpha: 0.72, duration: 0.045 }, 0.44)
          .to(shutterFlash, { autoAlpha: 0, duration: 0.18 }, 0.5)
          .to(shutterRing, { autoAlpha: 0.9, scale: 1.36, duration: 0.18 }, 0.45)
          .to(shutterRing, { autoAlpha: 0, scale: 1.8, duration: 0.18 }, 0.6)
          .to(sharedBottle, {
            "--shared-bottle-image-opacity": CAMERA_CARD_BOTTLE_OPACITY,
            duration: 0.18,
          }, 0.62)
          .to(impactCards, { autoAlpha: 1, scale: 1, stagger: 0.045, duration: 0.28 }, 0.66)
          .to(captureCaption, { autoAlpha: 1, y: 0, duration: 0.24 }, 0.82);
      }

      if (sceneTwo) {
        const analysisCards = gsap.utils.toArray(sceneTwo.querySelectorAll("[data-analysis-card], [data-map-card]"));
        const analysisBottleZone = sceneTwo.querySelector("[data-analysis-bottle-zone]");
        const analysisContent = sceneTwo.querySelector("[data-analysis-content]");
        const analysisLeaves = gsap.utils.toArray(sceneTwo.querySelectorAll("[data-analysis-leaves] span"));

        gsap.set(analysisBottleZone, { autoAlpha: 1 });
        gsap.set(analysisContent, { autoAlpha: 1, y: 44 });
        gsap.set(analysisCards, { autoAlpha: 0, y: 32 });
        gsap.set(analysisLeaves, {
          autoAlpha: 0,
          x: 0,
          y: 130,
          rotate: -26,
          scale: 0.68,
        });

        gsap.timeline({
          defaults: { ease: "none" },
          scrollTrigger: {
            trigger: sceneTwo,
            start: "top bottom",
            end: "top top",
            scrub: 0.72,
          },
        })
          .to(sharedBottle, {
            "--shared-bottle-image-opacity": NORMAL_BOTTLE_OPACITY,
            duration: 0.66,
            ease: "none",
          }, 0)
          .to(sharedBottle, {
            x: () => bottleState("analysisDrop").x,
            y: () => bottleState("analysisDrop").y - 76,
            width: () => bottleState("analysisDrop").width * 0.72,
            height: () => bottleState("analysisDrop").height * 0.72,
            rotate: -18,
            duration: 0.34,
            ease: "power1.in",
          }, 0)
          .to(sharedBottle, {
            ...bottleState("analysisDrop"),
            duration: 0.66,
            ease: "power2.out",
          }, 0.32)
          .to(analysisLeaves, {
            autoAlpha: 0.88,
            x: (index) => (index % 2 === 0 ? 48 : -34),
            y: (index) => -140 - index * 12,
            rotate: (index) => (index % 2 === 0 ? 48 : -62),
            scale: (index) => 0.82 + (index % 3) * 0.16,
            stagger: 0.014,
            duration: 0.72,
            ease: "sine.out",
          }, 0.08)
          .to(analysisLeaves, {
            autoAlpha: 0.08,
            y: "-=80",
            duration: 0.24,
            ease: "sine.in",
          }, 0.72);

        const analysisTimeline = gsap.timeline({
          defaults: { ease: "power3.out" },
          scrollTrigger: {
            trigger: sceneTwo,
            start: "top top",
            end: "+=220%",
            pin: true,
            scrub: 0.85,
            anticipatePin: 1,
          },
        });

        analysisTimeline
          .to(sharedBottle, { ...bottleState("analysis"), duration: 0.28 }, 0.02)
          .to(analysisContent, { y: 0, duration: 0.35 }, 0.18)
          .to(analysisCards, { autoAlpha: 1, y: 0, stagger: 0.045, duration: 0.32 }, 0.3)
          .to(sharedBottle, {
            y: () => bottleState("analysis").y + 84,
            rotate: -2,
            duration: 0.34,
            ease: "power1.inOut",
          }, 0.72)
          .to(analysisLeaves, {
            autoAlpha: 0.78,
            x: (index) => (index % 2 === 0 ? 42 : -30),
            y: (index) => -106 - index * 8,
            rotate: (index) => (index % 2 === 0 ? 36 : -52),
            scale: (index) => 0.74 + (index % 3) * 0.13,
            stagger: 0.014,
            duration: 0.3,
            ease: "sine.out",
          }, 0.68)
          .to(analysisLeaves, { autoAlpha: 0.08, y: "-=72", duration: 0.2, ease: "sine.in" }, 0.86);
      }

      if (sceneThree) {
        const auditBin = sceneThree.querySelector("[data-audit-bin]");
        const auditPanel = sceneThree.querySelector("[data-audit-panel]");
        const auditVerified = sceneThree.querySelector("[data-audit-verified]");
        const auditLeaves = gsap.utils.toArray(sceneThree.querySelectorAll("[data-audit-leaves] span"));
        const syncAuditFront = (visible = true) => {
          if (!auditFrontFixed || !auditBin) {
            return;
          }

          const rect = auditBin.getBoundingClientRect();

          if (rect.width === 0 || rect.height === 0) {
            gsap.set(auditFrontFixed, { autoAlpha: 0 });
            return;
          }

          gsap.set(auditFrontFixed, {
            x: rect.left,
            y: rect.top,
            width: rect.width,
            height: rect.height,
            autoAlpha: visible ? 1 : 0,
          });
        };

        const auditBottleState = (state) => {
          const rect = auditBin?.getBoundingClientRect();

          if (!rect || rect.width === 0 || rect.height === 0) {
            return bottleState(state === "insideBin" ? "bin" : "audit");
          }

          const height = Math.min(280, window.innerHeight * 0.44);
          const width = height * (64 / 210);
          const openingX = rect.left + rect.width * 0.5;
          const openingY = rect.top + rect.height * 0.16;
          const contactY = openingY - height * 0.96;

          if (state === "insideBin") {
            return {
              x: openingX - width / 2,
              y: openingY - height * 0.34,
              width,
              height,
              rotate: 7,
              autoAlpha: 0.82,
            };
          }

          if (state === "entry") {
            return {
              x: openingX - width / 2,
              y: contactY,
              width,
              height,
              rotate: 2,
              autoAlpha: 1,
            };
          }

          return {
            x: openingX - width / 2,
            y: openingY - height * 1.02,
            width,
            height,
            rotate: -11,
            autoAlpha: 1,
          };
        };

        gsap.set(auditPanel, { autoAlpha: 1, y: 54 });
        gsap.set(auditVerified, { autoAlpha: 0, y: 12, scale: 0.9 });
        gsap.set(auditFrontFixed, { autoAlpha: 0, x: 0, y: 0, width: 1, height: 1 });
        gsap.set(auditLeaves, {
          autoAlpha: 0,
          x: 0,
          y: 120,
          rotate: -28,
          scale: 0.7,
        });

        gsap.timeline({
          defaults: { ease: "none" },
          scrollTrigger: {
            trigger: sceneThree,
            start: "top 112%",
            end: "top top",
            scrub: 0.72,
          },
        })
          .to(auditLeaves, {
            autoAlpha: 0.72,
            x: (index) => (index % 2 === 0 ? 36 : -26),
            y: (index) => -118 - index * 9,
            rotate: (index) => (index % 2 === 0 ? 38 : -56),
            scale: (index) => 0.76 + (index % 3) * 0.14,
            stagger: 0.014,
            duration: 0.62,
            ease: "sine.out",
          }, 0.1)
          .to(auditLeaves, { autoAlpha: 0.08, y: "-=72", duration: 0.2, ease: "sine.in" }, 0.72);

        let auditTimeline;

        auditTimeline = gsap.timeline({
          defaults: { ease: "power2.inOut" },
          onUpdate: () => {
            syncAuditFront(!auditTimeline || auditTimeline.time() < 1.1);
          },
          scrollTrigger: {
            trigger: sceneThree,
            start: "top top",
            end: "+=230%",
            pin: true,
            scrub: 0.9,
            anticipatePin: 1,
            onEnter: () => syncAuditFront(true),
            onEnterBack: () => syncAuditFront(true),
            onLeave: () => syncAuditFront(false),
            onLeaveBack: () => syncAuditFront(false),
          },
        });

        auditTimeline
          .set(auditFrontFixed, {
            x: () => auditBin.getBoundingClientRect().left,
            y: () => auditBin.getBoundingClientRect().top,
            width: () => auditBin.getBoundingClientRect().width,
            height: () => auditBin.getBoundingClientRect().height,
            autoAlpha: 1,
          }, 0)
          .to(sharedBottle, {
            x: () => auditBottleState("aboveBin").x,
            y: () => auditBottleState("aboveBin").y,
            width: () => auditBottleState("aboveBin").width,
            height: () => auditBottleState("aboveBin").height,
            rotate: () => auditBottleState("aboveBin").rotate,
            autoAlpha: 1,
            clipPath: "inset(0% 0% 0% 0%)",
            duration: 0.34,
          }, 0)
          .to(auditLeaves, {
            autoAlpha: 0.82,
            x: (index) => (index % 2 === 0 ? 44 : -28),
            y: (index) => -90 - index * 10,
            rotate: (index) => (index % 2 === 0 ? 38 : -54),
            scale: (index) => 0.82 + (index % 3) * 0.16,
            stagger: 0.018,
            duration: 0.34,
            ease: "sine.out",
          }, 0.26)
          .to(sharedBottle, {
            x: () => auditBottleState("entry").x,
            y: () => auditBottleState("entry").y,
            width: () => auditBottleState("entry").width,
            height: () => auditBottleState("entry").height,
            rotate: () => auditBottleState("entry").rotate,
            autoAlpha: 1,
            clipPath: "inset(0% 0% 0% 0%)",
            duration: 0.24,
            ease: "power1.in",
          }, 0.3)
          .to(sharedBottle, {
            x: () => auditBottleState("insideBin").x,
            y: () => auditBottleState("insideBin").y,
            width: () => auditBottleState("insideBin").width,
            height: () => auditBottleState("insideBin").height,
            rotate: () => auditBottleState("insideBin").rotate,
            autoAlpha: () => auditBottleState("insideBin").autoAlpha,
            clipPath: "inset(0% 0% 0% 0%)",
            duration: 0.42,
            ease: "power2.in",
          }, 0.4)
          .to(auditLeaves, { autoAlpha: 0.14, y: "-=80", duration: 0.2, ease: "sine.in" }, 0.82)
          .to(sharedBottle, { autoAlpha: 0, duration: 0.14 }, 0.94)
          .to(auditVerified, { autoAlpha: 1, y: 0, scale: 1, duration: 0.22 }, 0.96)
          .to(auditPanel, { y: 0, duration: 0.38 }, 0.7);
      }
    }, root);
  });

  onBeforeUnmount(() => {
    if (resizeHandler) {
      window.removeEventListener("resize", resizeHandler);
      resizeHandler = null;
    }
    context?.revert();
  });

  return rootRef;
}
