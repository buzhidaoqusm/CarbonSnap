import { defineConfig } from "vite";
import vue from "@vitejs/plugin-vue";

export default defineConfig({
  plugins: [vue()],
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
