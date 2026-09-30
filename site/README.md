# cultureQC v0.3 site

React 18 on Vite. `npm run build` (from the repo root) emits `site/dist`, which
is what the v0.3 Vercel project serves at https://cultureqc-cvoy.vercel.app. The v0.2 site stays on `main` and
`cultureqc.vercel.app`.

## Layout

| Path | What it is |
|---|---|
| `src/App.jsx` | the page: top bar, hero, and the sections in order |
| `src/components/Stage.jsx` | the hero instrument: a real frame, its computed layers (cell probability, cutoff contour, borderline band, anomaly patches), the readout rail, the seven-example strip |
| `src/components/Timeline.jsx` | the five held-out flask replays: per-visit map with its three fields, the growth chart, quality gate, flags and the passage forecast |
| `src/components/Records.jsx` | the record chain, re-hashed in the browser, with the tamper switch |
| `src/components/Sections.jsx` | confluency trust, limits, validation, integration, what changed since v0.2, footer |
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
