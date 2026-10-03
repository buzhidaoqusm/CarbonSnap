// Does the page still render when every other host stops answering?
//
//   node tools/frontend/third-party.mjs http://localhost:4173/            # requests to other hosts hang
//   node tools/frontend/third-party.mjs http://localhost:4173/ --fail     # requests to other hosts are refused
//
// A firewall that drops packets makes a request hang rather than fail, and a
// stylesheet or classic script in <head> that never arrives stops the parser
// before it reaches <body>: the whole app stays blank.
//
// Exits 1 if #app has no content and nothing has been painted within --timeout ms.
import { parseArgs } from "node:util";

import { launchChrome, sleep } from "./cdp.mjs";

const { values, positionals } = parseArgs({
  allowPositionals: true,
  options: {
    fail: { type: "boolean", default: false },
    timeout: { type: "string", default: "10000" },
  },
});
const url = positionals[0];
if (!url) {
  console.error("usage: node tools/frontend/third-party.mjs <url> [--fail] [--timeout ms]");
  process.exit(2);
}

const browser = await launchChrome({ port: 9335 });
const { send, evaluate, on } = browser;
const origin = new URL(url).origin;
const otherHosts = [];
on(({ method, params }) => {
  if (method !== "Fetch.requestPaused") return;
  if (new URL(params.request.url).origin === origin) {
    send("Fetch.continueRequest", { requestId: params.requestId }).catch(() => {});
    return;
  }
  otherHosts.push(params.request.url);
  if (values.fail) {
    send("Fetch.failRequest", { requestId: params.requestId, errorReason: "ConnectionRefused" }).catch(() => {});
  }
  // Without --fail the request is never answered.
});

try {
  await send("Network.setCacheDisabled", { cacheDisabled: true });
  await send("Fetch.enable", { patterns: [{ urlPattern: "*" }] });
  const startedAt = Date.now();
  await send("Page.navigate", { url });

  let renderedMs = null;
  while (Date.now() - startedAt < Number(values.timeout)) {
    const rendered = await evaluate(
      `(document.getElementById("app")?.childElementCount ?? 0) > 0 &&
       performance.getEntriesByName("first-contentful-paint").length > 0`,
    );
    if (rendered) {
      renderedMs = Date.now() - startedAt;
      break;
    }
    await sleep(100);
  }

  console.log(
    JSON.stringify({
      url,
      otherHosts: values.fail ? "refused" : "hang",
      renderedMs,
      readyState: await evaluate("document.readyState"),
      requestsToOtherHosts: otherHosts.map((request) => request.slice(0, 100)),
    }),
  );
  if (renderedMs === null) process.exitCode = 1;
} finally {
  browser.close();
}
