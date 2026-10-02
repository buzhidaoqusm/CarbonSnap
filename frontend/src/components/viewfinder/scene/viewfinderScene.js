// The viewfinder's 3D scene: a studio sweep, four pieces of waste and window
// light, seen through a hand-held camera. Loaded as its own chunk after the
// page has painted, so three.js never delays the first paint.
import {
  BackSide,
  Box3,
  BoxGeometry,
  Color,
  DirectionalLight,
  HemisphereLight,
  Mesh,
  MeshBasicMaterial,
  MeshStandardMaterial,
  NeutralToneMapping,
  PCFShadowMap,
  PMREMGenerator,
  PerspectiveCamera,
  PlaneGeometry,
  Scene,
  SRGBColorSpace,
  Vector3,
  WebGLRenderer,
  WebGLRenderTarget,
} from "three";

import { createSpring, stepSpring, SPRING_UI } from "../../../motion/spring.js";
import { handheldOffset } from "../handheld.js";
import { MODEL_BUILDERS } from "./models.js";
import { projectPoints, samplePoints } from "./projection.js";
import {
  canPrintTexture,
  contactShadowTexture,
  glassLabelTexture,
  kraftTexture,
  petLabelTexture,
} from "./textures.js";

const BACKDROP = "#e7eaec"; // a shade under the page's steel, so the sweep reads as paper

// Where things stand, per screen shape. Meters; y is up, the camera looks toward -z.
//
// `frame` says where the group of items goes on screen (fractions of the
// viewport): its center, and how much of the width it spans. The copy owns
// the rest. The camera never turns to get there: like a shift lens, the
// projection itself moves (setViewOffset), so perspective stays the same.
const LAYOUTS = {
  landscape: {
    camera: { elevation: 0.36, azimuth: 0.12, fov: 28 },
    frame: { centerX: 0.69, centerY: 0.6, width: 0.46 },
    items: {
      pet: { position: [0.03, 0.0325, 0.07], rotation: [0, 0.42, Math.PI / 2], shadow: [0.24, 0.09] },
      can: { position: [0.06, 0, -0.07], rotation: [0, 0.6, 0], shadow: [0.1, 0.1] },
      box: { position: [0.2, 0, 0.02], rotation: [0, -0.5, 0], shadow: [0.2, 0.17] },
      glass: { position: [0.33, 0, -0.08], rotation: [0, 0.2, 0], shadow: [0.09, 0.09] },
    },
  },
  portrait: {
    camera: { elevation: 0.42, azimuth: 0.08, fov: 30 },
    frame: { centerX: 0.5, centerY: 0.665, width: 0.82 },
    items: {
      pet: { position: [0.04, 0.0325, 0.1], rotation: [0, 0.28, Math.PI / 2], shadow: [0.24, 0.09] },
      can: { position: [-0.09, 0, -0.06], rotation: [0, 0.6, 0], shadow: [0.1, 0.1] },
      box: { position: [0.08, 0, -0.03], rotation: [0, -0.45, 0], shadow: [0.2, 0.17] },
      glass: { position: [0.21, 0, -0.11], rotation: [0, 0.2, 0], shadow: [0.09, 0.09] },
    },
  },
};

// A paper sweep: floor, a quarter-circle bend, then the wall. One surface, no horizon line.
function createSweep() {
  const floorDepth = 2.0;
  const radius = 0.4;
  const wallHeight = 2.4;
  const bend = (Math.PI / 2) * radius;
  const length = floorDepth + bend + wallHeight;
  const geometry = new PlaneGeometry(6, length, 1, 96);
  const position = geometry.attributes.position;
  const backZ = -0.45; // where the floor starts to bend up
  for (let index = 0; index < position.count; index++) {
    const s = position.getY(index) + length / 2; // 0 at the front edge, `length` at the top of the wall
    let y;
    let z;
    if (s <= floorDepth) {
      y = 0;
      z = backZ + floorDepth - s;
    } else if (s <= floorDepth + bend) {
      const angle = (s - floorDepth) / radius;
      y = radius - radius * Math.cos(angle);
      z = backZ - radius * Math.sin(angle);
    } else {
      y = radius + (s - floorDepth - bend);
      z = backZ - radius;
    }
    position.setXYZ(index, position.getX(index), y, z);
  }
  // The plane's "up" (increasing s) now runs back along the floor and up the
  // wall, so its front face points up on the floor (x × -z = +y) and toward
  // the camera on the wall (x × y = +z). No flipping needed.
  geometry.computeVertexNormals();
  const sweep = new Mesh(geometry, new MeshStandardMaterial({ color: BACKDROP, roughness: 0.94 }));
  sweep.receiveShadow = true;
  return sweep;
}

// What shiny and clear things reflect: a real product-photo studio. The room is
// dark, softboxes make the highlights, and the white sweep sits under and
// behind the set. In a bright all-white room (RoomEnvironment) a clear bottle
// reflects and refracts only white and reads as milky plastic; dark
// surroundings give it the dark edges that tell the eye "clear".
function createStudioEnvironment() {
  const studio = new Scene();
  const box = new BoxGeometry(1, 1, 1);
  const panel = (color, intensity, position, scale) => {
    const material = new MeshBasicMaterial({ color });
    material.color.multiplyScalar(intensity); // above 1: light sources in the HDR map
    const mesh = new Mesh(box.clone(), material);
    mesh.position.set(...position);
    mesh.scale.set(...scale);
    studio.add(mesh);
  };
  const room = new Mesh(new BoxGeometry(24, 14, 24), new MeshBasicMaterial({ color: "#22272d", side: BackSide }));
  room.position.y = 5;
  studio.add(room);
  panel("#e4e7e9", 1, [0, -0.05, 0], [20, 0.1, 20]); // the sweep's floor
  panel("#e4e7e9", 1, [0, 3, -6], [20, 8, 0.1]); // the sweep's wall
  panel("#ffffff", 9, [-6, 4, 2], [0.1, 4, 5]); // key softbox, upper left
  panel("#eef3ff", 2.5, [6, 2.5, 3], [0.1, 3, 3]); // fill card, right
  panel("#ffffff", 5, [0, 8, 1], [6, 0.1, 1.2]); // strip light overhead
  box.dispose();
  return studio;
}

export async function createViewfinderScene(canvas, { items, maxPixelRatio = 2 }) {
  // Canvas text uses only fonts that are already loaded.
  // Phase timings, visible in DevTools' Performance panel and to tools/frontend scripts.
  let phaseStart = performance.now();
  const phase = (name) => {
    const now = performance.now();
    performance.measure(`viewfinder:${name}`, { start: phaseStart, end: now });
    phaseStart = now;
  };

  await document.fonts?.load('700 32px "Archivo Variable"').catch(() => {});
  phase("fonts");

  const renderer = new WebGLRenderer({ canvas, antialias: true, powerPreference: "high-performance" });
  renderer.outputColorSpace = SRGBColorSpace;
  renderer.toneMapping = NeutralToneMapping; // keeps product colors close to their real values
  renderer.shadowMap.enabled = true;
  renderer.shadowMap.type = PCFShadowMap;
  phase("renderer");

  const scene = new Scene();
  scene.background = new Color(BACKDROP);
  const pmrem = new PMREMGenerator(renderer);
  const studio = createStudioEnvironment();
  const environment = pmrem.fromScene(studio, 0.03).texture;
  studio.traverse((child) => {
    if (child.isMesh) {
      child.geometry.dispose();
      child.material.dispose();
    }
  });
  scene.environment = environment;
  scene.environmentIntensity = 1;
  phase("environment");

  scene.add(createSweep());

  // Key light from the upper left, neutral white: a warm key turned the paper cream.
  // A weak cool fill from the right. The hemisphere light is the studio's
  // background light: it lifts the sweep's wall, which faces the dark side of
  // the room, and adds no reflections that would soften the clear plastic.
  const background = new HemisphereLight("#f3f6f9", "#c3c9ce", 0.9);
  scene.add(background);
  const sun = new DirectionalLight("#ffffff", 2.4);
  sun.position.set(-1.1, 1.5, 0.7);
  sun.castShadow = true;
  sun.shadow.mapSize.set(2048, 2048);
  Object.assign(sun.shadow.camera, { left: -0.7, right: 0.7, top: 0.7, bottom: -0.7, near: 0.1, far: 4 });
  sun.shadow.radius = 5;
  sun.shadow.bias = -0.0004;
  sun.shadow.normalBias = 0.012;
  const fill = new DirectionalLight("#e4edff", 0.45);
  fill.position.set(1.2, 0.6, 1);
  scene.add(sun, sun.target, fill);

  const textures = {
    petLabel: petLabelTexture(),
    canPrint: canPrintTexture(),
    kraft: kraftTexture(),
    glassLabel: glassLabelTexture(),
    contact: contactShadowTexture(),
  };
  const contactMaterial = new MeshBasicMaterial({
    map: textures.contact,
    transparent: true,
    depthWrite: false,
    color: "#1b2229",
  });

  const objects = new Map();
  for (const item of items) {
    const model = MODEL_BUILDERS[item.id](textures);
    const shadow = new Mesh(new PlaneGeometry(1, 1), contactMaterial);
    shadow.rotation.x = -Math.PI / 2;
    scene.add(model, shadow);
    objects.set(item.id, { model, shadow, samples: [] });
  }
  phase("models");
  let firstFrame = true;

  const camera = new PerspectiveCamera(30, 1, 0.01, 20);
  const base = { position: new Vector3(), target: new Vector3() };
  const zoom = createSpring(1, SPRING_UI);
  let width = 1;
  let height = 1;
  let layoutName = null;
  let driftAmplitude = 1;
  const rects = new Map();
  const bounds = new Box3();
  const center = new Vector3();
  const group = new Box3();
  const groupCenter = new Vector3();
  const groupSize = new Vector3();
  let layout = null;

  function applyLayout(name) {
    if (name === layoutName) return;
    layoutName = name;
    layout = LAYOUTS[name];
    camera.fov = layout.camera.fov;
    group.makeEmpty();
    for (const [id, entry] of objects) {
      const placement = layout.items[id];
      entry.model.position.fromArray(placement.position);
      entry.model.rotation.set(...placement.rotation);
      entry.model.updateMatrixWorld(true);
      // Models start at their base, so a lying bottle's middle is not its position.
      bounds.setFromObject(entry.model).getCenter(center);
      entry.shadow.position.set(center.x, 0.0006, center.z);
      entry.shadow.scale.set(placement.shadow[0], placement.shadow[1], 1);
      // A lying bottle's shadow is long: turn it to run along the bottle.
      // (Euler XYZ applies z first, then y, so the bottle's axis is turned by rotation.y.)
      entry.shadow.rotation.z = placement.rotation[2] ? placement.rotation[1] : 0;
      entry.samples = samplePoints(entry.model);
      group.union(bounds);
    }
    group.getCenter(groupCenter);
    group.getSize(groupSize);
  }

  // Put the group where layout.frame says, at any viewport size.
  function frameCamera() {
    const { elevation, azimuth } = layout.camera;
    const tanHalfHorizontal = Math.tan(((camera.fov * Math.PI) / 180) / 2) * camera.aspect;
    // Distance at which the group's width fills frame.width of the screen.
    const distance = groupSize.x / (2 * tanHalfHorizontal * layout.frame.width);
    base.target.set(groupCenter.x, groupSize.y * 0.35, groupCenter.z);
    base.position.set(
      base.target.x + distance * Math.cos(elevation) * Math.sin(azimuth),
      base.target.y + distance * Math.sin(elevation),
      base.target.z + distance * Math.cos(elevation) * Math.cos(azimuth),
    );
    // Shift lens: slide the projection so the group's center lands on frame.center.
    const shiftX = (layout.frame.centerX - 0.5) * width;
    const shiftY = (layout.frame.centerY - 0.5) * height;
    camera.setViewOffset(width, height, -shiftX, -shiftY, width, height); // also updates the projection
  }

  function resize(nextWidth, nextHeight, devicePixelRatio = 1) {
    width = Math.max(1, nextWidth);
    height = Math.max(1, nextHeight);
    renderer.setPixelRatio(Math.min(devicePixelRatio, maxPixelRatio));
    renderer.setSize(width, height, false);
    camera.aspect = width / height;
    applyLayout(camera.aspect >= 1 ? "landscape" : "portrait");
    frameCamera();
  }

  function render(dt, timeSeconds) {
    const offset = handheldOffset(timeSeconds, driftAmplitude);
    camera.position.set(base.position.x + offset.x, base.position.y + offset.y, base.position.z);
    camera.lookAt(base.target);
    camera.rotateX(offset.pitch);
    camera.rotateY(offset.yaw);
    camera.rotateZ(offset.roll);
    stepSpring(zoom, dt);
    if (camera.zoom !== zoom.value) {
      camera.zoom = zoom.value;
      camera.updateProjectionMatrix();
    }
    if (firstFrame) phaseStart = performance.now();
    renderer.render(scene, camera);
    if (firstFrame) {
      phase("first-frame"); // includes compiling every shader the scene needs
      firstFrame = false;
    }
    for (const [id, entry] of objects) {
      rects.set(id, projectPoints(entry.samples, camera, width, height));
    }
  }

  // Copy the frame that was just rendered into a (small) 2D canvas. It must run
  // in the same task as render(): afterwards the browser may discard the buffer.
  function captureInto(target) {
    render(0, performance.now() / 1000);
    target.getContext("2d").drawImage(renderer.domElement, 0, 0, target.width, target.height);
  }

  function dispose() {
    scene.traverse((child) => {
      if (child.isMesh) {
        child.geometry.dispose();
        const materials = Array.isArray(child.material) ? child.material : [child.material];
        materials.forEach((material) => material.dispose());
      }
    });
    Object.values(textures).forEach((texture) => texture.dispose());
    environment.dispose();
    pmrem.dispose();
    renderer.dispose();
    // Browsers allow only a handful of live WebGL contexts; give this one back now.
    renderer.forceContextLoss();
  }

  // Compile every shader before the first frame, in the background where the
  // browser supports it (KHR_parallel_shader_compile). Compiling inside the
  // first render() blocked the page for 3 s on Windows, where ANGLE runs the
  // Direct3D shader compiler.
  //
  // Twice: to show what is behind the bottles, three.js first renders the
  // opaque objects into an off-screen target, and drawing into a target needs
  // shader variants without tone mapping. Compiling with a target bound
  // prepares those too.
  const warmUpTarget = new WebGLRenderTarget(1, 1);
  renderer.setRenderTarget(warmUpTarget);
  await renderer.compileAsync(scene, camera);
  renderer.setRenderTarget(null);
  warmUpTarget.dispose();
  await renderer.compileAsync(scene, camera);
  phase("compile");

  return {
    resize,
    render,
    captureInto,
    dispose,
    rects,
    setZoom(value, { immediate = false } = {}) {
      zoom.target = value;
      if (immediate) {
        zoom.value = value;
        zoom.velocity = 0;
      }
    },
    setDrift(amplitude) {
      driftAmplitude = amplitude;
    },
    get zoomSettled() {
      return Math.abs(zoom.value - zoom.target) < 1e-3 && Math.abs(zoom.velocity) < 1e-3;
    },
  };
}
