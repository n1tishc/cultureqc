# cultureQC workspace redesign

Implemented September 9, 2026. This document describes the current React
frontend and supersedes the landing-page sections of DESIGN.md. The Gradio
console is a separate surface. No Impeccable workflow was used for this redesign.

## Three reference products
 
### Updated navigation

The primary navigation now contains Home (`#/home`, the default), Demo
(`#/demo`), and Upload your data (`#/upload`). Home introduces the microscopy
workflow with a real, labeled sample preview. Demo contains the image explorer,
dataset summary, benchmarks, and audit trail as secondary navigation. The old
`#/analysis` URL opens Demo. Uploaded image state persists across page changes.
The interface uses restrained teal accents, white surfaces, larger navigation
targets, and generous spacing. Sample results are explicitly marked as demo data.

Validated the production build and local browser navigation, sample overlays,
record count, and overflow at 375, 768, 1024, and 1440 px. Live inference was not
invoked during these interface checks.

These are the three selected references for this use case, not an objective
ranking of every scientific website. Official product pages, interface imagery,
and documentation informed the design.

| Reference | Relevant evidence | Applied to cultureQC |
| --- | --- | --- |
| [CZ CELLxGENE Explorer](https://cellxgene.cziscience.com/docs/04__Analyze%20Public%20Data/4_1__Hosted%20Tutorials) | Its documentation describes sample metadata on the left, a central visualization, and features on the right. The official [interface screenshot](https://cellxgene.cziscience.com/doc-site/4a_tabulasapiens_cldn7.png) shows this arrangement. | A searchable specimen library, central microscopy image, and adjacent analysis inspector. Quiet light surfaces and compact contextual controls. |
| [Sartorius Incucyte](https://www.sartorius.com/en/products/live-cell-imaging-analysis/live-cell-analysis-software) | The software emphasizes navigating images, locating outliers, and validating segmentation using metric overlays. The [official analysis guide](https://www.sartorius.com/download/1163270/incucyte-basic-analysis-software-guidelines-8000-0522-d00-data.pdf) illustrates the image/measurement workflow. | A dataset quality breakdown, status filters, specimen thumbnails, and independent segmentation/evidence controls. |
| [ZEISS arivis](https://www.zeiss.com/microscopy/en/products/software/advanced-image-analysis.html) | Its product family separates image visualization/analysis, scaled batch processing, and model training. The [Pro product page](https://www.zeiss.com/microscopy/en/products/software/arivis-pro.html) presents microscopy as the central work surface. | Dedicated explorer, upload, benchmark, provenance, and integration destinations; image evidence stays next to its interpretation. |

## Design decisions

- Replace the long landing-page presentation with a working data-review app.
- Use a white navigation rail, pale cool-gray canvas, teal interactive controls,
  and consistent green/amber/red QC status labels with icons and words.
- Use existing self-hosted Archivo for UI and IBM Plex Mono for record data.
- Compute dataset counts and distributions from the existing nine records.
  No new performance figures, customers, or model output were introduced.
- Preserve the recorded/live distinction: the overview and explorer show
  recorded output; uploaded files receive verdicts only from the analysis API.
- Use the source image's aspect ratio and normalized evidence coordinates.
- Keep uploads and other visited pages mounted across navigation. Re-measure
  image frames when their container becomes visible or changes size.
- On phones, collapse navigation into a drawer, make the specimen library a
  horizontal selector, and stack the results below the image.

## Implementation

`site/src/App.jsx` owns navigation and retained page state.
`site/src/components/Workspace.jsx` owns the overview, explorer, and inspector.
`site/src/styles.css` is replaced with the shared workspace system. Existing
upload, hashing, ZIP parsing, audit verification, recorded data, and microscopy
rendering are reused. The original marketing components are no longer in the
application entry flow; their files are retained to avoid deleting prior work.

## Verification

- Production Vite build.
- Isolated headless browser: status filters, search and empty recovery,
  specimen selection, layer toggle, JSON download, audit verify/tamper/restore,
  and upload preservation across navigation.
- All seven routes checked for page overflow at 390, 768, 1024, and 1920px.
- Desktop and mobile screenshot inspection; no browser runtime errors.
- Existing user images were not sent to an external analysis service during QA.
