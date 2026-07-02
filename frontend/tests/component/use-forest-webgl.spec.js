import { defineComponent, h, nextTick, ref } from "vue";
import { mount } from "@vue/test-utils";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("three", () => {
  class Vector3 {
    constructor(x = 0, y = 0, z = 0) {
      this.x = x;
      this.y = y;
      this.z = z;
    }

    set(x, y, z) {
      this.x = x;
      this.y = y;
      this.z = z;
    }

    lerp(target) {
      this.x = target.x;
      this.y = target.y;
      this.z = target.z;
    }
  }

  class Geometry {
    constructor() {
      this.attributes = {
        position: {
          count: 4,
          getY: (index) => index / 3,
        },
      };
      this.dispose = vi.fn();
    }

    translate() {}

    setAttribute(name, value) {
      this.attributes[name] = value;
    }
  }

  class Material {
    constructor() {
      this.dispose = vi.fn();
    }
  }

  class Object3D {
    constructor() {
      this.children = [];
      this.position = new Vector3();
      this.rotation = { x: 0, y: 0, z: 0 };
      this.scale = { setScalar: vi.fn() };
    }

    add(child) {
      this.children.push(child);
    }
  }

  class Mesh extends Object3D {
    constructor(geometry, material) {
      super();
      this.geometry = geometry;
      this.material = material;
      this.isMesh = true;
    }
  }

  class Scene extends Object3D {
    traverse(callback) {
      const visit = (node) => {
        callback(node);
        for (const child of node.children || []) {
          visit(child);
        }
      };
      visit(this);
    }
  }

  class DirectionalLight extends Object3D {
    constructor() {
      super();
      this.shadow = {
        mapSize: {},
        camera: {},
      };
    }
  }

  return {
    AmbientLight: class AmbientLight extends Object3D {},
    BufferAttribute: class BufferAttribute {
      constructor(array, itemSize) {
        this.array = array;
        this.itemSize = itemSize;
      }
    },
    CircleGeometry: Geometry,
    ConeGeometry: Geometry,
    CylinderGeometry: Geometry,
    DirectionalLight,
    FogExp2: class FogExp2 {},
    Group: Object3D,
    Mesh,
    MeshLambertMaterial: Material,
    PCFSoftShadowMap: "PCFSoftShadowMap",
    PerspectiveCamera: class PerspectiveCamera extends Object3D {
      constructor() {
        super();
        this.aspect = 1;
      }

      lookAt() {}

      updateProjectionMatrix() {}
    },
    Scene,
    Vector3,
    WebGLRenderer: class WebGLRenderer {
      constructor() {
        this.domElement = document.createElement("canvas");
        this.shadowMap = {};
        this.dispose = vi.fn();
      }

      render() {}

      setClearColor() {}

      setPixelRatio() {}

      setSize() {}
    },
  };
});

const flushAsync = async () => {
  for (let index = 0; index < 5; index += 1) {
    await Promise.resolve();
    await nextTick();
  }
};

describe("useForestWebGL", () => {
  let controls;

  beforeEach(() => {
    controls = {};
    window.WebGLRenderingContext = function WebGLRenderingContext() {};
    HTMLCanvasElement.prototype.getContext = vi.fn((type) => (type === "webgl" ? {} : null));
    window.requestAnimationFrame = vi.fn(() => 1);
    window.cancelAnimationFrame = vi.fn();
    globalThis.requestAnimationFrame = window.requestAnimationFrame;
    globalThis.cancelAnimationFrame = window.cancelAnimationFrame;
    window.matchMedia = vi.fn(() => ({ matches: true }));
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  it("reinitializes the forest when the mount element is recreated", async () => {
    const { useForestWebGL } = await import("../../src/composables/ledger/useForestWebGL.js");

    const Host = defineComponent({
      setup() {
        const show = ref(false);
        const mountRef = ref(null);
        const treeCount = ref(12);
        const level = ref(3);

        controls.show = show;
        controls.treeCount = treeCount;

        useForestWebGL({
          mountRef,
          treeCount,
          level,
          xpProgress: ref(0.5),
          isReducedMotion: ref(true),
        });

        return () => (show.value ? h("div", { ref: mountRef, class: "forest-host" }) : null);
      },
    });

    const wrapper = mount(Host);

    expect(wrapper.find("canvas").exists()).toBe(false);

    controls.show.value = true;
    await flushAsync();

    expect(wrapper.find("canvas").exists()).toBe(true);

    controls.show.value = false;
    await flushAsync();

    expect(wrapper.find("canvas").exists()).toBe(false);

    controls.show.value = true;
    await flushAsync();

    expect(wrapper.find("canvas").exists()).toBe(true);
  });
});
