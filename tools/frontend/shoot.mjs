// Screenshot pages at given scroll positions in headless Chrome.
//
//   node tools/frontend/shoot.mjs plan.json
//
// plan.json:
// {
//   "outDir": "shots",
//   "shots": [
//     { "name": "home", "url": "http://localhost:5173/", "positions": "auto", "step": 600 },
//     { "name": "m-home", "url": "...", "width": 390, "height": 844, "mobile": true },
//     { "name": "ledger", "url": "...", "localStorage": { "cs_token": "..." } },
//     { "name": "home-rm", "url": "...", "reducedMotion": true }
//   ],
//   "blockUrls": ["*fonts.googleapis.com*"]
// }
//
// blockUrls makes matching requests fail at once. A third-party stylesheet that
// hangs in <head> keeps the whole page blank; blocking it shows what users who
// cannot reach that host get.
//
// Scrolling happens in 40px steps, one animation frame each, so scroll-driven
// timelines see every position instead of jumping to the end.
import { mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { join } from "node:path";

import { launchChrome, sleep } from "./cdp.mjs";

const plan = JSON.parse(readFileSync(process.argv[2], "utf8"));
mkdirSync(plan.outDir, { recursive: true });

const browser = await launchChrome();
const { send, evaluate, on, waitFor } = browser;
const problems = [];
on((message) => {
  if (message.method === "Runtime.exceptionThrown") {
    problems.push(`exception: ${message.params.exceptionDetails.exception?.description}`.slice(0, 300));
  }
  if (message.method === "Runtime.consoleAPICalled" && message.params.type === "error") {
    problems.push(`console.error: ${message.params.args.map((a) => a.value ?? a.description).join(" ")}`.slice(0, 300));
  }
});
await send("Page.enable");
await send("Runtime.enable");
if (plan.blockUrls?.length) {
  await send("Network.enable");
  await send("Network.setBlockedURLs", { urls: plan.blockUrls });
}

const report = [];
try {
  for (const shot of plan.shots) {
    const width = shot.width || 1440;
    const height = shot.height || 900;
    await send("Emulation.setDeviceMetricsOverride", { width, height, deviceScaleFactor: 1, mobile: !!shot.mobile });
    await send("Emulation.setEmulatedMedia", {
      features: [{ name: "prefers-reduced-motion", value: shot.reducedMotion ? "reduce" : "no-preference" }],
    });

    const origin = new URL(shot.url).origin;
    // Start every shot from a clean origin so one shot's login does not leak into the next.
    // Wait for this page's own load event: if it fired late, it would be taken
    // for the real page's and the screenshot would catch a page still loading.
    const blankLoaded = waitFor("Page.loadEventFired", 60000);
    await send("Page.navigate", { url: `${origin}/__blank` });
    await blankLoaded;
    await evaluate(`(() => {
      localStorage.clear();
      const values = ${JSON.stringify(shot.localStorage || {})};
      for (const key in values) localStorage.setItem(key, values[key]);
      return true;
    })()`);

    const loaded = waitFor("Page.loadEventFired");
    await send("Page.navigate", { url: shot.url });
    await loaded;
    await sleep(shot.settle ?? 2000);

    const scrollHeight = await evaluate("document.documentElement.scrollHeight");
    const step = shot.step || height;
    const positions =
      shot.positions === "auto"
        ? Array.from({ length: Math.ceil(scrollHeight / step) }, (_, index) => index * step)
        : shot.positions || [0];

    for (const y of positions) {
      await evaluate(`(async () => {
        const target = ${y};
        const direction = Math.sign(target - scrollY) || 1;
        while (Math.abs(target - scrollY) > 40) {
          const before = scrollY;
          scrollBy(0, direction * 40);
          await new Promise((resolve) => requestAnimationFrame(() => resolve()));
          if (scrollY === before) break; // reached the end of the page
        }
        scrollTo(0, target);
      })()`);
      await sleep(shot.wait ?? 1400);
      // Clip coordinates are document-relative, so offset by the scroll position.
      const pageTop = await evaluate("visualViewport.pageTop");
      const { data } = await send("Page.captureScreenshot", {
        format: "jpeg",
        quality: 72,
        clip: { x: 0, y: pageTop, width, height, scale: shot.scale ?? 0.6 },
      });
      writeFileSync(join(plan.outDir, `${shot.name}-${String(y).padStart(5, "0")}.jpg`), Buffer.from(data, "base64"));
    }
    report.push({ name: shot.name, scrollHeight, shots: positions.length });
  }
} finally {
  console.log(JSON.stringify({ report, problems }, null, 2));
  browser.close();
}
