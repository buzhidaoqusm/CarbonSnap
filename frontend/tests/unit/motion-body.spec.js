import { describe, expect, it } from "vitest";

import { GRAVITY, createBody, solveLaunchVelocity, stepBody } from "../../src/motion/body.js";

function simulate(body, seconds, hz, onStep = () => {}) {
  const frames = Math.round(seconds * hz);
  for (let frame = 0; frame < frames; frame++) {
    stepBody(body, 1 / hz);
    onStep(body, (frame + 1) / hz);
  }
  return body;
}

describe("stepBody", () => {
  it("falls under gravity and reaches the floor at sqrt(2h/g)", () => {
    const height = 1.25;
    const body = createBody({ position: { x: 0, y: height, z: 0 }, restitution: 0.3 });
    let firstContact = null;

    simulate(body, 1, 240, (b, t) => {
      if (firstContact === null && b.velocity.y > 0) firstContact = t; // bounced
    });

    expect(firstContact).toBeCloseTo(Math.sqrt((2 * height) / GRAVITY), 1);
  });

  it("rebounds to restitution squared times the drop height", () => {
    const body = createBody({ position: { x: 0, y: 1, z: 0 }, restitution: 0.5 });
    let bounced = false;
    let apexAfterBounce = 0;

    simulate(body, 1.2, 240, (b) => {
      if (b.velocity.y > 0) bounced = true;
      if (bounced) apexAfterBounce = Math.max(apexAfterBounce, b.position.y);
    });

    expect(apexAfterBounce).toBeGreaterThan(0.22);
    expect(apexAfterBounce).toBeLessThan(0.28);
  });

  it("comes to rest on the floor", () => {
    const body = createBody({ position: { x: 0, y: 1, z: 0 }, velocity: { x: 0.5, y: 0, z: 0 }, restitution: 0.4 });

    simulate(body, 5, 60);

    expect(body.resting).toBe(true);
    expect(body.position.y).toBe(0);
    expect(body.velocity).toEqual({ x: 0, y: 0, z: 0 });
  });

  it("lands in the same place at 30 and 120 frames per second", () => {
    const run = (hz) =>
      simulate(createBody({ position: { x: 0, y: 2, z: 0 }, velocity: { x: 1, y: 2, z: 0 } }), 0.6, hz).position;

    const slow = run(30);
    const fast = run(120);
    expect(Math.abs(slow.x - fast.x)).toBeLessThan(0.01);
    expect(Math.abs(slow.y - fast.y)).toBeLessThan(0.01);
  });

  it("spins with its angular velocity and loses spin when it bounces", () => {
    const body = createBody({ position: { x: 0, y: 0.5, z: 0 }, angularVelocity: { x: 0, y: 0, z: 4 } });

    simulate(body, 0.1, 120);
    expect(body.rotation.z).toBeCloseTo(0.4, 2);

    simulate(body, 1, 120);
    expect(Math.abs(body.angularVelocity.z)).toBeLessThan(4);
  });
});

describe("solveLaunchVelocity", () => {
  it("returns the velocity that lands on the target after the given time", () => {
    const from = { x: 0, y: 1, z: 0 };
    const to = { x: 2, y: 0.2, z: 0.5 };
    const velocity = solveLaunchVelocity(from, to, 0.8);
    // No floor in the way: we only check the flight itself.
    const body = createBody({ position: { ...from }, velocity, floorY: -Infinity });

    simulate(body, 0.8, 240);

    expect(body.position.x).toBeCloseTo(to.x, 2);
    expect(body.position.y).toBeCloseTo(to.y, 2);
    expect(body.position.z).toBeCloseTo(to.z, 2);
  });
});
