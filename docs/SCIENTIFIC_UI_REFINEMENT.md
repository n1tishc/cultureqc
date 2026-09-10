# Scientific imaging UI refinement

Applied the user-requested ui-ux-pro-max guidance to the existing React UI:
readable typography, explicit workflow steps, visible state, usable targets,
responsive layouts, and preserved reduced-motion behavior.

## Reference patterns

- [CELLxGENE Explorer](https://cellxgene.cziscience.com/docs/04__Analyze%20Public%20Data/4_1__Hosted%20Tutorials): metadata/selection alongside the visualization and a separate feature inspector. Retained the image-centered three-panel layout and enlarged its controls and result text.
- [Sartorius Incucyte](https://www.sartorius.com/en/products/live-cell-imaging-analysis/live-cell-analysis-software): guided analysis, image navigation, and metric overlays. Added explicit upload steps and previous/next navigation through the filtered specimen collection.
- [ZEISS arivis Pro](https://www.zeiss.com/microscopy/en/products/software/arivis-pro.html): image analysis and visualization as the product focus. Kept the interactive layers and sample challenge while clarifying the home page's scientific purpose.

These patterns inform the design; this is not a copy of the reference products
or an assertion that cultureQC has their capabilities.

## Changes and checks

Home now introduces the analysis capabilities and the Explore / Analyse / Verify
workflow. Demo has larger text, accessible previous/next controls, and responsive
image/inspector placement. Upload explains expected inputs and CPU latency and
shows the current workflow step. Existing model and record logic is preserved.

Verified production build, navigation across specimens, input-dependent upload
progress, browser errors, and overflow at 375, 768, 1024, and 1440px. Existing
3D controls, QC challenge, and reduced-motion checks are retained.
