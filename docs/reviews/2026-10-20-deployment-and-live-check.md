# Deployment, visual and live-console check

Date: 2026-10-20, after `c006c7d` was pushed. The checks below were read-only
against every remote service except live Analyze runs on the console Space
(owner's token and ZeroGPU quota, as in the earlier dry runs). With the owner's
approval the fixes were then committed (`1ad36fa` console, `607c5fe` site),
pushed, and the console was published as Space commit `0fb0ffa0`; see
[After publishing](#after-publishing).

## What is deployed

| Surface | Observed | Matches the plan? |
|---|---|---|
| v4 site, Vercel `cultureqc-cvoy` | Production deployment for `c006c7d` succeeded; the served bundle and footer carry `c006c7d`. `/`, `/records`, `/validation`, `/release-notes` and `/records?record=evican_ht29` return 200; an unknown path returns 404. | Yes |
| CI | Run 39510630433 on `c006c7d`: success. Run 39510280196 on `0007bc2` failed four frozen replay comparisons (Python 3.11 vs the recorded 3.14.7), corrected by the runtime pin, not by changing a decision. | Yes |
| Console Space `LongGrainRice/cultureqc-console` | RUNNING on zero-a10g at `712a9e54` (2026-10-11). Against `deploy/hf-space-demo/`: 81 files identical, 20 differ (most of `culture/`, `demo/app.py`, `demo/analysis.py`, README, requirements), 5 local modules absent (`culture/anomaly_coverage.py`, `growth_signal.py`, `ingestion.py`, `provenance.py`, `demo/uploads.py`). `demo/flask_timeline.py` is still on the Space although removed in `c131a1d`; `upload_folder` does not delete it and nothing imports it. | No: the backend changes since 2026-10-11 are not deployed |
| Legacy API `cultureqc-api` | RUNNING, cpu-basic, `9116405`; `/health` returned `models_loaded: true`, `warm_seconds: 13.9`, schema 0.2. A `models_loaded: false` reading is the documented warm-up state. | Frozen v0.2 surface, as documented |
| Raw demo `cultureqc-demo` | RUNNING, `6e1cc1a` | Frozen, as documented |

Local: `pytest tests deploy/hf-space/test_api.py` 878 passed, 1 skipped (the
opt-in real-Cellpose CPU check); `node --test site/tests/*.test.js` 15 passed;
production build passes; `sync_space.py --check` passes.

## Site against the C0/I2 contract (production)

Headless Chromium at 1280×800, 390×844 and 320×700, reduced motion. Opened and
inspected: home first view (desktop, mobile), the full home page (desktop),
HT29 (desktop, mobile), Records and the chain landing (desktop, mobile),
Evidence (desktop, mobile), release notes (desktop) and the illustrative review
(desktop). The other captures were used only for the DOM measurements below.

- 1280×800 first view: hero, microscopy, 39.41 %, CONTINUE and its reason are
  visible together. After `#demo`, image, result, scope and the exact-record
  link fit one viewport. On 390 px the image precedes the result.
- Page order: proposition → one Stage → Measure/Understand/Trace → `#fit` →
  `#evidence` → `#trail` → `#pilot` → technical appendix. Exactly one Stage.
  The pilot section has no sample sizes, savings or deadlines.
- Default `c2c12_normal_20_40`: 39.41 %, continue, "No calibrated error band".
  HT29: 52.91 %, band 23.51–82.31 %, target 80 %, human review, with the
  mixed-setup and anomaly-bank qualifications beside it.
- All 7 IDs select by deep link with an unrelated query kept; an unknown ID
  shows the visible fallback notice; Back/Forward restore selection; Reset
  returns to the default and the Segmentation view.
- Records: 9 of 9 verify in the browser; changing one number fails record 9
  only; reset restores. The HT29 record is the selected one.
- Illustrative review (desktop and mobile): "Verified illustrative extension:
  10 records…", `final_action` human_review, fictional reviewer,
  `host_signature_ref` null; its link selects HT29 (#9) and "Return to this
  reading" restores `/?example=evican_ht29#demo` at 52.91 %.
- Evidence keeps each qualification beside its number (fine-tuning "not used
  for recommendations"; MSC 8.19 → 3.43 pp with "only 4 images at 60–90 %").
- No horizontal overflow at 1280, 390 or 320 px on any of the four pages; no
  console errors or failed requests.
- Observation, not changed: the v0.4 release note still reads "a reading whose
  band clears the target passages". That was v0.4's behaviour; under
  `rules_v0.7` every shipped profile is measurement-only for automatic
  passage. C0 keeps historical notes unchanged, so it is flagged for the owner.

**Defect: fragment links opened at the top of the page.** Every fresh page load
with a `#fragment` stayed at `scrollY 0`, apart from the appendix targets that
`Home.jsx` scrolls itself. That includes "Inspect this exact record"
(`/records?record=…#chain`; the chain started 559 px down at 1280×800 and
1094 px down at 390×844) and the hero's "See how it fits" (`/records#integration`,
3,504 px down). Cause: the page is drawn by React after the browser's own jump
to the fragment found nothing; `RecordsPage` and `ValidationPage` never handled
it. Pre-dates v4, but v4 puts both links on the demo path.

Fix (local): `site/src/main.jsx` renders a `FollowHash` component after the page
that scrolls to the fragment once drawn, unless the page or reader has already
scrolled. Against a local build all 22 measured links land under the sticky
header (72 px desktop, 120 px mobile); the full functional pass above was
repeated with the same results. On a phone the chain heading is at the top; the
selected card is a few cards further down.

## Updated console: two startup failures found before publishing

1. **Cellpose-SAM weights are never provisioned on a fresh Space.** The T06
   loader in `culture/seg.py` refuses unless the approved `cpsam_v2` file is
   already on disk; it no longer downloads it. Reproduced with an empty model
   directory: `NotApproved: weights file not found`. On ZeroGPU,
   `zerogpu.load_models()` runs at startup, so the refusal would end startup.
   Upstream `mouseland/cellpose-sam` revision `7c61431b…` serves `cpsam_v2`
   with the approved SHA-256 `0f1cc3f7…c667` (checked by metadata, no
   download).
   Fix (local): `console.py` downloads it with `huggingface_hub.hf_hub_download`
   pinned to that revision, into Cellpose's model folder, only if the file is
   missing, before anything loads it; it logs the approvals check, whether or
   not warm-up is on. Run against this Mac's existing file it logs
   `Cellpose-SAM weights present, match (0.7 s)`.
2. **The Mac and Colab backups crash in warm-up.** `analyze_image` now re-reads
   `image_path` and refuses a file that is not the supplied image; the warm-up
   passed `console.py`. `read_image("console.py")` raises "Could not decode
   image safely". ZeroGPU does not take this branch; `deploy/run_console_mac.sh`
   and the Colab notebook do. Fix (local): the warm-up frame is written to a
   temporary PNG first. `demo/selfcheck.py` is unaffected: all 7 example images
   read identically both ways.

`tests/test_console_zerogpu.py` now gives each run an empty Cellpose model
folder and stubs the download (no 1.2 GB fetch in CI). It asserts the download
precedes every model load, that a file already present is not fetched again,
and that warm-up reads a real image file. The ordering and warm-up assertions
fail on the unfixed `console.py`; all 7 tests pass with the fix.

Publish readiness, beyond those two fixes: the gitignored `demo/` mirror matches
the root `demo/` apart from local runtime files (`events_web.jsonl`,
`uploads/`), but `sync_space.py --check` does not cover `demo/`, so run the full
`sync_space.py` before publishing. `scripts/space_dry_run.py` still parses the
new output: `audit-json` is rendered, and every field it reads is in the schema
0.8 reading record.

## What the updated console should produce

From the stored measurements under `rules_v0.7`, with console timing unknown
(no inference): all 7 examples keep their stored action (continue ×5, reimage,
human_review). A post-publish dry run that differs in action is a regression.
HT29's live reason changes: "Passage timing is unknown; the minimum interval
cannot be verified" rather than the band explanation, because v0.7 checks the
unknown passage timing first. The stored site example keeps its band reason.

Input handling also changes: RGB uploads are read as grayscale, while 16-bit
TIFFs and transparent PNGs are refused with a message (T09).

## Live fresh-image check (deployed build `712a9e54`)

One C2C12 frame not among the stored examples (`data/c2c12_picks/00ee04b2…png`,
1040×1392 uint8), C2C12 setup, target 80 %: upload 4.5 s, Analyze 8.2 s,
33.24 %, continue, quality gate passed, anomaly not flagged, `model_check`
match, chain intact (record #27), schema 0.5 / `rules_v0.5`. The record's
`image_hash` is not the SHA-256 of the uploaded file, consistent with the old
upload path re-saving the image before analysis; the new ingestion path is
meant to remove that.

## After publishing

`607c5fe` pushed: CI green on all five checks; the live site serves `607c5fe`
and all 22 measured fragment links land under the header in production.

The owner ran `deploy/publish_demo_space.py` (the automated session was not
permitted to): Space commit `0fb0ffa0`, RUNNING on zero-a10g.

- Startup log: `Cellpose-SAM weights downloaded, match (3.3 s)`; fine-tuned
  demo set on, weights match, 4 of 4 demo images; `anomaly banks verified`;
  `models loaded in 11.7 s`.
- Files: 106 identical to `deploy/hf-space-demo/`, none different, none
  missing; on the Space only, `.gitattributes` and the stale
  `demo/flask_timeline.py`.
- Dry run, `results/space_dry_run_0fb0ffa0.md`: anomaly flag and action as
  stored on 7 of 7 examples, readings within 0.04 pp; first Analyze 4.89 s,
  median of the rest 3.47 s. Fine-tuned demo set: shipped 43.49 / 56.08 /
  84.33 / 83.31 %, fine-tuned 78.69 / 75.43 / 89.87 / 83.37 %, weights check
  `match`; the changed copy carried no fine-tuned reading.
- The same fresh C2C12 frame as above: 33.24 %, continue, schema 0.8,
  `rules_v0.7`, `model_check` match, 6.0 s. The record's `image_hash` now
  equals the uploaded file's SHA-256.
- HT29 live: 52.91 %, band 23.51–82.31 %, human_review, reason "Passage timing
  is unknown; the minimum interval cannot be verified…", as predicted. Demo
  images 3 and 4 give the same reason.
- Refusals through the upload endpoint: 16-bit TIFF and transparent PNG get
  "Only uint8 grayscale or RGB images are supported…", a non-image gets "Could
  not decode image safely…"; an RGB JPEG is accepted. The four fine-tuned demo
  TIFFs are 8-bit RGB and are accepted.

`docs/DEMO_SCRIPT.md` now cites this dry run, the new log line, the 8-bit input
requirement and the live reason text. README, site data and the Space card
still cite the `712a9e54` dry runs by name, which remain accurate as history.

`712a9e54` remains the rollback: `snapshot_download(repo_type="space",
revision="712a9e54…")` fetches its 103 files (104 MB), which can be uploaded
back with `delete_patterns="*"`.

In the Space page (headless Chromium, not signed in, no Analyze pressed), a
16-bit TIFF upload shows the refusal in the results pane, the upload area
resets and Analyze stays enabled with no loading overlay; a following 8-bit
upload clears the message and previews normally. The refusal wording is
technical ("uint8"); left as is.

## Still open

- Human screen-reader and actual 200 % zoom checks and the V3 timed rehearsal
  remain pending; automated reflow evidence does not close them.
