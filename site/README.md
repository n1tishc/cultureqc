# cultureQC v0.3 site

React 18 on Vite. `npm run build` (from the repo root) emits `site/dist`, which
is what the v0.3 Vercel project serves at https://cultureqc-cvoy.vercel.app. The v0.2 site stays on `main` and
`cultureqc.vercel.app`.

## Layout

| Path | What it is |
|---|---|
| `index.html`, `validation.html`, `release-notes.html` | the three pages; each names its page on `<body data-page>`. Vercel's `cleanUrls` serves `/validation` and `/release-notes`, and `vite.config.js` does the same locally |
| `src/main.jsx` | picks the page component from `data-page` |
| `src/pages/Home.jsx` | the product page: hero, the stage, how it works, accuracy, flask history, records, integration, measured performance, scope |
| `src/pages/ValidationPage.jsx` | confluency against expert masks, the V1–V10 checks, and the detectability matrix with real-size contamination |
| `src/pages/ReleaseNotesPage.jsx` | release notes for v0.3 and v0.2 |
| `src/components/Shell.jsx` | the top bar, closing call to action, footer and secondary-page header shared by every page |
| `src/components/Stage.jsx` | the hero instrument: a real frame, its computed layers (cell probability, cutoff contour, borderline band, anomaly patches), the readout rail, the seven-example strip |
| `src/components/Product.jsx` | the home page's how-it-works steps, accuracy feature, measured-performance datasheet and scope |
| `src/components/Timeline.jsx` | the five held-out flask replays: per-visit map with its three fields, the growth chart, quality gate, flags and the passage forecast |
| `src/components/Records.jsx` | the record chain, re-hashed in the browser, with the tamper switch |
| `src/components/Sections.jsx` | confluency figures, detectability, validation, integration and the release notes |
| `src/lib/verify.js` | SHA-256 over each record's stored canonical JSON, and the chain links |
| `src/data.json` | **generated** by `assets/build_data.py`; never edit by hand |
| `public/img/v3/` | **generated** layers, thumbnails, replay maps and the contamination figure |

## Rules the page keeps

- No number is typed into a component. They come from `data.json`, which copies
  them from the README tables (checked by `tests/test_readme_provenance.py`),
  the console's examples and records, the replays, `configs/detectability.yaml`
  and `results/review_rate.csv`.
- `tests/test_claims.py` scans the components' text with the same claims policy
  as the README and the console.
- Cyan is what the segmentation model computed and magenta what the anomaly
  check computed; action colours mean actions only, and each travels with its
  word and its own mark.
