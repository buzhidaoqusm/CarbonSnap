import { onBeforeUnmount, onMounted } from "vue";
import gsap from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";

gsap.registerPlugin(ScrollTrigger);

export function useHomepageReplicaMotion(rootRef, headerStateRef) {
  let cleanup = () => {};

  onMounted(() => {
    const rootElement = rootRef.value;

    if (!rootElement) {
      return;
    }

    const prefersReducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

    const setHeaderState = (nextState) => {
      if (headerStateRef.value !== nextState) {
        headerStateRef.value = nextState;
      }
    };

    const revealTargets = [
      ...rootElement.querySelectorAll(".home-replica-section"),
      ...rootElement.querySelectorAll(".home-replica-footer-band"),
    ];

    if (prefersReducedMotion) {
      rootElement.dataset.reducedMotion = "true";
      revealTargets.forEach((target) => target.classList.add("is-visible"));

      const updateHeaderState = () => {
        const heroHeight = rootElement.querySelector(".home-replica-section--hero")?.offsetHeight ?? 0;
        setHeaderState(window.scrollY > Math.max(72, heroHeight * 0.2) ? "solid" : "overlay");
      };

      updateHeaderState();
      window.addEventListener("scroll", updateHeaderState, { passive: true });

      cleanup = () => {
        window.removeEventListener("scroll", updateHeaderState);
        setHeaderState("overlay");
      };

      return;
    }

    const context = gsap.context(() => {
      const heroSection = rootElement.querySelector(".home-replica-section--hero");
      const heroContentItems = rootElement.querySelectorAll(
        ".home-replica-hero__content > *, .home-replica-hero__media > *",
      );
      const setRevealHiddenState = (target) => {
        target.classList.remove("is-visible");
        gsap.set(target, {
          autoAlpha: 0,
          y: 56,
        });
      };

      const playReveal = (target, duration = 0.9) => {
        target.classList.add("is-visible");
        gsap.to(target, {
          autoAlpha: 1,
          duration,
          ease: "power2.out",
          overwrite: "auto",
          y: 0,
        });
      };

      if (heroContentItems.length > 0) {
        gsap.from(heroContentItems, {
          autoAlpha: 0,
          duration: 1,
          ease: "power2.out",
          stagger: 0.08,
          y: 28,
        });
      }

      revealTargets.forEach((target, index) => {
        if (index === 0) {
          target.classList.add("is-visible");
          return;
        }

        setRevealHiddenState(target);

        ScrollTrigger.create({
          trigger: target,
          start: "top 82%",
          end: "bottom 12%",
          onEnter: () => {
            playReveal(target, 0.9);
          },
          onEnterBack: () => {
            playReveal(target, 0.75);
          },
          onLeave: () => {
            setRevealHiddenState(target);
          },
          onLeaveBack: () => {
            setRevealHiddenState(target);
          },
        });
      });

      if (heroSection) {
        ScrollTrigger.create({
          trigger: heroSection,
          start: "bottom top+=96",
          onEnter: () => setHeaderState("solid"),
          onLeaveBack: () => setHeaderState("overlay"),
        });
      }
    }, rootElement);

    cleanup = () => {
      context.revert();
      setHeaderState("overlay");
    };
  });

  onBeforeUnmount(() => {
    cleanup();
  });
}
