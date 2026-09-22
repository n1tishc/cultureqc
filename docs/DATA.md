# Training data

Nothing under `data/` is tracked, and nothing under it is source. It is all
downloaded or derived, and it was 15 MB of committed PNGs (plus 1.8 GB of
downloads) sitting in a repo whose actual code is about 200 KB.

The files in `test-data/` are the exception and **are** tracked — they are
the fixtures the README quickstart, the demo, and the test suites run against.
Ten as of this writing: 4 real LIVECell-format phase-contrast fields, 4
synthetic challenge tiles, and 2 real EVICAN images (`evican_*.jpg`) added in
Slice 1 of `cultureQC_upgrade.md` — one low-error case, one high-error case
from the real-data validation, kept for the demo app's "Real images (EVICAN)"
example row. EVICAN is CC BY 4.0 (Parekh et al. 2020); see `docs/DATASETS.md`
for the full license/provenance verification. Attribution: Parekh, S. et al.,
"EVICAN — a balanced dataset for algorithm development in cell and nucleus
segmentation," *Bioinformatics* 36(12):3863–3870 (2020),
doi:10.17617/3.AJBV1S, CC BY 4.0.

## What lives where

| Path | What it is | Tracked |
|---|---|---|
| `data/sources/deepbacs/` | DeepBacs *E. coli* brightfield set, downloaded from [Zenodo 5550935](https://zenodo.org/records/5550935) | no |
| `data/sprites/bacteria/` | ~2 350 single-bacterium RGBA cutouts, derived from the above | no |
| `data/tiles/` | synthetic contamination / detachment / image-quality tiles | no |
| `data/sources/evican/` | EVICAN `eval2019` held-out split (images + COCO masks), downloaded for Slice 1's real-image confluency validation — see `docs/DATASETS.md` | no |
| `data/sources/livecell/` | LIVECell brightfield images (`livecell_train_val_images/`, flat, 3727 `.tif`), the `--base-dir` for `synth_contamination.py` — see `docs/DATASETS.md` | no |
| `data/sources/autoqc_bench/` | AutoQC-Bench `test/` + `splits/` (160 files, 51 MB), external anomaly-benchmark eval set for a later slice — see `docs/DATASETS.md` | no |
| `test-data/` | 4 real LIVECell-format phase-contrast fields + 4 synthetic challenge tiles + 2 real EVICAN images | **yes** |

## Regenerating it

```bash
python scripts/download_sources.py --out data/sources
python scripts/extract_sprites.py --input data/sources/deepbacs --out data/sprites/bacteria
```

`download_sources.py` only fetches DeepBacs (the sprite source) from Zenodo —
it does **not** fetch LIVECell. `synth_contamination.py --base-dir` is
`required=True` with no default, so regenerating `data/tiles/` needs LIVECell
pulled separately first (public, no auth, CC BY-NC 4.0 — see
`docs/DATASETS.md` for the exact URL and size) before the third command:

```bash
curl -O http://livecell-dataset.s3.eu-central-1.amazonaws.com/LIVECell_dataset_2021/images.zip
unzip images.zip -d data/sources/livecell/images && rm images.zip
python scripts/synth_contamination.py \
    --base-dir data/sources/livecell/images/livecell_train_val_images \
    --sprite-dir data/sprites/bacteria --out data/tiles
```

The Zenodo and LIVECell downloads are both public records and need no
credentials. Sprite extraction is deterministic given the same source images;
contamination synthesis takes `--seed` (default 42, matching the tiles shipped
in `test-data/`) — verified in Slice 1b by re-running it end-to-end and
comparing output to `test-data/` byte-for-byte, see `docs/DATASETS.md`.

## What needs it

Only the training and asset-generation path:

- `scripts/synth_contamination.py` — composites sprites onto clean tiles
- `site/assets/regen.py` — rebuilds the landing page's contaminated-field image

Neither the library (`culture/`), the API (`deploy/hf-space/`), nor the site
build (`site/assets/build_data.py`) touches `data/`. A fresh clone can install,
analyse an image, run the tests, and rebuild the page without downloading
anything from here.

## One caveat worth carrying

The sprites are composited at their source optical scale, which is larger
relative to the cells than a real objective would show. The QC classifier's
100 % contamination recall is measured against that distribution — see *Known
limits* in the root README before quoting the figure.
