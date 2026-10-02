import { BoxGeometry, Mesh, PerspectiveCamera } from "three";
import { describe, expect, it } from "vitest";

import { HANDHELD_LIMITS, handheldOffset } from "../../src/components/viewfinder/handheld.js";
import { VIEWFINDER_ITEMS, carbonFor } from "../../src/components/viewfinder/items.js";
import { projectPoints, samplePoints } from "../../src/components/viewfinder/scene/projection.js";

describe("carbonFor", () => {
  it("matches what the backend computes for the seeded PET bottle", () => {
    // backend: co2 = round(0.05 kg × 1.5, 2) = 0.08; points = round(0.08 × 100) = 8
    const pet = VIEWFINDER_ITEMS.find((item) => item.id === "pet");
    expect(carbonFor(pet)).toEqual({ co2Kg: 0.08, points: 8 });
  });

  it("gives every item a carbon value and whole points", () => {
    for (const item of VIEWFINDER_ITEMS) {
      const { co2Kg, points } = carbonFor(item);
      expect(co2Kg).toBeGreaterThan(0);
      expect(Number.isInteger(points)).toBe(true);
    }
  });
});

describe("handheldOffset", () => {
  it("stays within the documented limits", () => {
    for (let time = 0; time < 120; time += 0.37) {
      const offset = handheldOffset(time);
      for (const axis of Object.keys(HANDHELD_LIMITS)) {
        expect(Math.abs(offset[axis])).toBeLessThanOrEqual(HANDHELD_LIMITS[axis]);
      }
    }
  });

  it("moves smoothly between frames", () => {
    for (let time = 0; time < 30; time += 1 / 60) {
      const a = handheldOffset(time);
      const b = handheldOffset(time + 1 / 60);
      expect(Math.abs(a.yaw - b.yaw)).toBeLessThan(0.0002);
    }
  });

  it("is still when the amplitude is zero (reduced motion)", () => {
    const offset = handheldOffset(12.3, 0);
    expect(Object.values(offset).every((value) => value === 0)).toBe(true);
  });
});

describe("projectPoints", () => {
  function setup() {
    const camera = new PerspectiveCamera(40, 800 / 600, 0.01, 10);
    camera.position.set(0, 0, 2);
    camera.lookAt(0, 0, 0);
    camera.updateMatrixWorld();
    return camera;
  }

  it("centers an object that sits on the camera axis", () => {
    const camera = setup();
    const rect = projectPoints(samplePoints(new Mesh(new BoxGeometry(0.4, 0.4, 0.4))), camera, 800, 600);

    expect(rect.x + rect.width / 2).toBeCloseTo(400, 0);
    expect(rect.y + rect.height / 2).toBeCloseTo(300, 0);
  });

  it("follows the object when it moves right, and shrinks it with distance", () => {
    const camera = setup();
    const near = new Mesh(new BoxGeometry(0.2, 0.2, 0.2));
    const right = new Mesh(new BoxGeometry(0.2, 0.2, 0.2));
    right.position.set(0.5, 0, -1);

    const nearRect = projectPoints(samplePoints(near), camera, 800, 600);
    const rightRect = projectPoints(samplePoints(right), camera, 800, 600);

    expect(rightRect.x).toBeGreaterThan(nearRect.x);
    expect(rightRect.width).toBeLessThan(nearRect.width);
  });
});
