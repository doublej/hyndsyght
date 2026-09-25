import { defineConfig } from "vite";
import { svelte } from "@sveltejs/vite-plugin-svelte";

// https://vite.dev/config/
export default defineConfig({
  plugins: [svelte()],
  server: {
    proxy: {
      // dev mode: FastAPI isn't in Vite's own dev server loop, so proxy to
      // `hyndsyght serve`'s default port. changeOrigin rewrites Host so the
      // backend's Host-header guard still passes.
      "/api": { target: "http://127.0.0.1:8420", changeOrigin: true },
    },
  },
});
