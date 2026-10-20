# I2 — Standalone homepage and shared shell

Dependency: I1. Owner: same frontend builder.

Execution status: implemented 2026-10-16; scoped layout, route and build checks pass. Screenshot-based visual acceptance remains pending under V2. See the [I2 handoff](../../reviews/2026-10-16-i2-homepage-handoff.md).

Owned files: `site/src/pages/Home.jsx`, `site/src/components/Journey.jsx`, `site/src/components/Journey.css`, `site/src/components/Shell.jsx`, `site/src/styles.css`, homepage metadata in `site/index.html`. I3 supplies supporting copy but never edits these shared files concurrently.

V1 correction scope, 2026-10-16: the homepage owner also edits only the inherited calibration/action explanations in `site/src/components/Product.jsx` for finding F2. Preserve its IDs, figures and scientific inputs; this is not a redesign of the technical appendix.

## Implementation

1. Replace Upgrade's comparison-first content with the C0 hero. Remove the homepage version-comparison table rather than collapsing it into the primary journey. Keep historical release notes unchanged unless correcting a broken link. Release number may remain discreet metadata, never the value proposition.
2. Mount the actual reusable Stage once, immediately after the short hero. Remove the “Three cases” heading and duplicate explanatory preamble. Do not introduce a screenshot mockup above another real demo.
3. Follow with a compact Measure → Understand → Trace explanation. Each statement describes existing behavior; traceability links to Records, with the selected exact-record link continuing to live in Stage.
4. Add a host → cultureQC → host workflow: capture/context in, measurement/recommendation/record out, host review/retention/action. State that this is the intended boundary, not a shipped partner integration. Link to `/records#integration`.
5. Keep one concise evidence finding with dataset, protocol, sample count, qualification and source link together. Use the C0 claim contract. Full results belong on `/validation`; do not reproduce its tables.
6. Replace the full homepage Trail ledger with a compact `#trail` handoff, retaining Records' actual verification/tamper tools. Preserve any verification still consumed by Stage or technical details; don't delete it merely because the ledger moves.
7. Keep `#pilot` as the concrete next step: one setup, representative images + independent labels + intended target, frozen protocol before scoring, readout/error/review burden and limitations, agreed decision gate. Do not invent sufficient sample sizes, deadlines, savings or a submission backend. State offline/non-actuating scope and unresolved readiness separately.
8. Apply C0 navigation on every page through Shell. Keep the optional live console secondary and distinctly labelled. Retain all legacy routes/anchors and the technical appendix's auto-opening behavior. Update homepage title/description to the standalone proposition without unsupported SEO claims.

## Acceptance

- **I2-A:** At 1280×800 and 100% zoom, the initial viewport contains the hero, visible microscopy and its measurement/recommendation; it is not consumed by navigation/copy. After following Explore an analysis, image, compact result, scope and record link can be inspected together without scrolling the desktop workspace. Reduce chrome, not scope legibility, to fit.
- **I2-B:** At 390×844, no horizontal page overflow or clipped navigation. Image precedes compact result; vertical scrolling is expected. Also check 320px width and 200% text zoom/reflow; no fixed-height content clipping.
- **I2-C:** Main sequence matches C0 and contains exactly one Stage; there is no version comparison or repeated full ledger in the primary narrative. Specialist legacy content remains reachable.
- **I2-D:** All nav/CTA/footer links work from all four page entries. Evaluate goes to the actual plan, not the external console. Evidence is a page destination, not a misleading active-section highlight.
- **I2-E:** Existing fonts/tokens remain coherent, microscopy has more visual weight than decorative chrome, and all claims have the qualifications C0 requires. No fake counts, decorative badges or hidden material limitations.

Handoff: component/order map, link inventory, shared-copy changes coordinated with I3, and desktop/mobile requirements for V2.
