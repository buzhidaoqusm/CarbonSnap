// Compare two builds of the app, element by element and pixel by pixel.
//
//   node tools/frontend/style-diff.mjs plan.json
//
// plan.json:
// {
//   "before": "http://localhost:4175",
//   "after": "http://localhost:4174",
//   "routes": ["/", "/market", "/forum/posts/4"],
//   "viewports": [
//     { "name": "desktop", "width": 1440, "height": 900 },
//     { "name": "phone", "width": 390, "height": 844, "mobile": true }
//   ],
//   "localStorage": { "cs_token": "..." },
//   "reducedMotion": true,
//   "settle": 1500,
//   "screenWait": 300,
//   "maxScreens": 6,
//   "outDir": "style-diff"
// }
//
// settle: ms to wait after load before measuring. screenWait: ms to wait after
// each scroll before the screenshot. Everything but before, after, routes and
// viewports is optional.
//
// To serve two builds side by side, copy one dist/ elsewhere and run
//   npx vite preview --outDir <that folder> --port 4174
//
// Each route is loaded from both builds. The script compares every element's
// computed style (every standard property, plus ::before and ::after) and its box, then
// screenshots the page one screen at a time and compares the pixels. Differences
// are printed and written to <outDir>/report.json; a screen that differs gets a
// diff image in which changed pixels are red.
//
// Pages also differ from themselves (animations, clocks, live data, and large
// photos, which Chrome does not always scale to the same pixels). Run it with the
// same build on both sides first to see that noise floor.
//
// Exits 1 if anything differs.
import { mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { join } from "node:path";

import { launchChrome, sleep } from "./cdp.mjs";

const plan = JSON.parse(readFileSync(process.argv[2], "utf8"));
const outDir = plan.outDir || "style-diff";
mkdirSync(outDir, { recursive: true });

// Runs in the page. Values are stored once in a table and referenced by index,
// which keeps a page with thousands of elements to a few MB.
const COLLECT = `(() => {
  const SKIP = new Set(["script", "style", "link", "meta", "template", "noscript"]);
  // Custom properties are left out: their text can change with no effect (a minifier
  // writes 0.5 as .5), and every standard property that uses one is compared.
  const props = [...getComputedStyle(document.documentElement)].filter((prop) => !prop.startsWith("--"));
  const index = new Map();
  const values = [];
  const id = (value) => {
    if (!index.has(value)) {
      index.set(value, values.length);
      values.push(value);
    }
    return index.get(value);
  };
  const pathOf = (element) => {
    const parts = [];
    for (let node = element; node; node = node.parentElement) {
      const parent = node.parentElement;
      parts.unshift(parent ? node.localName + ":" + ([...parent.children].indexOf(node) + 1) : node.localName);
    }
    return parts.join(" > ");
  };
  const elements = [];
  for (const element of [document.documentElement, document.body, ...document.body.querySelectorAll("*")]) {
    if (SKIP.has(element.localName)) continue;
    const path = pathOf(element);
    for (const pseudo of ["", "::before", "::after"]) {
      const style = getComputedStyle(element, pseudo || null);
      if (pseudo && (style.content === "none" || style.content === "normal")) continue;
      const box = pseudo ? null : element.getBoundingClientRect();
      elements.push([
        path + pseudo,
        // The two builds run on different ports; url(...) values carry the origin.
        props.map((prop) => id(style.getPropertyValue(prop).replaceAll(location.origin, "<origin>"))),
        box && [box.x, box.y + scrollY, box.width, box.height].map((n) => Math.round(n * 10) / 10),
      ]);
    }
  }
  return { props, values, elements };
})()`;

// Runs in the page: decodes two PNG screenshots and counts the pixels that differ.
const PIXEL_DIFF = `async function (beforePng, afterPng) {
  const decode = async (data) => createImageBitmap(await (await fetch("data:image/png;base64," + data)).blob());
  const [beforeImage, afterImage] = await Promise.all([decode(beforePng), decode(afterPng)]);
  if (beforeImage.width !== afterImage.width || beforeImage.height !== afterImage.height) return { changed: -1 };
  const pixels = (image) => {
    const context = new OffscreenCanvas(image.width, image.height).getContext("2d");
    context.drawImage(image, 0, 0);
    return context.getImageData(0, 0, image.width, image.height).data;
  };
  const before = pixels(beforeImage);
  const after = pixels(afterImage);
  const diff = new ImageData(afterImage.width, afterImage.height);
  let changed = 0;
  for (let i = 0; i < after.length; i += 4) {
    const same = before[i] === after[i] && before[i + 1] === after[i + 1] && before[i + 2] === after[i + 2];
    if (!same) changed++;
    // Changed pixels in red over a faded copy of the "after" screen.
    diff.data[i] = same ? 191 + after[i] / 4 : 255;
    diff.data[i + 1] = same ? 191 + after[i + 1] / 4 : 0;
    diff.data[i + 2] = same ? 191 + after[i + 2] / 4 : 0;
    diff.data[i + 3] = 255;
  }
  if (!changed) return { changed };
  const canvas = new OffscreenCanvas(afterImage.width, afterImage.height);
  canvas.getContext("2d").putImageData(diff, 0, 0);
  const bytes = new Uint8Array(await (await canvas.convertToBlob({ type: "image/png" })).arrayBuffer());
  let binary = "";
  for (let i = 0; i < bytes.length; i += 0x8000) binary += String.fromCharCode(...bytes.subarray(i, i + 0x8000));
  return { changed, image: btoa(binary) };
}`;

const browser = await launchChrome({ port: 9336 });
const { send, evaluate, waitFor } = browser;

async function load(base, route) {
  // Start from a clean origin with the plan's localStorage, like shoot.mjs.
  const origin = new URL(base).origin;
  const blankLoaded = waitFor("Page.loadEventFired", 60000);
  await send("Page.navigate", { url: `${origin}/__blank` });
  await blankLoaded;
  await evaluate(`(() => {
    localStorage.clear();
    const values = ${JSON.stringify(plan.localStorage || {})};
    for (const key in values) localStorage.setItem(key, values[key]);
    return true;
  })()`);
  const loaded = waitFor("Page.loadEventFired", 60000);
  await send("Page.navigate", { url: new URL(route, base).href });
  await loaded;
  await evaluate("document.fonts.ready.then(() => true)");
  await sleep(plan.settle ?? 1500);
}

async function screens(viewport) {
  const height = await evaluate("document.documentElement.scrollHeight");
  const count = Math.min(plan.maxScreens ?? 6, Math.ceil(height / viewport.height));
  const shots = [];
  for (let screen = 0; screen < count; screen++) {
    // "instant": a page with scroll-behavior: smooth would still be gliding when the shot is taken.
    await evaluate(`new Promise((resolve) => {
      scrollTo({ top: ${screen * viewport.height}, behavior: "instant" });
      requestAnimationFrame(() => requestAnimationFrame(() => resolve(true)));
    })`);
    await sleep(plan.screenWait ?? 300);
    shots.push((await send("Page.captureScreenshot", { format: "png" })).data);
  }
  return { height, shots };
}

function compareStyles(before, after) {
  const afterByPath = new Map(after.elements.map((element) => [element[0], element]));
  const afterProp = new Map(after.props.map((prop, index) => [prop, index]));
  const changed = {};
  const boxes = [];
  const onlyBefore = [];
  for (const [path, style, box] of before.elements) {
    const other = afterByPath.get(path);
    if (!other) {
      onlyBefore.push(path);
      continue;
    }
    afterByPath.delete(path);
    before.props.forEach((prop, index) => {
      const was = before.values[style[index]];
      const is = afterProp.has(prop) ? after.values[other[1][afterProp.get(prop)]] : "(not reported)";
      if (was === is) return;
      changed[prop] ??= { count: 0, examples: [] };
      changed[prop].count++;
      if (changed[prop].examples.length < 3) changed[prop].examples.push({ path, before: was, after: is });
    });
    if (box && other[2] && box.some((value, index) => Math.abs(value - other[2][index]) > 0.5)) {
      boxes.push({ path, before: box, after: other[2] });
    }
  }
  return { elements: before.elements.length, onlyBefore, onlyAfter: [...afterByPath.keys()], changed, boxes };
}

const report = [];
try {
  await send("Page.enable");
  await send("Runtime.enable");
  await send("Emulation.setEmulatedMedia", {
    features: [{ name: "prefers-reduced-motion", value: plan.reducedMotion ? "reduce" : "no-preference" }],
  });
  for (const viewport of plan.viewports) {
    await send("Emulation.setDeviceMetricsOverride", {
      width: viewport.width,
      height: viewport.height,
      deviceScaleFactor: 1,
      mobile: !!viewport.mobile,
    });
    for (const route of plan.routes) {
      const sides = {};
      for (const side of ["before", "after"]) {
        await load(plan[side], route);
        sides[side] = { styles: await evaluate(COLLECT), ...(await screens(viewport)) };
      }
      const styles = compareStyles(sides.before.styles, sides.after.styles);

      const { result: page } = await send("Runtime.evaluate", { expression: "globalThis" });
      const pixels = [];
      const name = `${viewport.name}${route.replace(/[^a-z0-9]+/gi, "_")}`;
      for (let screen = 0; screen < Math.min(sides.before.shots.length, sides.after.shots.length); screen++) {
        const { result } = await send("Runtime.callFunctionOn", {
          objectId: page.objectId,
          functionDeclaration: PIXEL_DIFF,
          arguments: [{ value: sides.before.shots[screen] }, { value: sides.after.shots[screen] }],
          awaitPromise: true,
          returnByValue: true,
        });
        const { changed, image } = result.value;
        if (image) writeFileSync(join(outDir, `${name}-${screen}.png`), Buffer.from(image, "base64"));
        pixels.push(changed);
      }

      const styleChanges = Object.values(styles.changed).reduce((sum, entry) => sum + entry.count, 0);
      const screensChanged = pixels.filter((changed) => changed !== 0).length;
      const same =
        !styles.onlyBefore.length &&
        !styles.onlyAfter.length &&
        !styleChanges &&
        !styles.boxes.length &&
        !screensChanged &&
        sides.before.height === sides.after.height &&
        sides.before.shots.length === sides.after.shots.length;
      report.push({
        route,
        viewport: viewport.name,
        same,
        height: [sides.before.height, sides.after.height],
        pixelsChangedPerScreen: pixels,
        ...styles,
        boxes: styles.boxes.slice(0, 20),
        boxesChanged: styles.boxes.length,
      });
      console.log(
        `${same ? "same" : "DIFF"}  ${viewport.name.padEnd(8)} ${route.padEnd(18)} ` +
          `${styles.elements} elements, ${styleChanges} style values, ${styles.boxes.length} boxes, ` +
          `DOM -${styles.onlyBefore.length}/+${styles.onlyAfter.length}, ` +
          `screens ${pixels.length - screensChanged}/${pixels.length} identical`,
      );
      for (const [prop, { count, examples }] of Object.entries(styles.changed)) {
        console.log(`      ${prop} x${count}  ${examples[0].path}: ${examples[0].before} -> ${examples[0].after}`);
      }
    }
  }
} finally {
  writeFileSync(join(outDir, "report.json"), JSON.stringify(report, null, 1));
  browser.close();
}
if (report.some((entry) => !entry.same)) process.exitCode = 1;
