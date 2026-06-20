import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Production web client for IRBIS64. Dev server proxies /api to the Python backend.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: { "/api": "http://127.0.0.1:8080" },
  },
  build: {
    outDir: "dist",
    emptyOutDir: true,
    sourcemap: false,
  },
});
