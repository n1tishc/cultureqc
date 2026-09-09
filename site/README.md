# cultureQC landing page

React 18 on Vite. `npm run build` emits `site/dist`, which is what Vercel serves.

```bash
npm install
npm run dev      # http://localhost:5173, proxying /health and /analyze to :7860
npm run build    # -> dist/
npm run preview  # serve that build
npm run data     # regenerate src/data.json + public/img from pipeline output
```

## Layout

| Path | What it is |
|---|---|
| `src/App.jsx` | the hash router and both view panels |
| `src/components/` | `Plate`, `Hero`, `Leaf`, `Upload`, `Chain`, `Ladder`, `Rail`, … |
| `src/lib/` | `hash.js` (SHA-256 + canonical JSON), `zip.js`, `labels.js` |
| `src/styles.css` | the whole visual world, one file |
| `src/config.js` | `ANALYSIS_API` and the deployment-state constants |
| `src/data.json` | **generated** — real pipeline output the page renders |
| `assets/` | source images, fonts, and the scripts that produce them |
| `public/` | shipped as-is: `og.png`, `favicon.png`, `img/` |

Two things the code depends on and neither `npm run build` nor React will warn
you about:

**`styles.css` drives state through attributes, not classes alone.**
`[data-mask]`, `[data-boxes]`, `[data-s]`, `[data-v]`, `[data-flagged]`, and the
`--rail-h` / `--nw` / `--nh` custom properties. Components set those exact
attributes. Rename one and the design breaks silently — the markup still renders,
it just stops being styled.

**`src/data.json` is generated.** `assets/build_data.py` reads the committed
pipeline output in `assets/pipeline-output/` and `assets/ladder/`. Hand-editing
the JSON would make the page display records the pipeline never wrote, which is
the one thing this page cannot do. CI re-runs the script and fails on any diff.

## Two views

Two tab-switched views, hash-routed and deep-linkable:

| Route | View | What it is for |
|---|---|---|
| `#/overview` (default) | **Overview** | The argument: what it does, the 2.3 pp vs 31 pp head-to-head, 100% early recall, software-not-an-instrument. A compact plate runs the scan-and-verdict animation in the first viewport. |
| `#/analysis` | **Analysis** | The evidence: the nine-specimen instrument, **your own uploads**, the confluency table, the full severity matrix, the audit chain and the provenance disclosures. |

Browser back/forward work, `aria-selected` tracks the tab, arrow keys move
between tabs, and the fore-edge index rebuilds itself per view. Both panels stay
mounted and one is `hidden`, so a batch you uploaded survives a tab switch.

## Running your own images

The Analysis view accepts a single image, many images, or a `.zip` (parsed in the
browser with `DecompressionStream`, no library — stored and deflated entries, no
ZIP64).

Every file is hashed with WebCrypto and linked into a *hash-chained ingest
manifest* built in the browser. That manifest is real and verifiable:
`image_hash` is the same SHA-256 `culture/records.py::hash_file` would write, and
**Verify** recomputes the whole chain on the spot. The page never estimates a
confluency or a QC flag itself — there is no model in the browser, and inventing
a number here would undercut the whole argument.

Verdicts need the pipeline, and where the page can reach one depends on where it
is served from. `location.hostname` decides, in `LOCAL_TOOLING`:

| Served from | Endpoint control | What a visitor gets |
|---|---|---|
| `localhost`, `127.0.0.1`, a private LAN address | shown, probes the local endpoint first | manifest, plus real verdicts once the API is running locally |
| a public host, `ANALYSIS_API` empty | **not rendered at all** | manifest only, stated plainly as a deliberate limit |
| a public host, `ANALYSIS_API` set | status only, no URL box | manifest, plus real verdicts from that API |

The middle row is written as a complete state rather than a degraded one: the
readiness panel is removed from the DOM rather than hidden, the Analyse button is
withdrawn rather than disabled, rows read `hashed · not analysed` rather than
`pending`, and no word of the endpoint appears in the copy. Nothing in the
shipped page mentions plumbing unless it is actually usable.

A batch caps at 200 files and 64 MB per file, runs three requests at a time, and
can be cancelled mid-run. TIFFs are hashed and analysed but cannot be previewed —
browsers do not decode TIFF, so those rows show a "no preview" placeholder rather
than a broken image.

**Analysis is slow on CPU** — tens of seconds per tile, minutes for a full
704×520 field, plus a cold boot if the Space is asleep. The 200-file cap is far
beyond what is practical against a CPU backend.

**The API keeps nothing.** It writes each upload to a temp directory, analyses
it, and reduces `image_ref` to the filename in the response — `analyze()` would
otherwise record an absolute path into a directory that is deleted moments later,
which is an audit trail you cannot follow back to its evidence. The hash-chained
log it appends to is per-boot, because a HuggingFace Space's disk is wiped on
restart; the browser's own manifest chain over your batch is where continuity
lives for a visitor.

## Things to fill in

`src/config.js`:

```js
export const DEMO_VIDEO = "";   /* URL of the console screen recording */
export const REPO_URL   = "";   /* public GitHub repository */
export const CONTACT    = "";   /* contact email address, no mailto: prefix */
```

While a value is empty the page does not render a dead link: the Source and
Get-in-touch buttons are omitted entirely, and the primary **See it run** action
falls back to the analysis view. Fill any of the three and its link appears.

`ANALYSIS_API` in the same file is the one switch between "hosted visitors get a
verifiable manifest" and "hosted visitors get real verdicts". Anything answering
`GET /health` with `{"status":"ok","models_loaded":true}` and a multipart
`POST /analyze` the way `deploy/hf-space/api.py` does will work unchanged.

The absolute site URL lives in `index.html`, in the `og:image` and `canonical`
tags — crawlers do not resolve relative URLs, and `og.png` is the one asset
referenced by full origin for that reason.

## Where the numbers come from

Nothing on the page is mocked up. Every figure, mask, evidence box and hash was
produced by this repo's own pipeline before the page was written:

| Source | What it produced |
|---|---|
| `assets/regen.py` | Composited contamination onto a full 704×520 Huh7 field with `scripts/synth_contamination.py`, then ran `culture.seg` + `culture.qc` + `culture.rules` over nine images — real Cellpose-SAM masks, real Grad-CAM boxes, and nine real hash-chained records via `culture.records.RecordWriter`. Output in `assets/pipeline-output/` (including `events.jsonl`, chain verified intact). |
| `assets/ladder/` | The contamination severity ladder: four real fields × clean/early/mid/late, built with the project's own synthesis at native sprite scale and passed through the shipped classifier. 12/12 contaminated tiles flagged at 1.000, 4/4 clean controls normal. |
| `assets/prep_assets.py` | Converted the above to WebP. Output in `assets/web/`. |
| `assets/build_data.py` | Copies the WebP into `public/img/` and writes `src/data.json`. |
| `assets/make_og.py` | Builds `public/og.png` and `public/favicon.png` from the same output — the composited Huh7 field, the classifier's own Grad-CAM box on it, and the real confluency, flag, action and record hash. It does the cover-crop arithmetic in Python so the box lands on the region it was actually measured on rather than sliding out from under the crop. |

Full rebuild from the pipeline is slow, because it runs the models:

```bash
.venv/bin/python site/assets/regen.py
.venv/bin/python site/assets/prep_assets.py
python site/assets/build_data.py
```

### Two findings worth carrying back into the product

**`demo/app.py::_scale_bboxes` over-scales evidence boxes on non-256px images.**
The Grad-CAM box comes from a centred 256×256 crop, so mapping it back to a
704×520 field should offset the origin only — the box's own width and height stay
in tile pixels. The console multiplies them by the full-image scale factor
(2.75× horizontally), so a full-frame box draws far wider than the region
actually analysed and runs off the image. Both the page
(`assets/build_data.py::fix_boxes`) and the API
(`deploy/hf-space/api.py::_boxes_normalised`) have the correct mapping; the
console still has the bug.

**The QC classifier is sensitive to bacterial sprite scale.** Rescaling the
sprite library and re-running the shipped classifier: on the single tile tested
at 0.45× the model still flagged it at 0.999, but that is one tile, not recall.
Across the full twelve-tile severity ladder at 0.45×, only 6 of 12 contaminated
tiles were flagged, and at 0.2× the model reads contamination as an
image-quality artifact instead. The 100% figure quoted on the page is measured at
the sprites' native optical scale, which is larger relative to the cells than a
real objective would show, so it is bounded to that synthetic distribution. The
page discloses this in its provenance section rather than hiding it.

## The chain is real

The **Verify chain** control is not a picture of a hash chain. `src/data.json`
carries the canonical JSON of each record exactly as `culture/records.py`
serialised it (`sort_keys=True, separators=(",",":"), ensure_ascii=True`), and
`src/lib/hash.js::canonJSON` reproduces that byte for byte in JavaScript. The
page recomputes each SHA-256 with WebCrypto and compares against the stored
digest and the next record's `prev_record_hash`.

The tamper control mutates one field of leaf 05. Two rows then fail: leaf 05 on
its own digest, and leaf 06 because its stored `prev_record_hash` no longer
matches what was just recomputed. Leaf 07 links to leaf 06's *untouched* record,
whose digest still comes out right, so the walk heals from there — the status
line's "every record after it is unprovable" is stronger than what the rows show.

## Claims on the page

Only the briefed product truth is stated: 2.3 pp vs ~31 pp confluency error, 98%
test accuracy, 100% contamination recall at all severities, the four bound
outputs, vendor-neutral "software, not an instrument", and the GMP-traceable
audit record. There are no invented customers, prices, vendor logos, or
capabilities. The confluency comparison table is labelled as *disagreement
between two methods on the same field*, not as labelled error — the benchmark
figures are stated separately. The synthetic-training-data provenance is
disclosed in its own section, matching the console's permanent footer disclosure.

## Fonts

Archivo (variable, weight + width axes) and Martian Mono (variable), latin
subset, in `src/assets/fonts/` and fingerprinted by Vite. Archivo's width axis
carries the hierarchy — condensed for display, expanded for reading. Both have
real fallback stacks.
