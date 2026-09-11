/* Deployment-shape decisions. Everything here is read once at module load. */

/* ─── swap these when the links exist ─── */
export const DEMO_VIDEO = ""; /* URL of the console screen recording */
export const REPO_URL = "https://github.com/n1tishc/cultureqc"; /* public GitHub repository */
export const LINKEDIN_URL = ""; /* public LinkedIn profile */
export const CONTACT = ""; /* contact email address, no mailto: prefix */

/* Public analysis API, e.g. "https://api.example.org". Empty means none exists,
   which is the honest default: hosted, this page hashes and manifests files and
   states plainly that it does not analyse them. Set this and every visitor gets
   real verdicts from the real pipeline — nothing else has to change. */
export const ANALYSIS_API = "https://longgrainrice-cultureqc-api.hf.space";

export const MAX_FILES = 200;
export const MAX_BYTES = 64 * 1024 * 1024;

/* Whoever opened this from disk or from an address on their own network is
   running the repo, so the endpoint control is theirs to use. To a visitor on
   the hosted site it is plumbing for a machine they do not have: it never
   renders, and no word of it appears in the copy. Public + no ANALYSIS_API is a
   complete state, not a broken one, and the page is written that way.

   Private ranges count as local because the dev server is routinely opened by
   LAN IP to demo it on a phone or a second laptop; treating that as public would
   drop the analysis path silently, which is the worst way to lose a feature. */
export const LOCAL_TOOLING = (() => {
  const h = location.hostname;
  if (["localhost", "127.0.0.1", "[::1]", "::1", ""].includes(h)) return true;
  if (h.endsWith(".local") || h.endsWith(".localhost")) return true;
  return (
    /^10\./.test(h) ||
    /^192\.168\./.test(h) ||
    /^172\.(1[6-9]|2\d|3[01])\./.test(h)
  );
})();

export const CAN_ANALYSE = !!ANALYSIS_API || LOCAL_TOOLING;

/* In development, vite.config.js proxies /health and /analyze to the API on
   7860, so the page's own origin is the endpoint — which keeps working when the
   dev server is reached by LAN IP, where a hard-coded 127.0.0.1 would point at
   the visitor's own machine instead of the one running the pipeline. */
export const DEFAULT_ENDPOINT = location.protocol.startsWith("http")
  ? location.origin
  : "http://127.0.0.1:7860";

/* Local tooling wins locally. Someone running the repo is pointing the page at
   the pipeline on their own machine; sending them to the hosted service instead
   would test the wrong thing and fail whenever it is asleep. */
export const START_ENDPOINT = LOCAL_TOOLING ? DEFAULT_ENDPOINT : ANALYSIS_API;

/* Deliberate, not a leak. The deployment-state test suites assert on these from
   outside the bundle (`page.evaluate("CAN_ANALYSE")`) because which state the
   page is in is exactly what they exist to check, and a bundler otherwise makes
   that unobservable. They are constants derived from location — nothing a
   visitor could set changes what the page does. */
Object.assign(window, {
  LOCAL_TOOLING,
  CAN_ANALYSE,
  START_ENDPOINT,
  ANALYSIS_API,
  DEFAULT_ENDPOINT,
});
