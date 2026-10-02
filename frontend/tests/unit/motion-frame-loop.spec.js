import { describe, expect, it, vi } from "vitest";

import { createFrameLoop } from "../../src/motion/frameLoop.js";

// A hand-cranked requestAnimationFrame: frame(t) runs the pending callback at time t (ms).
function fakeScheduler() {
  let pending = null;
  let nextId = 1;
  return {
    raf: (callback) => {
      pending = { id: nextId++, callback };
      return pending.id;
    },
    caf: (id) => {
      if (pending?.id === id) pending = null;
    },
    frame(time) {
      const current = pending;
      pending = null;
      current?.callback(time);
    },
    get hasPending() {
      return pending !== null;
    },
  };
}

describe("createFrameLoop", () => {
  it("passes the time since the previous frame in seconds, starting at zero", () => {
    const scheduler = fakeScheduler();
    const onFrame = vi.fn();
    const loop = createFrameLoop(onFrame, scheduler);

    loop.start();
    scheduler.frame(1000);
    scheduler.frame(1016);

    expect(onFrame.mock.calls[0][0]).toBe(0);
    expect(onFrame.mock.calls[1][0]).toBeCloseTo(0.016, 6);
  });

  it("clamps a long gap, such as a background tab, to maxDt", () => {
    const scheduler = fakeScheduler();
    const onFrame = vi.fn();
    const loop = createFrameLoop(onFrame, { ...scheduler, maxDt: 1 / 30 });

    loop.start();
    scheduler.frame(0);
    scheduler.frame(5000);

    expect(onFrame.mock.calls[1][0]).toBeCloseTo(1 / 30, 6);
  });

  it("stops scheduling frames after stop()", () => {
    const scheduler = fakeScheduler();
    const onFrame = vi.fn();
    const loop = createFrameLoop(onFrame, scheduler);

    loop.start();
    scheduler.frame(0);
    loop.stop();

    expect(scheduler.hasPending).toBe(false);
    expect(loop.running).toBe(false);
  });

  it("does not report the paused time as one huge step after a restart", () => {
    const scheduler = fakeScheduler();
    const onFrame = vi.fn();
    const loop = createFrameLoop(onFrame, scheduler);

    loop.start();
    scheduler.frame(0);
    loop.stop();
    loop.start();
    scheduler.frame(20000);

    expect(onFrame.mock.calls[1][0]).toBe(0);
  });
});
