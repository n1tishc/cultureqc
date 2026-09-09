/* One shared media query. Every timed sequence collapses to 0 ms when it matches,
   rather than being skipped — the end state is identical, it just arrives at once. */
export const RM = window.matchMedia("(prefers-reduced-motion: reduce)");

/* A 1×1 transparent GIF. The <img> elements exist before a leaf is chosen, and a
   real src beats an empty one: no broken-image glyph, no console noise. */
export const BLANK =
  "data:image/gif;base64,R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7";
