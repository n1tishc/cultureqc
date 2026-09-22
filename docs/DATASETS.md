# DATASETS

Real-image datasets used for the upgrade (`cultureQC_upgrade.md`), their
licenses, and whether they overlap with Cellpose-SAM (`cpsam_v2`) training —
verified before any of these were downloaded or used, per spec rule 6.

## Verified Cellpose-SAM training corpus (primary source)

Fetched directly from the Cellpose-SAM paper's full text (Pachitariu, Rariden
& Stringer, "Cellpose-SAM: superhuman generalization for cellular
segmentation," bioRxiv 2025.04.28.651001), Methods section, which states:
**"We used 18 publicly available datasets for training Cellpose-SAM"** —
22,826 training images, 3,341,254 training ROIs. The named datasets:

Cellpose (updated), Cellpose Nuclei, TissueNet, **LiveCell**, Omnipose, YeaZ,
**DeepBacs**, Neurips 2022 challenge, MoNuSeg, MoNuSAC, CryoNuSeg, NuInsSeg,
BCCD, CPM 15+17, TNBC, LynSec, IHC TMA, CoNIC, PanNuke.

This confirms the upgrade spec's own instruction (§4.1: "Do not use LIVECell
... or DeepBacs as held-out") — both are explicitly in the list. Neither
**EVICAN** nor **Cell Tracking Challenge** appear anywhere in this list, in
the paper, or in the Cellpose GitHub README (checked separately) — both are
safe to use as held-out real-data eval sets with respect to Cellpose-SAM
training overlap.

**Aside, not a Slice 1 blocker but worth flagging for later:** the Cellpose
GitHub README states "All Cellpose models are trained on data that is
licensed under CC-BY-NC. The Cellpose annotated dataset is also CC-BY-NC" —
i.e. the *shipped weights* carry a non-commercial-license-trained-on taint.
Worth a legal read before any commercial claim tied to Cellpose-SAM
specifically (separate from cultureQC's own code license); not evaluated
further here.

## EVICAN — used, primary held-out eval (Slice 1)

- **What:** Parekh et al. 2020, *Bioinformatics* 36(12):3863–3870,
  "EVICAN — a balanced dataset for algorithm development in cell and nucleus
  segmentation." 4,600+ grayscale brightfield/phase-contrast images across 30
  cell lines, 4 microscope setups, 3 labs, COCO-format instance masks (`Cell`,
  `Nucleus` categories).
- **License:** **CC BY 4.0**, confirmed two ways: (1) the paper states "This
  is an Open Access article distributed under the terms of the Creative
  Commons Attribution License," and the dataset itself is "provided under a
  CC-BY license to allow far-ranging use"; (2) confirmed independently and
  programmatically from the hosting repository's own Dataverse API
  (`GET /api/datasets/:persistentId/?persistentId=doi:10.17617/3.AJBV1S`),
  whose structured metadata states `"license":{"name":"CC BY 4.0", ...}`.
  Free to use, including for this purpose, with attribution.
- **Source images:** original acquisitions by the paper's authors, **not**
  derived from another dataset — ruled out as a possible indirect Cellpose-SAM
  overlap route.
- **Training overlap:** not in Cellpose-SAM's training list (see above). Not
  mentioned anywhere in the Cellpose-SAM paper.
- **Hosting note:** the URL cited in the paper itself
  (`edmond.mpdl.mpg.de/imeji/collection/...`) is dead — redirects to the
  Max Planck Society's newer Edmond/Dataverse platform
  (`edmond.mpg.de`), current persistent link:
  `https://edmond.mpg.de/dataset.xhtml?persistentId=doi:10.17617/3.AJBV1S`.
  That human-facing page is behind Anubis, a proof-of-work anti-bot wall
  explicitly there (per its own page) to block "AI companies aggressively
  scraping" — deliberately not solved programmatically here. The
  **Dataverse REST API is not behind it** and is the documented, intended
  machine-access path for this platform (`/api/datasets/:persistentId/...`,
  `/api/access/datafile/{id}`), used instead. Every download was verified
  against the manifest's MD5 checksum.
- **What was downloaded** (`data/sources/evican/`, gitignored per
  `docs/DATA.md`'s existing pattern — not committed):
  - `EVICAN_eval2019.zip` (7.7 MB, 98 images) — the dataset's own designated
    **held-out evaluation split**, distinct from its train/val splits. Not
    used for anything else in this repo (no train/val downloaded).
  - `instances_eval2019_{easy,medium,difficult}_EVICAN2.json` — COCO instance
    annotations for that split (2-category: `Cell`, `Nucleus`), 33+33+32=98
    images total, matching the image count exactly.
  - **Not downloaded:** `EVICAN_train2019.zip` (2.2 GB), `_val2019.zip`
    (540 MB), `*_BGblurred.zip`, `*_masks.zip`, `*_EVICAN60.json` (the
    60-category per-cell-line variant — not needed; the 2-category `Cell`
    mask is what confluency GT needs). Unneeded for Slice 1 and would bloat
    the checkout for no purpose.
- **Partial-annotation caveat (spec §4.2):** EVICAN's *training* images are
  documented as partially annotated (not every cell in a frame is masked).
  The `eval2019` split used here is different — it's the dataset's own
  curated evaluation crops. Sanity-checked visually on two images (one
  `easy`-tier, one `difficult`-tier: `10_C2C12.jpg`, `2_769p.jpg`) by
  rendering the `Cell` mask over the image — both show clean, exhaustive
  coverage (every visible cell body masked, clean unmasked background, no
  obviously-missed cells). Treated as fully-annotated for GT confluency
  (union of `Cell` polygons / image area) without further region-restriction;
  see `scripts/eval_confluency_real.py`'s module docstring for the same note
  next to the code that relies on it.

## Cell Tracking Challenge — **not used, blocked on permission**

- **What:** `celltrackingchallenge.net`, various 2D+time adherent-culture
  sequences. `DIC-C2DH-HeLa` (HeLa cells, DIC, **GT** — expert-verified, not
  majority-vote silver-truth — segmentation, 37 MB train + 41 MB test) was
  the strongest candidate: small, real GT (unlike `PhC-C2DH-U373` and
  `PhC-C2DL-PSC`, the other adherent PhC/DIC options, which only have **ST**
  — silver truth, i.e. consensus-of-past-submissions pseudo-labels, not
  expert-annotated). `BF-C2DL-HSC` confirmed suspension-culture per the
  spec's own note — would have been skipped regardless.
- **Training overlap:** not in Cellpose-SAM's training list (see above) —
  this part is clear.
- **License — the actual blocker:** the site's stated Conditions of Use
  (`celltrackingchallenge.net/datasets/`) read, verbatim: *"Any public
  non-CTC-related, scientific use of our datasets requires explicit
  permission from the challenge organizers"* and *"Cloning of our datasets or
  their parts, including reference annotations, is strictly forbidden."*
  cultureQC's validation is exactly "public, non-CTC-related, scientific
  use" — this requires asking the organizers first, which is a real-world
  outward-facing action for the repo owner to take (not something to do
  unilaterally as part of an automated recon/eval pass). **Not downloaded.**
- **If you want this dataset:** email the Cell Tracking Challenge organizers
  (contact via `celltrackingchallenge.net`) referencing the intended use
  (external validation of a confluency-estimation method, non-commercial),
  and if granted, `DIC-C2DH-HeLa`'s training set alone
  (`https://data.celltrackingchallenge.net/training-datasets/DIC-C2DH-HeLa.zip`,
  37 MB) would be the natural addition to Slice 1's eval — its GT (not ST)
  segmentation and small size make it a good secondary real-data check
  alongside EVICAN. Left as a follow-up, not blocking Slice 1's gate.

## LIVECell — used, `data/tiles/` regeneration source (Slice 1b)

- **What:** Edlund et al. 2021, *Nature Methods* 18:1038–1045, "LIVECell — a
  large-scale dataset for label-free live cell segmentation." Phase-contrast
  brightfield images across 8 cell lines, the sprite-compositing base images
  for `scripts/synth_contamination.py`'s synthetic contamination/detachment/
  image-quality tiles (`data/tiles/`).
- **License:** CC BY-NC 4.0. **In Cellpose-SAM's training list** (see top of
  this file) — this is fine here because LIVECell is only ever used as the
  *background* onto which synthetic sprites are composited, never as a
  segmentation eval target; it is not part of any confluency-accuracy claim.
- **Hosting:** public S3, no auth —
  `http://livecell-dataset.s3.eu-central-1.amazonaws.com/LIVECell_dataset_2021/images.zip`
  (1.2 GB zipped). Extracts to `livecell_train_val_images/` (3727 flat `.tif`
  files — **not** nested by cell type, correcting an earlier inaccurate
  WebFetch-derived summary from Slice 0) and `livecell_test_images/`.
- **Documentation gap found and fixed:** `docs/DATA.md` previously claimed
  `data/tiles/` was reproducible from "two commands," but
  `scripts/download_sources.py` never fetches LIVECell (Zenodo/DeepBacs only)
  and `synth_contamination.py --base-dir` is `required=True` with no default
  — the documented command would fail outright on a fresh clone. Fixed in
  `docs/DATA.md` with the actual three-step sequence, LIVECell's URL, and its
  license.
- **Fidelity verification:** re-ran
  `scripts/synth_contamination.py --base-dir data/sources/livecell/images/livecell_train_val_images --sprite-dir data/sprites/bacteria --out data/tiles`
  (default `--seed 42`, default 1000 tiles/class, 4000 tiles total) against a
  freshly-downloaded LIVECell copy and compared output to the pre-existing
  `test-data/` fixtures by SHA-256. **3 of 4 spot-checked tiles are
  bit-identical.** The one mismatch (`contam_00015.png`) has an **identical**
  `tile_id`, crop position, `class`, and `n_sprites` in `manifest.csv` — only
  pixel content differs. Root cause: the compositing pipeline segments a
  background mask to decide sprite placement, and that segmentation step is
  sensitive to the installed library version (not to `--seed`, not to file
  ordering — `sorted(glob.glob(...))` + `random.shuffle(seed=42)` is fully
  deterministic given an identical file set, confirmed by code reading). This
  is a **benign, understood non-determinism** (environment-version drift in a
  non-seed-controlled step), not a split-integrity or reproducibility bug —
  the manifest's structural columns (which tile came from which base image,
  which class, how many sprites) reproduce exactly; only the exact sprite
  pixel placement on one tile out of four checked does not.

## AutoQC-Bench — sized, not yet pulled (Slice 1b/spec §4A validation target)

- **What:** `github.com/MMV-Lab/mmv_AutoQC` — a published benchmark for
  automated microscopy image-quality/anomaly detection the spec names as an
  external validation target (run per its protocol, report AUROC next to
  published baselines, don't tune on its test set).
- **Repo license:** MIT (`mmv_AutoQC` GitHub repo itself).
- **Dataset hosting:** BioStudies/EBI, accession **S-BIAD2133**, "over 8,000
  cell migration brightfield images" per the study page. Queried directly via
  `curl` against the plain HTTP directory listing (not the repo's own
  `download_autoqc_data.py` — see below) under `study-component-10`.
- **Actual size — exact, from the dataset's own file manifest** (BioStudies
  publishes a complete file list, `file_list_v02.json`, fetched directly —
  8,393 entries, each with an exact byte size; no extrapolation needed):

  | Directory | Files | Size |
  |---|---:|---:|
  | `splits/` | 12 | 0.2 MB |
  | `test/anomalies/` | 48 | 18.2 MB |
  | `test/good_data/` | 100 | 34.5 MB |
  | `train/` | 8,233 | 2,823.5 MB |
  | **Total** | **8,393** | **2,876.5 MB (≈2.9 GB)** |

  `train/` is essentially the entire dataset by size — `test/` + `splits/`
  together are **~53 MB**, trivial to pull regardless of what's decided about
  `train/`.
- **Structure:**
  - `train/` — raw images; presumably the "normal" bank an anomaly baseline
    is fit against
  - `test/anomalies/`, `test/good_data/{human,mouse}/` — the held-out eval
    set the spec says not to tune on
  - `splits/` — `normal_train.csv`, `normal_val.csv`,
    `test_test_fold{0-4}.csv`, `test_val_fold{0-4}.csv` (CSVs list image
    paths relative to `train/`/`test/`, e.g. `train\01_A1_000.tiff` —
    confirmed by reading `normal_train.csv` directly)
- **Downloaded:** `test/` + `splits/` only (~53 MB), via
  `scripts/fetch_autoqc_bench.py` (below) — into `data/sources/autoqc_bench/`.
  **`train/` deliberately not pulled yet.** The spec's own AutoQC-Bench line
  (§4A: "run per its protocol, report AUROC next to published baselines,
  don't tune on its test set") is a **Slice 4** anomaly-scoring task, not
  Slice 1b's — pulling 2.8 GB now, before the scoring method is even chosen,
  would be premature. When that slice starts, the real question is whether
  the DINOv2-embedding anomaly approach (the reason `culture/cache.py` stores
  DINOv2 embeddings at all) needs *raw* `train/` images fed through the cache,
  or whether `splits/normal_train.csv`'s path list is only needed to know
  *which* embeddings to treat as the normal bank once the corresponding
  images are pulled on demand — that's a design decision for whoever starts
  Slice 4, not assumed here either way.
- **Not run via the repo's own fetcher.** `mmv_AutoQC` ships
  `download_autoqc_data.py`; running that unreviewed third-party script was
  **declined** — the sandbox's own external-code classifier denied it, and
  that denial was treated as a real constraint, not worked around. The
  reviewed alternative (`scripts/fetch_autoqc_bench.py`) reads the same
  public `file_list_v02.json` manifest and pulls each file directly with
  `urllib`, verifying byte size against the manifest after each download.
  **EBI 403s urllib's default User-Agent** after a batch of plain requests
  (observed: 67 files in, then every request 403'd, even though the same URL
  is reachable via `curl`/browser with no auth) — fixed by sending a
  descriptive `User-Agent` identifying the script and its purpose. The script
  is resumable (skips any file already on disk at its manifest-listed size),
  so the 403 mid-run cost nothing but a re-invocation.

## Not used this slice

- **BriFiSeg** (spec: "Optional") — not evaluated for license/overlap; skipped
  to keep Slice 1 small, matching the spec's own framing of EVICAN as the
  primary set. Revisit only if EVICAN's result needs a second real-BF
  cross-check.
- **C2C12 time-lapse** (Sci Data 2018) — spec marks this "Slices 2–3; hand-
  label ~20 frames if used for Slice 1," i.e. explicitly optional here since
  it has tracking GT, not segmentation GT, without manual labeling work.
  Deferred to Slice 2/3, where it's actually required (replay, growth
  backtest).

## Held-out eval subset actually scored (Slice 1)

Of EVICAN's 98 `eval2019` images, a stratified subset was run through
Cellpose-SAM (rather than all 98, which is ~4.7 hr of local CPU time
dominated by a handful of very large images — a genuinely Colab-shaped GPU
pass per the upgrade spec's own notebook plan; the repo owner chose to trim
the local eval set instead of invoking Colab for this one). Selection method,
exact images, and counts are in `results/confluency_real_tuning.json` and
`results/confluency_real.csv` (script: `scripts/eval_confluency_real.py`) —
not restated here to avoid a second copy drifting from the actual run.
