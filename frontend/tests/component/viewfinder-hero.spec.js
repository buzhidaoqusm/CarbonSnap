import { flushPromises, mount } from "@vue/test-utils";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

// jsdom has no WebGL: replace the three.js scene with a stand-in that reports
// where each item is on screen.
const fakeScene = {
  resize: vi.fn(),
  render: vi.fn(),
  captureInto: vi.fn(),
  dispose: vi.fn(),
  setZoom: vi.fn(),
  setDrift: vi.fn(),
  zoomSettled: true,
  rects: new Map([
    ["pet", { x: 500, y: 600, width: 220, height: 80 }],
    ["can", { x: 760, y: 470, width: 70, height: 120 }],
    ["box", { x: 860, y: 520, width: 160, height: 120 }],
    ["glass", { x: 1060, y: 380, width: 70, height: 230 }],
  ]),
};
vi.mock("../../src/components/viewfinder/scene/viewfinderScene.js", () => ({
  createViewfinderScene: vi.fn(async () => fakeScene),
}));

import ViewfinderHero from "../../src/components/viewfinder/ViewfinderHero.vue";

let frameCallbacks = [];
function runFrames(count, startTime = 1000) {
  for (let frame = 0; frame < count; frame++) {
    const callbacks = frameCallbacks;
    frameCallbacks = [];
    callbacks.forEach((callback) => callback(startTime + frame * 16));
  }
}

function setReducedMotion(reduce) {
  window.matchMedia = vi.fn((query) => ({ matches: reduce && query.includes("reduced-motion") }));
}

async function mountLive() {
  const wrapper = mount(ViewfinderHero, {
    attachTo: document.body,
    global: { stubs: { RouterLink: { template: "<a><slot /></a>" } } },
  });
  await flushPromises(); // the scene module "loads"
  runFrames(2);
  return wrapper;
}

beforeEach(() => {
  setReducedMotion(false);
  frameCallbacks = [];
  window.requestAnimationFrame = vi.fn((callback) => frameCallbacks.push(callback));
  window.cancelAnimationFrame = vi.fn();
  window.requestIdleCallback = (callback) => callback();
  window.ResizeObserver = class {
    observe() {}
    disconnect() {}
  };
  window.IntersectionObserver = class {
    observe() {}
    disconnect() {}
  };
  Object.defineProperty(window, "scrollY", { value: 0, configurable: true });
  Object.values(fakeScene).forEach((value) => value?.mockClear?.());
});

afterEach(() => {
  document.body.innerHTML = "";
});

describe("ViewfinderHero", () => {
  it("shows the copy at once and keeps the shutter disabled until the scene is ready", () => {
    window.requestIdleCallback = () => {}; // the scene never loads
    const wrapper = mount(ViewfinderHero, {
      global: { stubs: { RouterLink: { template: "<a><slot /></a>" } } },
    });

    expect(wrapper.find("h1").text()).toContain("Snap it.");
    expect(wrapper.find(".vf__shutter").attributes("disabled")).toBeDefined();
    expect(wrapper.attributes("data-state")).toBe("loading");
  });

  it("goes live and renders frames once the scene has loaded", async () => {
    const wrapper = await mountLive();

    expect(wrapper.attributes("data-state")).toBe("live");
    expect(fakeScene.render).toHaveBeenCalled();
    expect(wrapper.find(".vf__shutter").attributes("disabled")).toBeUndefined();
  });

  it("takes the photo on the shutter and lists what the backend would record", async () => {
    const wrapper = await mountLive();

    await wrapper.find(".vf__shutter").trigger("click");

    expect(fakeScene.captureInto).toHaveBeenCalledTimes(1);
    expect(wrapper.attributes("data-state")).toBe("captured");
    const rows = wrapper.findAll(".vf__result");
    expect(rows).toHaveLength(4);
    // PET: 0.05 kg × 1.5 = 0.08 kg CO2e -> 8 points, as recycling_analysis_service computes it
    expect(rows[0].text()).toContain("PET bottle");
    expect(rows[0].text()).toContain("50 g");
    expect(rows[0].text()).toContain("0.08 kg");
    expect(rows[0].text()).toContain("+8");
    expect(wrapper.find(".vf__sr").text()).toBe("Photo taken. 4 items recognized.");
  });

  it("takes the photo on the first scroll down", async () => {
    const wrapper = await mountLive();

    Object.defineProperty(window, "scrollY", { value: 120, configurable: true });
    window.dispatchEvent(new Event("scroll"));
    await flushPromises();

    expect(wrapper.attributes("data-state")).toBe("captured");
  });

  it("goes back to the live viewfinder when the shutter is pressed again", async () => {
    const wrapper = await mountLive();
    await wrapper.find(".vf__shutter").trigger("click");

    await wrapper.find(".vf__shutter").trigger("click");

    expect(wrapper.attributes("data-state")).toBe("live");
    expect(wrapper.findAll(".vf__result")).toHaveLength(0);
    expect(wrapper.find(".vf__shutter").attributes("aria-label")).toBe("Take photo");
  });

  it("holds the camera still when the user asks for reduced motion", async () => {
    setReducedMotion(true);

    await mountLive();

    expect(fakeScene.setDrift).toHaveBeenCalledWith(0);
  });

  it("gives the WebGL context back when it unmounts", async () => {
    const wrapper = await mountLive();

    wrapper.unmount();

    expect(fakeScene.dispose).toHaveBeenCalledTimes(1);
  });
});
