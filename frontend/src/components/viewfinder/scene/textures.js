// Textures drawn on a 2D canvas at runtime: no image files to download, and
// the print stays generic (no real brands).
import { CanvasTexture, RepeatWrapping, SRGBColorSpace } from "three";

const LABEL_FONT = '"Archivo Variable", "Segoe UI", system-ui, sans-serif';

function canvasTexture(width, height, draw, { color = true } = {}) {
  const canvas = document.createElement("canvas");
  canvas.width = width;
  canvas.height = height;
  draw(canvas.getContext("2d"), width, height);
  const texture = new CanvasTexture(canvas);
  if (color) texture.colorSpace = SRGBColorSpace;
  texture.anisotropy = 4;
  return texture;
}

// Deterministic noise, so every load prints the same paper fibers.
function seededRandom(seed) {
  let state = seed;
  return () => {
    state = (state * 1664525 + 1013904223) % 4294967296;
    return state / 4294967296;
  };
}

// A water-bottle label. Width:height is about 4:1, the label's circumference to its height.
export function petLabelTexture() {
  return canvasTexture(1024, 256, (ctx, w, h) => {
    ctx.fillStyle = "#f5f8fb";
    ctx.fillRect(0, 0, w, h);
    ctx.fillStyle = "#2f7fd6";
    ctx.beginPath();
    ctx.moveTo(0, h * 0.62);
    for (let x = 0; x <= w; x += 8) {
      ctx.lineTo(x, h * 0.62 + Math.sin((x / w) * Math.PI * 6) * h * 0.06);
    }
    ctx.lineTo(w, h);
    ctx.lineTo(0, h);
    ctx.fill();
    ctx.fillStyle = "#123a66";
    ctx.font = `700 ${h * 0.3}px ${LABEL_FONT}`;
    ctx.fillText("spring water", w * 0.08, h * 0.45);
    ctx.font = `600 ${h * 0.16}px ${LABEL_FONT}`;
    ctx.fillStyle = "#ffffff";
    ctx.fillText("500 ml", w * 0.58, h * 0.88);
  });
}

// A drinks can sleeve, wrapped around the can body.
export function canPrintTexture() {
  return canvasTexture(1024, 400, (ctx, w, h) => {
    ctx.fillStyle = "#e9c24a";
    ctx.fillRect(0, 0, w, h);
    ctx.fillStyle = "#f6dc7c";
    ctx.fillRect(0, h * 0.18, w, h * 0.05);
    ctx.fillRect(0, h * 0.77, w, h * 0.05);
    ctx.fillStyle = "#3d2a07";
    ctx.font = `800 ${h * 0.22}px ${LABEL_FONT}`;
    ctx.fillText("sparkling", w * 0.12, h * 0.55);
    ctx.font = `600 ${h * 0.09}px ${LABEL_FONT}`;
    ctx.fillText("lemon  330 ml", w * 0.13, h * 0.68);
  });
}

// Kraft corrugated board: fibers, faint flutes, slightly darker edges.
export function kraftTexture() {
  const texture = canvasTexture(512, 512, (ctx, w, h) => {
    const random = seededRandom(7);
    ctx.fillStyle = "#b98a58";
    ctx.fillRect(0, 0, w, h);
    for (let i = 0; i < 2600; i++) {
      const shade = 150 + Math.floor(random() * 50);
      ctx.fillStyle = `rgba(${shade}, ${Math.floor(shade * 0.72)}, ${Math.floor(shade * 0.45)}, ${0.06 + random() * 0.08})`;
      ctx.fillRect(random() * w, random() * h, 1 + random() * 6, 1);
    }
    ctx.fillStyle = "rgba(90, 58, 26, 0.05)";
    for (let x = 0; x < w; x += 9) ctx.fillRect(x, 0, 2, h);
    const edge = ctx.createRadialGradient(w / 2, h / 2, w * 0.3, w / 2, h / 2, w * 0.75);
    edge.addColorStop(0, "rgba(0,0,0,0)");
    edge.addColorStop(1, "rgba(70,40,10,0.18)");
    ctx.fillStyle = edge;
    ctx.fillRect(0, 0, w, h);
  });
  texture.wrapS = texture.wrapT = RepeatWrapping;
  return texture;
}

// A paper label for the glass bottle.
export function glassLabelTexture() {
  return canvasTexture(1024, 320, (ctx, w, h) => {
    ctx.fillStyle = "#f1ead8";
    ctx.fillRect(0, 0, w, h);
    ctx.strokeStyle = "#7c5a2a";
    ctx.lineWidth = 6;
    ctx.strokeRect(w * 0.05, h * 0.12, w * 0.4, h * 0.76);
    ctx.fillStyle = "#3b2d1a";
    ctx.font = `700 ${h * 0.2}px ${LABEL_FONT}`;
    ctx.fillText("ginger", w * 0.1, h * 0.5);
    ctx.font = `600 ${h * 0.11}px ${LABEL_FONT}`;
    ctx.fillText("soda  330 ml", w * 0.1, h * 0.72);
  });
}

// A soft dark blob that grounds an object where it touches the surface.
export function contactShadowTexture() {
  return canvasTexture(
    256,
    256,
    (ctx, w, h) => {
      const gradient = ctx.createRadialGradient(w / 2, h / 2, 0, w / 2, h / 2, w / 2);
      gradient.addColorStop(0, "rgba(0,0,0,0.55)");
      gradient.addColorStop(0.45, "rgba(0,0,0,0.22)");
      gradient.addColorStop(1, "rgba(0,0,0,0)");
      ctx.fillStyle = gradient;
      ctx.fillRect(0, 0, w, h);
    },
    { color: false },
  );
}
