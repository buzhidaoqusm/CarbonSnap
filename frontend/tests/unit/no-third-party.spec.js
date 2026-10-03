import { readFileSync, readdirSync } from "node:fs";
import { join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";

// A stylesheet or classic script from another host in <head> blocks the whole
// app while that host is slow, and keeps the page blank when the host hangs.
// Everything the first paint needs has to come from our own build.
// (Not `new URL(path, import.meta.url)`: Vite rewrites that into a served URL.)
const frontend = resolve(fileURLToPath(import.meta.url), "../../..");
const REMOTE = /^(?:https?:)?\/\//i;

function read(path) {
  return readFileSync(join(frontend, path), "utf8");
}

describe("third-party resources", () => {
  it("are not loaded by index.html", () => {
    const html = read("index.html");
    const urls = [...html.matchAll(/\b(?:src|href)\s*=\s*["']([^"']+)["']/gi)].map((match) => match[1]);

    expect(urls.filter((url) => REMOTE.test(url))).toEqual([]);
  });

  it("are not imported by any stylesheet", () => {
    const files = readdirSync(join(frontend, "src"), { recursive: true })
      .map((file) => `src/${file.replaceAll("\\", "/")}`)
      .filter((file) => /\.(css|vue)$/.test(file));
    const remote = files.flatMap((file) =>
      // @import "…", @import url(…), and url(…) in @font-face or anywhere else.
      [...read(file).matchAll(/(?:@import\s+["']|url\(\s*["']?)([^"')\s;]+)/gi)]
        .map((match) => match[1])
        .filter((url) => REMOTE.test(url))
        .map((url) => `${file}: ${url}`),
    );

    expect(files.length).toBeGreaterThan(10);
    expect(remote).toEqual([]);
  });
});
