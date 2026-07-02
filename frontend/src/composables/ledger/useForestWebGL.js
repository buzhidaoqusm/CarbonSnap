import { onBeforeUnmount, ref, unref, watch } from "vue";

function hasWebGLSupport() {
  try {
    const canvas = document.createElement("canvas");
    return Boolean(
      window.WebGLRenderingContext &&
        (canvas.getContext("webgl") || canvas.getContext("experimental-webgl")),
    );
  } catch {
    return false;
  }
}

// Deterministic LCG pseudo-random so tree positions are consistent per session
function makeSeededRandom(seed) {
  let s = seed;
  return () => {
    s = (s * 1664525 + 1013904223) & 0xffffffff;
    return (s >>> 0) / 0xffffffff;
  };
}

// Mountain surface height at a given (x, z) radius from center
function mountainY(radius, maxRadius, peakHeight) {
  const t = Math.max(0, 1 - radius / maxRadius);
  return peakHeight * t * t * (3 - 2 * t); // smoothstep curve
}

export function useForestWebGL({ mountRef, treeCount, level, xpProgress, isReducedMotion }) {
  const isReady = ref(false);
  let cleanup = null;
  let initVersion = 0;

  async function initialize(version) {
    const mount = unref(mountRef);
    if (!mount || !hasWebGLSupport()) return;

    const THREE = await import("three");
    if (version !== initVersion || unref(mountRef) !== mount) {
      return;
    }

    // ─── Renderer ────────────────────────────────────────────────────────────
    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
    renderer.setClearColor(0x000000, 0);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, window.innerWidth < 900 ? 1.2 : 1.5));
    renderer.shadowMap.enabled = true;
    renderer.shadowMap.type = THREE.PCFSoftShadowMap;
    mount.appendChild(renderer.domElement);

    // ─── Scene ───────────────────────────────────────────────────────────────
    const scene = new THREE.Scene();
    scene.fog = new THREE.FogExp2(0xd4ede6, 0.07);

    // ─── Camera ──────────────────────────────────────────────────────────────
    const camera = new THREE.PerspectiveCamera(42, 1, 0.1, 200);
    // Isometric-like angle: elevated, side view
    camera.position.set(12, 10, 14);
    camera.lookAt(0, 1.5, 0);

    // ─── Lights ──────────────────────────────────────────────────────────────
    const ambientLight = new THREE.AmbientLight(0xfff8ee, 1.1);
    scene.add(ambientLight);

    const sunLight = new THREE.DirectionalLight(0xfffbe6, 2.2);
    sunLight.position.set(8, 16, 6);
    sunLight.castShadow = true;
    sunLight.shadow.mapSize.width = 1024;
    sunLight.shadow.mapSize.height = 1024;
    sunLight.shadow.camera.near = 0.5;
    sunLight.shadow.camera.far = 80;
    sunLight.shadow.camera.left = -12;
    sunLight.shadow.camera.right = 12;
    sunLight.shadow.camera.top = 12;
    sunLight.shadow.camera.bottom = -12;
    scene.add(sunLight);

    const fillLight = new THREE.DirectionalLight(0xaaddcc, 0.5);
    fillLight.position.set(-6, 4, -8);
    scene.add(fillLight);

    // ─── Ground plane ────────────────────────────────────────────────────────
    const groundGeo = new THREE.CircleGeometry(9, 64);
    const groundMat = new THREE.MeshLambertMaterial({ color: 0x8db87a });
    const ground = new THREE.Mesh(groundGeo, groundMat);
    ground.rotation.x = -Math.PI / 2;
    ground.receiveShadow = true;
    scene.add(ground);

    // ─── Mountain ────────────────────────────────────────────────────────────
    // Build a low-poly cone with vertex-color bands (rocky peak → earthy mid → grassy base)
    const MOUNTAIN_RADIUS = 5.5;
    const MOUNTAIN_HEIGHT = 5.8;
    const RADIAL_SEG = 18;
    const HEIGHT_SEG = 6;

    const mountainGeo = new THREE.ConeGeometry(MOUNTAIN_RADIUS, MOUNTAIN_HEIGHT, RADIAL_SEG, HEIGHT_SEG, false);
    mountainGeo.translate(0, MOUNTAIN_HEIGHT / 2, 0);

    // Per-vertex color for the stratified mountain look
    const positions = mountainGeo.attributes.position;
    const colors = new Float32Array(positions.count * 3);
    const levelValue = Math.max(1, Number(unref(level)) || 1);
    const grassSaturation = Math.min(1, levelValue / 10); // 0 → 1 over 10 levels

    for (let i = 0; i < positions.count; i++) {
      const y = positions.getY(i);
      const relY = y / MOUNTAIN_HEIGHT; // 0 = base, 1 = peak

      let r, g, b;
      if (relY > 0.78) {
        // Rocky peak – gray-white
        r = 0.82; g = 0.80; b = 0.78;
      } else if (relY > 0.45) {
        // Mid earthy brown, blended toward green with level
        const t = (relY - 0.45) / 0.33;
        r = 0.52 - t * 0.1;
        g = 0.38 + t * 0.08;
        b = 0.22 + t * 0.04;
      } else {
        // Grassy lower slope – greener with higher level
        r = 0.30 - grassSaturation * 0.08;
        g = 0.50 + grassSaturation * 0.18;
        b = 0.22 - grassSaturation * 0.04;
      }

      colors[i * 3] = r;
      colors[i * 3 + 1] = g;
      colors[i * 3 + 2] = b;
    }

    mountainGeo.setAttribute("color", new THREE.BufferAttribute(colors, 3));
    const mountainMat = new THREE.MeshLambertMaterial({ vertexColors: true, flatShading: true });
    const mountain = new THREE.Mesh(mountainGeo, mountainMat);
    mountain.castShadow = true;
    mountain.receiveShadow = true;
    scene.add(mountain);

    // ─── Trees ───────────────────────────────────────────────────────────────
    // Build a single tree template then clone/instance it
    function buildTreeMesh(THREE, trunkColor, foliageColors) {
      const group = new THREE.Group();

      // Trunk
      const trunkGeo = new THREE.CylinderGeometry(0.07, 0.11, 0.55, 6);
      const trunkMat = new THREE.MeshLambertMaterial({ color: trunkColor, flatShading: true });
      const trunk = new THREE.Mesh(trunkGeo, trunkMat);
      trunk.castShadow = true;
      trunk.position.y = 0.27;
      group.add(trunk);

      // 3 layers of foliage cones (bottom→top: wider→narrower)
      const layers = [
        { r: 0.58, h: 0.72, y: 0.70, ci: 0 },
        { r: 0.46, h: 0.65, y: 1.08, ci: 1 },
        { r: 0.30, h: 0.58, y: 1.42, ci: 2 },
      ];
      for (const layer of layers) {
        const geo = new THREE.ConeGeometry(layer.r, layer.h, 7, 1);
        const mat = new THREE.MeshLambertMaterial({ color: foliageColors[layer.ci], flatShading: true });
        const mesh = new THREE.Mesh(geo, mat);
        mesh.castShadow = true;
        mesh.position.y = layer.y;
        group.add(mesh);
      }

      return group;
    }

    // Two tree variants for visual variety
    const treeVariants = [
      {
        trunkColor: 0x7a5c3a,
        foliageColors: [0x2d8a4e, 0x38a85e, 0x45c070],
      },
      {
        trunkColor: 0x6b4e2e,
        foliageColors: [0x1e7a3e, 0x2c9652, 0x3db065],
      },
    ];

    const treeGroups = [];
    const MAX_TREES = 60;
    const visibleCount = Math.min(MAX_TREES, Number(unref(treeCount)) || 0);
    const rng = makeSeededRandom(42);

    // Pre-generate all tree positions (deterministic, up to MAX_TREES)
    const treePositions = [];
    for (let i = 0; i < MAX_TREES; i++) {
      const angle = rng() * Math.PI * 2;
      // Distribute on slope: avoid peak (r < 0.18) and flat edge (r > 0.84)
      const radius = (0.18 + rng() * 0.66) * MOUNTAIN_RADIUS;
      const x = Math.cos(angle) * radius;
      const z = Math.sin(angle) * radius;
      const y = mountainY(radius, MOUNTAIN_RADIUS, MOUNTAIN_HEIGHT);
      // Normal direction on cone surface for slight outward tilt
      treePositions.push({ x, y, z, angle, radius });
    }

    const treeContainer = new THREE.Group();
    scene.add(treeContainer);

    function spawnTree(index) {
      const pos = treePositions[index];
      if (!pos) return;
      const variant = treeVariants[index % treeVariants.length];
      const mesh = buildTreeMesh(THREE, variant.trunkColor, variant.foliageColors);

      // Slight random scale variation per tree
      const rngLocal = makeSeededRandom(index * 7 + 13);
      const scale = 0.7 + rngLocal() * 0.45;
      mesh.scale.setScalar(scale);

      mesh.position.set(pos.x, pos.y, pos.z);
      // Tilt tree to face outward along mountain slope
      mesh.rotation.y = pos.angle + Math.PI;

      treeContainer.add(mesh);
      treeGroups.push({ mesh, baseScale: scale, index });
    }

    // Spawn the correct count of trees
    for (let i = 0; i < visibleCount; i++) {
      spawnTree(i);
    }

    // ─── Entry animation ─────────────────────────────────────────────────────
    const SKIP_ANIM = unref(isReducedMotion) || window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    const animStartTime = performance.now();
    const STAGGER = SKIP_ANIM ? 0 : 60; // ms between each tree growing
    const GROW_DURATION = SKIP_ANIM ? 0 : 420; // ms for each tree to grow

    if (!SKIP_ANIM) {
      // Start hidden; animation loop will scale them up
      for (const tree of treeGroups) {
        tree.mesh.scale.setScalar(0);
      }
    }

    // ─── Pointer tracking for gentle parallax ────────────────────────────────
    let pointerX = 0;
    let pointerY = 0;
    const onPointerMove = (e) => {
      const rect = mount.getBoundingClientRect();
      pointerX = ((e.clientX - rect.left) / Math.max(rect.width, 1) - 0.5) * 2;
      pointerY = ((e.clientY - rect.top) / Math.max(rect.height, 1) - 0.5) * 2;
    };
    const onPointerLeave = () => { pointerX = 0; pointerY = 0; };
    mount.addEventListener("pointermove", onPointerMove, { passive: true });
    mount.addEventListener("pointerleave", onPointerLeave);

    // ─── Resize ──────────────────────────────────────────────────────────────
    const resize = () => {
      const w = mount.clientWidth;
      const h = mount.clientHeight || 380;
      if (!w) return;
      renderer.setSize(w, h, false);
      renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, window.innerWidth < 900 ? 1.2 : 1.5));
      camera.aspect = w / h;
      camera.updateProjectionMatrix();
    };
    resize();
    window.addEventListener("resize", resize);

    // ─── Camera base position ─────────────────────────────────────────────────
    const CAM_BASE = new THREE.Vector3(12, 10, 14);

    // ─── Animation loop ───────────────────────────────────────────────────────
    let raf = 0;
    const render = () => {
      raf = requestAnimationFrame(render);
      const now = performance.now();
      const time = now / 1000;

      // Grow trees with stagger
      if (!SKIP_ANIM) {
        for (let i = 0; i < treeGroups.length; i++) {
          const startMs = animStartTime + i * STAGGER;
          const elapsed = now - startMs;
          if (elapsed <= 0) continue;
          const t = Math.min(1, elapsed / GROW_DURATION);
          // Ease out cubic
          const easedT = 1 - (1 - t) * (1 - t) * (1 - t);
          treeGroups[i].mesh.scale.setScalar(treeGroups[i].baseScale * easedT);
        }
      }

      // Gentle wind sway on tree foliage
      for (const { mesh, index } of treeGroups) {
        const swayAmount = 0.018;
        mesh.rotation.z = Math.sin(time * 0.9 + index * 0.7) * swayAmount;
        mesh.rotation.x = Math.cos(time * 0.7 + index * 0.5) * swayAmount * 0.6;
      }

      // Camera parallax drift
      const camX = CAM_BASE.x + pointerX * 0.8;
      const camY = CAM_BASE.y + pointerY * 0.5;
      const camZ = CAM_BASE.z - pointerX * 0.4;
      camera.position.lerp(new THREE.Vector3(camX, camY, camZ), 0.04);
      camera.lookAt(0, 1.5, 0);

      renderer.render(scene, camera);
    };
    render();

    isReady.value = true;

    // ─── Cleanup ─────────────────────────────────────────────────────────────
    cleanup = () => {
      cancelAnimationFrame(raf);
      window.removeEventListener("resize", resize);
      mount.removeEventListener("pointermove", onPointerMove);
      mount.removeEventListener("pointerleave", onPointerLeave);

      // Dispose all geometries and materials
      scene.traverse((obj) => {
        if (obj.isMesh) {
          obj.geometry?.dispose();
          if (Array.isArray(obj.material)) {
            obj.material.forEach((m) => m.dispose());
          } else {
            obj.material?.dispose();
          }
        }
      });
      renderer.dispose();
      renderer.domElement.remove();
      isReady.value = false;
    };
  }

  // Re-initialize when the DOM mount is recreated, or when treeCount/level changes.
  watch(
    [() => unref(mountRef), treeCount, level],
    () => {
      initVersion += 1;
      if (cleanup) {
        cleanup();
        cleanup = null;
      }
      initialize(initVersion);
    },
    { flush: "post", immediate: true },
  );

  onBeforeUnmount(() => {
    initVersion += 1;
    cleanup?.();
  });

  return { isReady };
}
