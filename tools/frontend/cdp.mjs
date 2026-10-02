// Minimal Chrome DevTools Protocol client: launch headless Chrome, talk to one page.
// No dependencies: Node 22+ ships a global WebSocket.
import { spawn } from "node:child_process";
import { existsSync, mkdtempSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";

const CHROME_CANDIDATES = [
  process.env.CHROME_PATH,
  process.env.LOCALAPPDATA && join(process.env.LOCALAPPDATA, "Google/Chrome/Application/chrome.exe"),
  "C:/Program Files/Google/Chrome/Application/chrome.exe",
  "C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe",
  "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
  "/usr/bin/google-chrome",
  "/usr/bin/chromium",
];

export const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

function findChrome() {
  const found = CHROME_CANDIDATES.find((path) => path && existsSync(path));
  if (!found) {
    throw new Error("Chrome not found. Set CHROME_PATH to a Chrome or Edge executable.");
  }
  return found;
}

export async function launchChrome({ port = 9333 } = {}) {
  // A throwaway profile, so the run never touches the user's own browser data.
  const profileDir = mkdtempSync(join(tmpdir(), "carbonsnap-cdp-"));
  const chrome = spawn(
    findChrome(),
    [
      "--headless=new",
      `--remote-debugging-port=${port}`,
      `--user-data-dir=${profileDir}`,
      "--hide-scrollbars",
      "--no-first-run",
      "--no-default-browser-check",
      "about:blank",
    ],
    { stdio: "ignore" },
  );

  let targets;
  for (let attempt = 0; attempt < 50 && !targets; attempt++) {
    try {
      targets = await (await fetch(`http://127.0.0.1:${port}/json/list`)).json();
    } catch {
      await sleep(200);
    }
  }
  if (!targets) {
    chrome.kill();
    throw new Error("Chrome did not open its debugging port.");
  }

  const ws = new WebSocket(targets.find((target) => target.type === "page").webSocketDebuggerUrl);
  await new Promise((resolve) => ws.addEventListener("open", resolve, { once: true }));

  let seq = 0;
  const pending = new Map();
  const listeners = new Set();
  ws.addEventListener("message", (event) => {
    const message = JSON.parse(event.data);
    if (message.id && pending.has(message.id)) {
      pending.get(message.id)(message);
      pending.delete(message.id);
    } else if (message.method) {
      listeners.forEach((listener) => listener(message));
    }
  });

  const send = (method, params = {}) =>
    new Promise((resolve, reject) => {
      const id = ++seq;
      pending.set(id, (message) =>
        message.error ? reject(new Error(`${method}: ${message.error.message}`)) : resolve(message.result),
      );
      ws.send(JSON.stringify({ id, method, params }));
    });

  const evaluate = async (expression) => {
    const result = await send("Runtime.evaluate", { expression, awaitPromise: true, returnByValue: true });
    if (result.exceptionDetails) {
      throw new Error(result.exceptionDetails.exception?.description || "evaluate failed");
    }
    return result.result.value;
  };

  const on = (listener) => {
    listeners.add(listener);
    return () => listeners.delete(listener);
  };

  const waitFor = (method, timeoutMs = 15000) =>
    new Promise((resolve) => {
      const timer = setTimeout(() => {
        off();
        resolve(null);
      }, timeoutMs);
      const off = on((message) => {
        if (message.method === method) {
          clearTimeout(timer);
          off();
          resolve(message);
        }
      });
    });

  const close = () => {
    ws.close();
    chrome.kill();
    // Chrome may hold the profile for a moment after exit; a leftover temp dir is harmless.
    setTimeout(() => {
      try {
        rmSync(profileDir, { recursive: true, force: true });
      } catch {
        // still locked
      }
    }, 1000);
  };

  return { send, evaluate, on, waitFor, close };
}
