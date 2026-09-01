import { defineConfig } from "vite";
import vue from "@vitejs/plugin-vue";

// Proxies /api and /media to the FastAPI backend during local dev so the
// frontend can call relative paths (e.g. `/api/v1/episodes`) without
// hardcoding a host, and CORS never enters the picture in dev.
export default defineConfig({
  plugins: [vue()],
  server: {
    port: 5173,
    proxy: {
      "/api": {
        target: "http://localhost:8000",
        changeOrigin: true,
      },
      "/media": {
        target: "http://localhost:8000",
        changeOrigin: true,
      },
    },
  },
});
