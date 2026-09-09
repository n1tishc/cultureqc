# Training data

Nothing under `data/` is tracked, and nothing under it is source. It is all
downloaded or derived, reproducible from two commands, and it was 15 MB of
committed PNGs (plus 1.8 GB of downloads) sitting in a repo whose actual code is
about 200 KB.

The eight files in `test-data/` are the exception and **are** tracked — they are
the fixtures the README quickstart, the demo, and the test suites run against.

## What lives where

| Path | What it is | Tracked |
|---|---|---|
| `data/sources/deepbacs/` | DeepBacs *E. coli* brightfield set, downloaded from [Zenodo 5550935](https://zenodo.org/records/5550935) | no |
| `data/sprites/bacteria/` | ~2 350 single-bacterium RGBA cutouts, derived from the above | no |
| `data/tiles/` | synthetic contamination / detachment / image-quality tiles | no |
| `test-data/` | 4 real phase-contrast fields + 4 challenge tiles | **yes** |

## Regenerating it

```bash
python scripts/download_sources.py --out data/sources
python scripts/extract_sprites.py --input data/sources/deepbacs --out data/sprites/bacteria
python scripts/synth_contamination.py --sprite-dir data/sprites/bacteria --out data/tiles
```

The download is a public Zenodo record and needs no credentials. Sprite
extraction is deterministic given the same source images; contamination
synthesis takes `--seed`, and the tiles shipped in `test-data/` came from an
earlier run of it.

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
