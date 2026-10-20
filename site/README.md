# cultureQC standalone product site

React 18 on Vite. `npm run build` (from the repo root) emits `site/dist`.
Use `npm --prefix site run dev -- --host 127.0.0.1 --port 5173 --strictPort`
for local review. Publishing requires separate owner approval; local source
does not establish the revision on any public URL. See the
[release-state map](../docs/specs/release-state.md) and [current product brief](../docs/PRODUCT.md).

## Layout

| Path | What it is |
|---|---|
| `index.html`, `records.html`, `validation.html`, `release-notes.html` | four pages, selected by `<body data-page>`; Vercel clean URLs and Vite local routes share these entry points |
| `src/main.jsx` | picks the page component from `data-page` |
| `src/pages/Home.jsx` | standalone product journey: one stored analysis, Measure/Understand/Trace, host boundary, evidence and offline evaluation; technical appendix is secondary |
| `src/pages/RecordsPage.jsx` | exact-record selection, historical chain verification and separate illustrative review extension |
| `src/pages/ValidationPage.jsx` | fine-tuning evidence, setup calibration, confluency against expert masks and scoped detectability; historical V1–V10 architecture tables are not the main presentation |
| `src/pages/ReleaseNotesPage.jsx` | release notes for v0.3 and v0.2 |
| `src/components/Shell.jsx` | the top bar, closing call to action, footer and secondary-page header shared by every page |
| `src/components/Stage.jsx` | the hero instrument: a real frame, its computed layers (cell probability, cutoff contour, borderline band, anomaly patches), the readout rail, the seven-example strip |
| `src/components/Product.jsx` | the home page's how-it-works steps, accuracy feature, measured-performance datasheet and scope |
| `src/components/Timeline.jsx` | the five held-out flask replays: per-visit map with its three fields, the growth chart, quality gate, flags and the passage forecast |
| `src/components/Records.jsx` | the record chain, re-hashed in the browser, with the tamper switch |
| `src/components/ReviewExample.jsx` | explicitly fictional review linked to the unchanged HT29 reading, not a real approval or signature |
| `src/components/Sections.jsx` | confluency figures, detectability, validation, integration and the release notes |
| `src/lib/verify.js` | SHA-256 over each record's stored canonical JSON, and the chain links |
| `src/data.json` | **generated** by `assets/build_data.py`; never edit by hand |
| `public/img/v3/` | **generated** layers, thumbnails, replay maps and the contamination figure |

## Rules the page keeps

- No number is typed into a component. They come from `data.json`, which copies
  them from the README tables (checked by `tests/test_readme_provenance.py`),
  the console's examples and records, the replays, `configs/detectability.yaml`,
  `results/confluency_profiles.json`, and `results/review_rate_v05.csv` (with
  `results/review_rate.csv` for the `rules_v0.4` comparison).
- `tests/test_claims.py` scans the components' text with the same claims policy
  as the README and the console.
- Cyan is what the segmentation model computed and magenta what the anomaly
  check computed; action colours mean actions only, and each travels with its
  word and its own mark.

## Artifact boundaries

Run `.venv/bin/python site/assets/build_data.py` from the repository root to
regenerate data (requires numpy, pyyaml and jsonschema). Do not edit JSON by hand.
`meta.schema` / `meta.rules` identify local source at generation time, not a
remote runtime. Stored reading bytes retain schema `0.4` / `rules_v0.5`.
The generator copies the nine-record historical chain to a temporary file,
appends one fictional review using `review_event` / `RecordWriter`, validates
it and exports a separate `examples.review_demo`. Identity, timestamps and
review reason are illustrative; there is no signature or action authorization.
Both checkpoints ship with the page; production anchors need independent storage.
Source logs are never rewritten. `node --test site/tests/*.test.js` exercises
both verifiers, including tampering and mismatched reading references.

## Proof-journey browser checks

With the local Vite server running on port 5173, read `ego-browser skill`, then
run from the repository root:

```sh
ego-browser nodejs < site/tests/proof-journey.browser.js
ego-browser nodejs < site/tests/proof-pointer.browser.js
```

Each standalone regression owns one task space and finishes it on success.
The pointer regression checks 1440px and 390px viewport widths with reduced
motion, including review disclosure and contained JSON overflow. All navigation
uses selector-based pointer clicks with automatic browser scrolling; the earlier
chain-link workaround was removed after the approved browser update and retest.
Neither regression proves physical touch, screenshot-based visual acceptance,
screen-reader speech or actual 200% browser zoom. See the
[post-update visual record](../docs/reviews/2026-10-20-proof-visual-acceptance.md).
