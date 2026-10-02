// Load one page in headless Chrome and report what it costs.
//
//   node tools/frontend/metrics.mjs http://localhost:4173/
//   node tools/frontend/metrics.mjs http://localhost:4173/ --down 10 --rtt 40 --detail
//
// Measure a production build (`npm run build && npx vite preview`), not the dev
// server: Vite dev serves hundreds of unbundled modules and the numbers mean nothing.
//
// Output: transferred KB by resource type, load time, LCP (when the largest
// above-the-fold element finished painting) and long tasks (>50 ms on the main thread).
import { parseArgs } from "node:util";

import { launchChrome, sleep } from "./cdp.mjs";

const { values, positionals } = parseArgs({
  allowPositionals: true,
  options: {
    down: { type: "string" }, // Mbps
    rtt: { type: "string", default: "40" }, // ms
    detail: { type: "boolean", default: false },
  },
});
const url = positionals[0];
if (!url) {
  console.error("usage: node tools/frontend/metrics.mjs <url> [--down Mbps] [--rtt ms] [--detail]");
  process.exit(2);
}

const browser = await launchChrome({ port: 9334 });
const { send, evaluate, on, waitFor } = browser;
const requests = new Map();
on((message) => {
  const { method, params } = message;
  if (method === "Network.requestWillBeSent") {
    requests.set(params.requestId, { url: params.request.url, start: params.timestamp });
  } else if (method === "Network.responseReceived" && requests.has(params.requestId)) {
    requests.get(params.requestId).type = params.type;
  } else if (method === "Network.loadingFinished" && requests.has(params.requestId)) {
    Object.assign(requests.get(params.requestId), { bytes: params.encodedDataLength, end: params.timestamp });
  }
});

try {
  await send("Network.enable");
  await send("Network.setCacheDisabled", { cacheDisabled: true });
  await send("Page.enable");
  await send("Emulation.setDeviceMetricsOverride", { width: 1440, height: 900, deviceScaleFactor: 1, mobile: false });
  if (values.down) {
    const bytesPerSecond = (Number(values.down) * 1024 * 1024) / 8;
    await send("Network.emulateNetworkConditions", {
      offline: false,
      latency: Number(values.rtt),
      downloadThroughput: bytesPerSecond,
      uploadThroughput: bytesPerSecond,
    });
  }
  await send("Page.addScriptToEvaluateOnNewDocument", {
    source: `
      window.__lcp = 0;
      window.__lcpElement = "";
      window.__longTasks = [];
      new PerformanceObserver((list) => {
        for (const e of list.getEntries()) {
          window.__lcp = e.startTime;
          const el = e.element;
          window.__lcpElement = (e.url ? e.url.split("/").pop() + " " : "") +
            (el ? el.tagName.toLowerCase() + (el.className && typeof el.className === "string" ? "." + el.className.trim().split(/\\s+/).join(".") : "") : "");
        }
      }).observe({ type: "largest-contentful-paint", buffered: true });
      new PerformanceObserver((list) => { for (const e of list.getEntries()) window.__longTasks.push(Math.round(e.duration)); })
        .observe({ type: "longtask", buffered: true });`,
  });

  const startedAt = Date.now();
  const loaded = waitFor("Page.loadEventFired", 120000);
  await send("Page.navigate", { url });
  await loaded;
  const loadMs = Date.now() - startedAt;
  await sleep(3000); // let late requests and LCP candidates settle

  const page = await evaluate(
    "({ lcp: Math.round(window.__lcp), lcpElement: window.__lcpElement, longTasks: window.__longTasks })",
  );
  const finished = [...requests.values()].filter((request) => request.bytes !== undefined);
  const kbByType = {};
  for (const request of finished) {
    kbByType[request.type] = (kbByType[request.type] || 0) + request.bytes / 1024;
  }
  for (const type in kbByType) kbByType[type] = Math.round(kbByType[type]);
  const totalKB = Math.round(finished.reduce((sum, request) => sum + request.bytes, 0) / 1024);

  if (values.detail) {
    finished
      .sort((a, b) => b.bytes - a.bytes)
      .forEach((request) =>
        console.log(
          `${String(Math.round(request.bytes / 1024)).padStart(6)} KB ${String(Math.round((request.end - request.start) * 1000)).padStart(6)} ms  ${request.url.slice(0, 100)}`,
        ),
      );
  }
  console.log(
    JSON.stringify({
      url,
      network: values.down ? `${values.down}Mbps/${values.rtt}ms` : "unthrottled",
      loadMs,
      totalKB,
      kbByType,
      ...page,
    }),
  );
} finally {
  browser.close();
}
