import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    // The API and the page share an origin in local development: api.py serves
    // /health and /analyze on 7860, and this proxy puts them on the dev origin
    // too, so the browser takes the same-origin path it takes in production
    // against the Space — no CORS difference between dev and deployed.
    proxy: {
      "/health": "http://127.0.0.1:7860",
      "/analyze": "http://127.0.0.1:7860",
    },
  },
  build: {
    outDir: "dist",
    assetsDir: "assets",
    // The reference data is one 33 KB JSON import; leaving it in the main chunk
    // avoids a second round trip for something every view needs.
    chunkSizeWarningLimit: 700,
  },
});
