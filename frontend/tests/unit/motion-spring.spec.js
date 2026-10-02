import { describe, expect, it } from "vitest";

import {
  SPRING_LAND,
  SPRING_UI,
  createSpring,
  dampingRatio,
  isAtRest,
  stepSpring,
} from "../../src/motion/spring.js";

function simulate(spring, seconds, hz, onStep = () => {}) {
  const frames = Math.round(seconds * hz);
  for (let frame = 0; frame < frames; frame++) {
    stepSpring(spring, 1 / hz);
    onStep(spring, (frame + 1) / hz);
  }
  return spring;
}

describe("spring presets", () => {
  it("makes the UI spring critically damped and the landing spring bouncy", () => {
    expect(dampingRatio(SPRING_UI)).toBeCloseTo(1, 5);
    expect(dampingRatio(SPRING_LAND)).toBeCloseTo(0.548, 2);
  });
});

describe("stepSpring", () => {
  it("settles the UI spring without overshooting", () => {
    const spring = createSpring(1, SPRING_UI);
    spring.target = 0;
    let lowest = Infinity;
    let settledAt = null;

    simulate(spring, 1, 60, (s, t) => {
      lowest = Math.min(lowest, s.value);
      if (settledAt === null && Math.abs(s.value) < 1e-3) settledAt = t;
    });

    expect(lowest).toBeGreaterThan(-0.01);
    expect(settledAt).not.toBeNull();
    expect(settledAt).toBeLessThan(0.6);
  });

  it("overshoots the landing spring by about 13% before settling", () => {
    const spring = createSpring(0, SPRING_LAND);
    spring.target = 1;
    let highest = -Infinity;

    simulate(spring, 1.5, 60, (s) => {
      highest = Math.max(highest, s.value);
    });

    expect(highest).toBeGreaterThan(1.08);
    expect(highest).toBeLessThan(1.18);
    expect(spring.value).toBeCloseTo(1, 2);
  });

  it("moves the same way at 30, 60 and 144 frames per second", () => {
    // 1/3 s is a whole number of frames at all three rates (10, 20, 48).
    const at = (hz) => {
      const spring = createSpring(0, SPRING_LAND);
      spring.target = 1;
      return simulate(spring, 1 / 3, hz).value;
    };

    expect(Math.abs(at(30) - at(60))).toBeLessThan(0.01);
    expect(Math.abs(at(144) - at(60))).toBeLessThan(0.01);
  });

  it("keeps the velocity it already has when the target changes", () => {
    const spring = createSpring(0, SPRING_UI);
    spring.target = 1;
    simulate(spring, 0.05, 60);
    const velocityBefore = spring.velocity;

    spring.target = 2;

    expect(spring.velocity).toBe(velocityBefore);
    expect(velocityBefore).toBeGreaterThan(0);
  });

  it("settles at the target after a long pause instead of exploding", () => {
    const spring = createSpring(0, SPRING_LAND);
    spring.target = 1;

    stepSpring(spring, 5);

    expect(spring.value).toBe(1);
    expect(spring.velocity).toBe(0);
    expect(isAtRest(spring)).toBe(true);
  });

  it("reports rest only when both position and velocity are near zero", () => {
    const spring = createSpring(0, SPRING_UI);
    expect(isAtRest(spring)).toBe(true);

    spring.target = 1;
    expect(isAtRest(spring)).toBe(false);

    spring.value = 1;
    spring.velocity = 2;
    expect(isAtRest(spring)).toBe(false);
  });
});
