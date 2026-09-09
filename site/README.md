# cultureQC landing page

`index.html` is the deliverable: one self-contained file, ~740 KB, no build step and no
external requests. Fonts, every microscopy image, and every record are inlined as
base64 / data URIs. Drop it on any static host, or open it from disk.

## Two views

The page is two tab-switched views, hash-routed and deep-linkable:

| Route | View | What it is for |
|---|---|---|
| `#/overview` (default) | **Overview** | The argument: what it does, the 2.3 pp vs 31 pp head-to-head, 100% early recall, software-not-an-instrument, provenance. A compact plate runs the scan-and-verdict animation in the first viewport. |
| `#/analysis` | **Analysis** | The evidence: the nine-specimen instrument, **your own uploads**, the confluency table, the full severity matrix, and the audit chain. |

Browser back/forward work, `aria-selected` tracks the tab, arrow keys move between tabs,
and the fore-edge index rebuilds itself per view.

## Running your own images

The Analysis view accepts a single image, many images, or a `.zip` (ZIP is parsed in the
browser with `DecompressionStream`, no library — stored and deflated entries, no ZIP64).

Every file is hashed with WebCrypto and linked into a *hash-chained ingest manifest* built
in the browser. That manifest is real and verifiable: `image_hash` is the same SHA-256
`culture/records.py::hash_file` would write, and **Verify** recomputes the whole chain on
the spot. The page never estimates a confluency or a QC flag itself — there is no model in
the browser, and inventing a number here would undercut the whole argument.

Verdicts need the pipeline, and where the page can reach one depends on where it is served
from. `location.hostname` decides, in `LOCAL_TOOLING`:

| Served from | Endpoint control | What a visitor gets |
|---|---|---|
| `localhost`, `127.0.0.1`, a private LAN address, `file://` | shown, probes the local endpoint first | manifest, plus real verdicts once the API is running locally |
| a public host, `ANALYSIS_API` empty | **not rendered at all** | manifest only, stated plainly as a deliberate limit |
| a public host, `ANALYSIS_API` set | status only, no URL box | manifest, plus real verdicts from that API |

The middle row is the default for a hosted deploy, and it is written as a complete state
rather than a degraded one: no "not connected", no localhost URL, no instruction to run a
Python file. Nothing in the shipped copy mentions the endpoint unless it is actually usable.

```bash
python deploy/hf-space/api.py        # http://127.0.0.1:7860 — page and pipeline, one origin
```

That serves `site/index.html` at `/` as well as the API, so there is no cross-origin hop
for Chrome's private-network checks to block. The page prefers a local endpoint over
`ANALYSIS_API` whenever it is opened from localhost, a private address, or disk, so local
work never silently tests the deployed service.

`/analyze` takes a multipart form:

```bash
curl -X POST http://127.0.0.1:7860/analyze \
     -F "image=@field.tif" -F "cell_line=Huh7" -F "target_confluency=80"
```

See `deploy/README.md` for the Space and Vercel deployments. The previous
`demo/serve.py` has been removed: it spoke an older contract (raw request body,
`{"ok": true}`) and a second server would have drifted from the deployed one.

**Analysis is slow on CPU** — roughly 50 s for a 256x256 tile and several minutes for a
full 704x520 field, measured with the models already resident. The 200-file batch cap is
far beyond what is practical against a CPU backend.

A batch caps at 200 files and 64 MB per file, runs three requests at a time, and can be
cancelled mid-run. TIFFs are hashed and analysed but cannot be previewed — browsers do not
decode TIFF, so those rows show a "no preview" placeholder rather than a broken image.

**The API keeps nothing.** It writes each upload to a temp directory, analyses it, and
reduces `image_ref` to the filename in the response — `analyze()` would otherwise record an
absolute path into a directory that is deleted moments later, which is an audit trail you
cannot follow back to its evidence. The hash-chained log it appends to is per-boot, because
a HuggingFace Space's disk is wiped on restart; the browser's own manifest chain over your
batch is where continuity lives for a visitor.

## Things to fill in

Near the top of the `<script>` block in `index.html` (also in `src/template.html`):

```js
const DEMO_VIDEO   = "";   /* URL of the console screen recording */
const REPO_URL     = "";   /* public GitHub repository */
const CONTACT      = "";   /* contact email address, no mailto: prefix */
const ANALYSIS_API = "";   /* public analysis API, e.g. https://api.example.org */
```

`ANALYSIS_API` is the one switch between "hosted visitors get a verifiable manifest" and
"hosted visitors get real verdicts". Anything answering `GET /health` with
`{"status":"ok","models_loaded":true}` and a multipart `POST /analyze` the way
`deploy/hf-space/api.py` does will work unchanged.

And one in `src/assemble.py`:

```python
SITE_URL = ""   # e.g. "https://cultureqc.example" — where the page will live
```

## Deploying

Upload three files to any static host: `index.html`, `og.png`, `favicon.png`.

`index.html` is still self-contained and makes **zero external requests** — the favicon is
inlined as a data URI. `og.png` is the single exception to that rule, and it is not fetched
by the page at all: it exists for crawlers, which do not read `data:` URIs and which need an
absolute URL for Open Graph. That is why `og:image` is emitted only once `SITE_URL` is set —
an empty value ships no tag rather than a URL that 404s.

```bash
python site/src/make_og.py     # regenerate og.png + favicon.png
python site/src/assemble.py    # then re-inline
```

`make_og.py` builds the link-preview card from real pipeline output: the composited Huh7
field the page already ships, the classifier's own Grad-CAM evidence box on it, and the
confluency, flag, action and record hash straight out of `results.json`. It does the
cover-crop arithmetic in Python so the box lands on the region it was actually measured on
rather than sliding out from under the crop.

While a value is empty the page does not render a dead link: the Source and Get-in-touch
buttons are omitted entirely, and the primary **See it run** action falls back to
scrolling to the interactive first viewport. Fill any of the three and its link appears.

Edit `src/template.html` and re-run the assembler (below) rather than editing
`index.html` by hand — the built file is generated.

## Where the numbers come from

Nothing on the page is mocked up. Every figure, mask, evidence box and hash was produced
by this repo's own pipeline before the page was written:

| Source | What it produced |
|---|---|
| `src/regen.py` | Composited contamination onto a full 704×520 Huh7 field with `scripts/synth_contamination.py`, then ran `culture.seg` + `culture.qc` + `culture.rules` over nine images — real Cellpose-SAM masks, real Grad-CAM boxes, and nine real hash-chained records via `culture.records.RecordWriter`. Output in `src/pipeline-output/` (including `events.jsonl`, chain verified intact). |
| `src/ladder/` | The contamination severity ladder: four real fields × clean/early/mid/late, built with the project's own synthesis at native sprite scale and passed through the shipped classifier. 12/12 contaminated tiles flagged at 1.000, 4/4 clean controls normal. |
| `src/prep_assets.py` | Converted the above to WebP and wrote the page's data bundle. Output in `src/web/`. |
| `src/assemble.py` | Inlined fonts, images and data into `src/template.html` → `index.html`. |

### Two findings worth carrying back into the product

**`demo/app.py::_scale_bboxes` over-scales evidence boxes on non-256px images.** The Grad-CAM
box comes from a centred 256×256 crop, so mapping it back to a 704×520 field should offset the
origin only — the box's own width and height stay in tile pixels. The current code multiplies
them by the full-image scale factor (2.75× horizontally), so a full-frame Grad-CAM box draws far
wider than the region actually analysed and runs off the image. The page corrects this in
`assemble.py::fix_boxes`; the console still has the bug.

**The QC classifier is sensitive to bacterial sprite scale.** Rescaling the sprite library and
re-running the shipped classifier: recall holds at 0.45× (0.999 on the tile tested) but collapses
below that — at 0.45× across the full ladder only 6 of 12 contaminated tiles were flagged, and at
0.2× the model reads contamination as an image-quality artifact. The sprites are composited at
their source optical scale, which is larger relative to the cells than a real objective would
show, so the reported recall is bounded to that synthetic distribution. The page discloses this
in its provenance section rather than hiding it.

The **Verify chain** control in the audit section is not a picture of a hash chain. The page
carries the canonical JSON of each record exactly as `culture/records.py` serialised it
(`sort_keys=True, separators=(",",":")`), recomputes each SHA-256 in the browser with
WebCrypto, and compares against the stored digest and the next record's `prev_record_hash`.
The tamper control mutates one field of the flagged leaf and the break cascades correctly through
every record after it.

## Regenerating

```bash
# full rebuild from the pipeline (slow — runs the models)
.venv/bin/python site/src/regen.py
.venv/bin/python site/src/prep_assets.py
.venv/bin/python site/src/assemble.py

# just re-inline after editing the template (fast)
.venv/bin/python site/src/assemble.py
```

`regen.py` and `prep_assets.py` currently read and write absolute scratch paths; point their
`HERE` / `OUT` constants at `site/src/` before re-running the slow steps.

## Claims on the page

Only the briefed product truth is stated: 2.3 pp vs ~31 pp confluency error, 98% test
accuracy, 100% contamination recall at all severities, the four bound outputs,
vendor-neutral "software, not an instrument", and the GMP-traceable audit record. There
are no invented customers, prices, vendor logos, or capabilities. The confluency
comparison table is labelled as *disagreement between two methods on the same field*, not
as labelled error — the benchmark figures are stated separately. The synthetic-training-data
provenance is disclosed in its own section, matching the console's permanent footer
disclosure.

## Fonts

Archivo (variable, weight + width axes) and Martian Mono (variable), latin subset, embedded
as woff2 data URIs. Archivo's width axis carries the hierarchy — condensed for display,
expanded for reading. Both have real fallback stacks.
