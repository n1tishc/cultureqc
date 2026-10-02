import { execSync } from "node:child_process";
import { resolve } from "node:path";
import { fileURLToPath } from "node:url";
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

/* Three pages. Vercel's cleanUrls serves /validation from validation.html;
   this does the same for `vite` and `vite preview`, so links read the same. */
const PAGES = ["validation", "release-notes"];
const ROOT = fileURLToPath(new URL(".", import.meta.url));

function cleanUrls() {
  const rewrite = (req, _res, next) => {
    const path = (req.url || "").split(/[?#]/)[0].replace(/\/$/, "");
    if (PAGES.includes(path.slice(1))) req.url = req.url.replace(path, `${path}.html`);
    next();
  };
  return {
    name: "clean-urls",
    configureServer: (server) => server.middlewares.use(rewrite),
    configurePreviewServer: (server) => server.middlewares.use(rewrite),
  };
}

export default defineConfig({
  plugins: [react(), cleanUrls()],
  define: { __COMMIT__: JSON.stringify(commit()) },
  build: {
    outDir: "dist",
    assetsDir: "assets",
    chunkSizeWarningLimit: 700,
    rollupOptions: {
      input: {
        index: resolve(ROOT, "index.html"),
        ...Object.fromEntries(PAGES.map((p) => [p, resolve(ROOT, `${p}.html`)])),
      },
    },
  },
});
