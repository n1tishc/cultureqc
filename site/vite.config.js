import { execSync } from "node:child_process";
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

/* The footer names the commit the page was built from: Vercel provides it;
   a local build asks git. */
function commit() {
  if (process.env.VERCEL_GIT_COMMIT_SHA) return process.env.VERCEL_GIT_COMMIT_SHA;
  try {
    return execSync("git rev-parse HEAD", { stdio: ["ignore", "pipe", "ignore"] }).toString().trim();
  } catch {
    return "";
  }
}

export default defineConfig({
  plugins: [react()],
  define: { __COMMIT__: JSON.stringify(commit()) },
  build: {
    outDir: "dist",
    assetsDir: "assets",
    chunkSizeWarningLimit: 700,
  },
});
