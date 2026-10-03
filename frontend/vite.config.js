import { fileURLToPath } from "node:url";

import { defineConfig } from "vite";
import vue from "@vitejs/plugin-vue";
import tailwindcss from "tailwindcss";

export default defineConfig({
  plugins: [vue()],
  css: {
    postcss: {
      // An absolute path, so the build finds the config from any working directory.
      plugins: [tailwindcss({ config: fileURLToPath(new URL("./tailwind.config.js", import.meta.url)) })],
    },
  },
  test: {
    environment: "jsdom",
    globals: true,
    // The AI chat view specs drive real typing/streaming animations, which
    // take ~4s alone and longer when files run in parallel on a loaded CI box.
    testTimeout: 30000,
    hookTimeout: 30000,
  },
  server: {
    port: 5173,
    proxy: {
      "/api": {
        target: "http://127.0.0.1:5000",
        changeOrigin: true,
      },
    },
  },
});
