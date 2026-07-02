import { onBeforeUnmount, onMounted, unref } from "vue";

function clamp(value, min = 0, max = 1) {
  return Math.min(max, Math.max(min, value));
}

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

export function useStageWebGL({
  activeChapter,
  isReducedMotion,
  mountRef,
  progress,
  scenePhase,
}) {
  let animationFrame = 0;
  let cleanup = null;

  async function initialize() {
    const mount = unref(mountRef);

    if (!mount || unref(isReducedMotion) || !hasWebGLSupport()) {
      return;
    }

    const THREE = await import("three");

    const scene = new THREE.Scene();
    const camera = new THREE.OrthographicCamera(-1, 1, 1, -1, 0, 1);
    const renderer = new THREE.WebGLRenderer({
      alpha: true,
      antialias: true,
      powerPreference: "high-performance",
    });

    renderer.setClearAlpha(0);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 1.5));

    const uniforms = {
      uTime: { value: 0 },
      uProgress: { value: 0 },
      uDissolveStart: { value: 0.19 },
      uDissolveEnd: { value: 0.31 },
      uResolution: { value: new THREE.Vector2(1, 1) },
      uNoiseScaleLow: { value: window.innerWidth < 900 ? 2.2 : 2.95 },
      uNoiseScaleHigh: { value: window.innerWidth < 900 ? 8.0 : 12.4 },
      uSceneMix: { value: 0 },
      uPointer: { value: new THREE.Vector2(0, 0) },
    };

    const geometry = new THREE.PlaneGeometry(2, 2);
    const material = new THREE.ShaderMaterial({
      transparent: true,
      depthWrite: false,
      uniforms,
      vertexShader: `
        varying vec2 vUv;

        void main() {
          vUv = uv;
          gl_Position = vec4(position.xy, 0.0, 1.0);
        }
      `,
      fragmentShader: `
        varying vec2 vUv;

        uniform float uTime;
        uniform float uProgress;
        uniform float uDissolveStart;
        uniform float uDissolveEnd;
        uniform vec2 uResolution;
        uniform float uNoiseScaleLow;
        uniform float uNoiseScaleHigh;
        uniform float uSceneMix;
        uniform vec2 uPointer;

        float hash(vec2 p) {
          return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453123);
        }

        float noise(vec2 p) {
          vec2 i = floor(p);
          vec2 f = fract(p);
          vec2 u = f * f * (3.0 - 2.0 * f);

          return mix(
            mix(hash(i), hash(i + vec2(1.0, 0.0)), u.x),
            mix(hash(i + vec2(0.0, 1.0)), hash(i + vec2(1.0, 1.0)), u.x),
            u.y
          );
        }

        float fbm(vec2 p) {
          float value = 0.0;
          float amplitude = 0.5;

          for (int i = 0; i < 5; i++) {
            value += amplitude * noise(p);
            p *= 2.02;
            amplitude *= 0.5;
          }

          return value;
        }

        float smoothMask(float edge0, float edge1, float value) {
          return smoothstep(edge0, edge1, value);
        }

        vec3 darkScene(vec2 uv, float time) {
          vec2 aspectUv = uv;
          aspectUv.x *= uResolution.x / max(uResolution.y, 1.0);

          float fog = fbm(aspectUv * 2.8 + vec2(time * 0.014, -time * 0.01));
          float mist = fbm(aspectUv * 5.8 - vec2(time * 0.024, time * 0.014));
          float canopy = smoothMask(0.2, 0.64, fbm(vec2(aspectUv.x * 1.7, uv.y * 6.8) + vec2(0.0, time * 0.012)));
          float branchNoise = fbm(vec2(uv.x * 10.0, uv.y * 3.5) + vec2(time * 0.008, 2.0));
          float trunkA = smoothMask(0.055, 0.01, abs(uv.x - 0.76 + fog * 0.05)) * smoothMask(0.1, 0.8, uv.y);
          float trunkB = smoothMask(0.07, 0.018, abs(uv.x - 0.2 - fog * 0.035)) * smoothMask(0.32, 0.88, uv.y);
          float shrub = smoothMask(0.22, 0.62, fbm(vec2(uv.x * 8.2, uv.y * 11.8) - vec2(time * 0.014, 0.0)));
          float branchEdge = smoothMask(0.24, 0.82, branchNoise) * smoothMask(0.26, 0.02, uv.y);

          vec3 base = mix(vec3(0.1, 0.113, 0.102), vec3(0.195, 0.205, 0.188), fog * 0.46 + mist * 0.2);
          base += canopy * vec3(0.026, 0.032, 0.022);
          base += trunkA * vec3(0.038, 0.033, 0.024);
          base += trunkB * vec3(0.03, 0.026, 0.02);
          base += shrub * vec3(0.022, 0.026, 0.018) * smoothMask(0.65, 0.04, uv.y);
          base -= branchEdge * vec3(0.012, 0.011, 0.009);
          base += vec3(0.12, 0.104, 0.078) * smoothMask(0.48, 0.0, distance(uv, vec2(0.52, 0.44))) * 0.18;
          base += vec3(0.022, 0.025, 0.02) * smoothMask(0.9, 0.35, uv.y);

          return base;
        }

        vec3 lightScene(vec2 uv, float time) {
          float paper = fbm(uv * 4.4 + vec2(time * 0.008, -time * 0.004));
          float wash = fbm(uv * 12.0 - vec2(0.0, time * 0.012));
          float foliage = smoothMask(0.18, 0.6, fbm(vec2(uv.x * 9.5, uv.y * 4.6) + vec2(time * 0.016, 4.0)));
          float topFade = smoothMask(0.84, 0.2, uv.y);
          float paperCloud = smoothMask(0.3, 0.0, distance(uv, vec2(0.5, 0.55)));

          vec3 base = mix(vec3(0.842, 0.822, 0.785), vec3(0.898, 0.878, 0.838), paper * 0.44 + wash * 0.16);
          base -= foliage * vec3(0.132, 0.112, 0.086) * topFade * 0.5;
          base += vec3(0.94, 0.918, 0.878) * paperCloud * 0.05;
          base -= vec3(0.018, 0.016, 0.013) * smoothMask(0.98, 0.58, uv.y);

          return base;
        }

        void main() {
          vec2 uv = vUv;
          vec2 pointerDrift = vec2(uPointer.x * 0.015, uPointer.y * 0.012);
          float time = uTime;

          float lowNoise = fbm((uv + pointerDrift) * uNoiseScaleLow + vec2(0.0, time * 0.035));
          float highNoise = fbm((uv - pointerDrift) * uNoiseScaleHigh - vec2(time * 0.08, 0.0));
          float sceneDarkNoise = fbm(uv * 2.6 + vec2(time * 0.01, -time * 0.012));
          float dissolveDriver = smoothstep(uDissolveStart, uDissolveEnd, uProgress);

          float bottomBias = uv.y * 0.98;
          float erosion = bottomBias + (lowNoise - 0.5) * 0.41 + (highNoise - 0.5) * 0.14;
          float threshold = dissolveDriver * 1.06;
          float reveal = smoothMask(erosion - 0.08, erosion + 0.012, threshold);
          float edge = 1.0 - smoothMask(0.015, 0.09, abs(threshold - erosion));
          float band = edge * smoothMask(0.05, 0.88, dissolveDriver);
          float foam = edge * smoothMask(0.0, 0.24, lowNoise + highNoise * 0.42);
          float underglow = smoothMask(0.0, 0.16, threshold - erosion) * smoothMask(0.12, 0.88, dissolveDriver);

          vec3 sceneA = darkScene(uv, time);
          vec3 sceneB = lightScene(uv, time);
          vec3 color = mix(sceneA, sceneB, reveal);

          color += band * vec3(0.94, 0.9, 0.84) * 0.2;
          color += vec3(0.88, 0.79, 0.61) * foam * 0.1;
          color += vec3(0.95, 0.88, 0.79) * underglow * 0.08;
          color += sceneDarkNoise * 0.012;

          float vignette = smoothMask(0.92, 0.18, distance(uv, vec2(0.5, 0.53)));
          float alpha = mix(0.97, 1.0, vignette);

          gl_FragColor = vec4(color, alpha);
        }
      `,
    });

    const mesh = new THREE.Mesh(geometry, material);
    scene.add(mesh);
    mount.appendChild(renderer.domElement);

    const onPointerMove = (event) => {
      const rect = mount.getBoundingClientRect();
      const x = ((event.clientX - rect.left) / Math.max(rect.width, 1) - 0.5) * 2;
      const y = ((event.clientY - rect.top) / Math.max(rect.height, 1) - 0.5) * 2;
      uniforms.uPointer.value.set(clamp(x, -1, 1), clamp(y, -1, 1));
    };

    const onPointerLeave = () => {
      uniforms.uPointer.value.set(0, 0);
    };

    const resize = () => {
      const width = mount.clientWidth;
      const height = mount.clientHeight;

      if (!width || !height) {
        return;
      }

      renderer.setSize(width, height, false);
      renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, window.innerWidth < 900 ? 1.2 : 1.5));
      uniforms.uResolution.value.set(width, height);
      uniforms.uNoiseScaleLow.value = window.innerWidth < 900 ? 2.2 : 2.95;
      uniforms.uNoiseScaleHigh.value = window.innerWidth < 900 ? 8.0 : 12.4;
    };

    const render = () => {
      uniforms.uTime.value = performance.now() / 1000;
      uniforms.uProgress.value = unref(progress);
      uniforms.uSceneMix.value = ["insight", "impact", "outro"].includes(unref(activeChapter))
        ? 1
        : unref(scenePhase) === "dissolve"
          ? clamp((unref(progress) - 0.18) / 0.2)
          : 0;

      renderer.render(scene, camera);
      animationFrame = window.requestAnimationFrame(render);
    };

    resize();
    render();

    window.addEventListener("resize", resize);
    window.addEventListener("pointermove", onPointerMove, { passive: true });
    window.addEventListener("pointerleave", onPointerLeave);

    cleanup = () => {
      window.removeEventListener("resize", resize);
      window.removeEventListener("pointermove", onPointerMove);
      window.removeEventListener("pointerleave", onPointerLeave);
      window.cancelAnimationFrame(animationFrame);
      geometry.dispose();
      material.dispose();
      renderer.dispose();
      renderer.domElement.remove();
    };
  }

  onMounted(() => {
    initialize();
  });

  onBeforeUnmount(() => {
    cleanup?.();
  });
}
