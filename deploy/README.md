# Deploying cultureQC

## What runs where

| What | Where | Built from | Status |
|---|---|---|---|
| v0.4 site | https://cultureqc-cvoy.vercel.app (Vercel project `cultureqc-cvoy`) | `site/`, production branch `slice-1b-compute-cache` | Live; every push to that branch redeploys it |
| Review console | `LongGrainRice/cultureqc-console` (ZeroGPU) | `deploy/hf-space-demo/` (`console.py` → `demo/app.py`) | Live; published with `deploy/publish_demo_space.py` |
| v0.2 site | https://cultureqc.vercel.app (Vercel project `cultureqc`) | `main` | Left as it is |
| v0.2 API | `LongGrainRice/cultureqc-api` (CPU, Docker) | `deploy/hf-space/` | Frozen: serves the v0.2 site only; not republished |
| Raw model demo | `LongGrainRice/cultureqc-demo` (ZeroGPU) | `deploy/hf-space-demo/app.py` | Frozen: left as it is |

The v0.4 site has no analysis path of its own: it shows the pipeline's stored
output and links to the console for a live run. Nothing is published or pushed
without the owner's go-ahead, and `deploy/publish_space.py` (the v0.2 API) is
not run.

## Layout

| Path | What it is |
|---|---|
| `deploy/hf-space-demo/` | the console Space (`console.py`); also holds the raw demo's `app.py` |
| `deploy/hf-space-demo/zerogpu.py` | ZeroGPU wiring, active only when `SPACES_ZERO_GPU` is set |
| `deploy/hf-space/` | the frozen v0.2 API Space (`api.py`, FastAPI in Docker) |
| `*/culture/`, `*/config/`, `*/configs/` | **generated** copies in both Spaces; see sync, below |
| `deploy/sync_space.py` | copies the pipeline into both Spaces; `--check` reports drift |
| `deploy/publish_demo_space.py` | publishes the console Space |
| `deploy/run_console_mac.sh` | the console on the Mac (backup) |
| `vercel.json`, `site/vercel.json` | build `site/` with Vite and serve `site/dist` |

`culture/`, `config/` and `configs/` inside each Space are copies. Keeping a
second hand-edited copy of the analysis code is how a deployed pipeline quietly
stops being the one in the repo, so they are generated:

```bash
python deploy/sync_space.py            # refresh the copies in both Spaces
python deploy/sync_space.py --check    # report drift, exit 1 if any (CI runs this)
```

Run the sync after any change under `culture/`, `config/` or `configs/`. The
console's `demo/` and `cache/anomaly/banks.npz` are synced too, but git-ignored
(the banks are not in git at all; they come from `scripts/eval_anomaly.py`).
Both Space folders are tracked directly in this repo: don't `git init` inside
them, or the main checkout can no longer track them (this happened to
`deploy/hf-space-demo/` once and had to be undone).

## The review console — `LongGrainRice/cultureqc-console` on ZeroGPU

The console (`console.py` → `demo/app.py`) runs on its own Space, published
from `deploy/hf-space-demo/`. It is a separate Space so that nothing already
running changes: `cultureqc-demo` keeps the raw-output page and `cultureqc-api`
keeps serving the v0.2 site.

```bash
python deploy/sync_space.py                     # mirrors culture/, config/, configs/, demo/, banks, demo images
.venv/bin/python -m pytest deploy/hf-space/test_api.py tests/test_console_zerogpu.py -q
.venv/bin/python deploy/publish_demo_space.py   # refuses unless the banks match configs/anomaly.yaml
.venv/bin/python scripts/space_dry_run.py --out results/space_dry_run_<space commit>.md
```

The fine-tuned demo set (`demo/lab_demo.py`) is on by default in the Space. Its
weights are not in the Space or this repository: they are uploaded once to the
private model repo `LongGrainRice/cultureqc-finetuned` with
`scripts/upload_finetuned_weights.py` (it refuses unless the file is the
approved one and the repo is private), and the Space reads them at startup
with the secret `CULTUREQC_HF_TOKEN`, a read-only token for that repo. Without
them the startup log says `fine-tuned demo set OFF` and the console runs as
before; the Space variable `CULTUREQC_FINETUNED` set to empty turns it off.

**Why ZeroGPU rather than a dedicated GPU tier** (chosen 2026-09-28): it costs
nothing beyond the PRO plan, needs no switching on before the call or back to
CPU after it, and stays fast after the call if the link is opened again. The
costs: a GPU is attached per live Analyze (in the 2026-10-04 dry run,
`results/space_dry_run_e6c44671.md`, the first took 6.22 s and the rest a
median 3.22 s; in the 2026-09-28 run, commit `0210c79`, one of 7 took 18.50 s,
cause not measured), each Analyze draws on the viewer's ZeroGPU quota (a
signed-out Analyze also ran, checked once on EVICAN PC3), and the startup
self-check cannot run (no GPU at startup), so the dry run is
`scripts/space_dry_run.py` from outside instead. `zerogpu.py` is active only
when `SPACES_ZERO_GPU` is set, so switching the Space to a dedicated GPU tier
needs no code change (then the startup self-check, `CULTUREQC_SELFCHECK=5`,
works as before).

1. The Space log should show `ZeroGPU (a GPU per live Analyze …)`, `anomaly
   banks verified` and `models loaded in … s`.
2. Dry run: `scripts/space_dry_run.py` uploads each of the 7 precomputed
   examples' images, runs Analyze live on the Space signed in with the local
   token (the owner's quota), each with its imaging setup's calibration
   profile, times each one from the client and compares the record with the
   stored example. Then open both 3D views (Analyze → 3D, Flask Timeline → 3D)
   in the browser that will be used on the call: they need WebGL.
3. On the call, open the Space **signed in, from huggingface.co/spaces/…**,
   so Analyze uses the PRO quota. Precomputed examples and replays use no GPU.
   The Space sleeps after 48 h without visitors and a boot takes minutes
   (models loaded in 73.4 s after the build, Cellpose-SAM download included):
   open it 10 minutes before the call and check the log shows `models loaded`.
4. `@spaces.GPU(duration=60)` in `zerogpu.py`: tune from the dry run's times,
   not guesses.

### Backup: the Mac (no Hugging Face at run time)

If the Space is down on the day (it returned 5xx for hours on 2026-09-28,
across unrelated Spaces), run the same console on the Mac:

```bash
deploy/run_console_mac.sh              # http://127.0.0.1:7860; share the browser window
deploy/run_console_mac.sh --selfcheck  # dry run -> results/live_latency_mac_mps.md
```

It syncs and runs `hf-space-demo/console.py`, with Cellpose-SAM on Apple's
GPU (`CULTUREQC_DEVICE=mps`; DINOv2 and the classifier stay on CPU) and the
Hugging Face offline flags set, so the weights come from the local caches
(`~/.cellpose/models`, `~/.cache/huggingface`). It was checked with the
network blocked: all 7 examples re-run live with the same anomaly flag and
action as stored, and a live Analyze appends to the chain. Timings and
live-vs-stored values are in `results/live_latency_mac_mps.md`; quote them
from there. The run log is per boot, in a temp directory.

### Backup: Colab GPU

For a CUDA dry run or a second machine without the Space:

```bash
python scripts/make_console_bundle.py   # -> ../cultureqc_console_bundle.zip (~1.4 GB)
```

The zip holds the synced `hf-space-demo/` plus the three models' weights
(Cellpose-SAM, DINOv2-small, the QC checkpoint) and a manifest with every
file's SHA-256. Upload it to `MyDrive/cultureqc/` and run
`nb/05_console_colab.ipynb` on a T4 runtime:
- It copies the zip to Colab's local disk, checks the manifest, and installs
  the packages from PyPI.
- It runs `demo.selfcheck` over all 7 examples offline, which gives
  `live_latency_colab_gpu.md` (commit it under `results/`).
- It opens the console through Colab's own port proxy: a full-tab URL (printed)
  and the same console inline below the cell.

The bundle was checked on the Mac by unzipping it and running the self-check
with an empty `HOME` (no local model caches) and the network blocked. On Colab (Tesla T4,
2026-09-29) all 7 examples gave the same flag and action as stored, median
12.06 s per C2C12 frame (`results/live_latency_colab_gpu.md`), measured before
the calibration profiles. A public `gradio.live` link (`CULTUREQC_SHARE=1`)
goes through Gradio's share servers, which Hugging Face runs, so the Colab
proxy window is the one to rely on.

## The site — Vercel

Vercel builds every push to this repo. The v0.4 site is the project
`cultureqc-cvoy`, whose production branch is `slice-1b-compute-cache`, so it
gets a public URL (https://cultureqc-cvoy.vercel.app) while `main` stays
untouched; its domain is set in `site/index.html` (`canonical`, `og:url`,
`og:image`, which crawlers need absolute). `cultureqc` (production from
`main`, `cultureqc.vercel.app`) is the v0.2 site and is left as it is. A third
project, `site`, also builds each commit (its status shows on GitHub). Preview deployments sit behind Vercel's login; the
production domains are public.

```bash
npm install
npm run build     # -> site/dist
npm run preview   # serve that build locally before pushing
```

A project rooted at the repository uses `vercel.json` (`outputDirectory:
site/dist`); one rooted at `site/` uses `site/vercel.json` (`dist`); they set
the same build and headers. No other dashboard configuration and no
environment variables are needed. The footer names the commit from
`VERCEL_GIT_COMMIT_SHA`.

### Regenerating the page's data

`site/src/data.json` and `site/public/img/v3/` are generated from the repo's
own output (the console's examples and records, the calibration profiles, the
replays and their maps, `configs/detectability.yaml`, and the README's two
results tables, whose numbers `tests/test_readme_provenance.py` checks against
their sources):

```bash
python site/assets/build_data.py            # data.json (needs only numpy and pyyaml)
python site/assets/build_data.py --images   # and the layers, thumbnails, maps, og.jpg
```

Each record ships as the exact canonical JSON `culture/records.py` hashed; the
generator checks every SHA-256 on export, and the page re-hashes the same bytes
in the browser (`site/src/lib/verify.js`, tested by `site/tests/verify.test.js`).
CI re-runs the generator with only numpy and pyyaml installed and fails if
`data.json` differs.

## Frozen: the v0.2 API Space — `LongGrainRice/cultureqc-api`

`deploy/hf-space/` is the FastAPI backend the v0.2 site calls (`ORIGINS` in
`api.py` allows only `https://cultureqc.vercel.app`). It runs the old pipeline
on CPU, where Cellpose-SAM takes minutes per frame (V9), which is why the v0.4
site links to the console for a live run instead. The Space is not
republished; its folder is kept here because CI runs its contract tests and
`sync_space --check` against it. The v0.2 site's own local setup (a Vite proxy
to a local API) and its cross-origin check are documented with that site's
source, in `deploy/README.md` on `main`.

### The `/analyze` contract

- `/health` answers immediately and reports `models_loaded: false` until both
  models are resident. `/analyze` returns **503 + Retry-After** while warming
  rather than queueing.
- The record gets its public image filename before signing (rewriting
  `image_ref` after signing invalidated the returned hash in an earlier
  version). Responses include `record_canonical`, the exact signed JSON text,
  because JavaScript normalizes Python values such as `80.0` to `80`.
- With the optional form field `stream=true`, `POST /analyze` returns NDJSON
  events instead of one JSON body: `queued` (waiting for the shared model
  lock); `segmentation/running`, then `segmentation/complete`; `qc/running`,
  then `qc/complete` (with Grad-CAM evidence if available); `result` (the full
  response plus `visuals`); `error` (terminal, with no verdict); and
  `heartbeat` every ten seconds during long stages. Without the flag the plain
  JSON contract is unchanged. `culture/visuals.py` encodes the display images
  (`raw`, `probability`, `mask`, `contour`, `heatmap`); they change no number,
  threshold or record field.

```bash
curl https://longgrainrice-cultureqc-api.hf.space/health
curl -X POST https://longgrainrice-cultureqc-api.hf.space/analyze \
     -F "image=@test-data/contam_00015.png" -F "cell_line=Huh7" -F "target_confluency=80"
```

No weights are uploaded: `culture/qc.py` pulls its checkpoint from
`LongGrainRice/cultureqc-qc-effnetb0-v1` via `hf_hub_download`, and
Cellpose-SAM downloads itself on first construction.

### Tests

```bash
python -m pytest deploy/hf-space/test_api.py -q
```

28 contract tests: readiness semantics, input validation, response shape, the
evidence-box arithmetic, the CORS allowlist in both Space and local modes, that
the inference is off the event loop, and that twelve concurrent uploads leave
the hash chain intact. The models are stubbed; the concurrency test drives the
**real** `RecordWriter`, because the bug it guards is in the write path, and it
was confirmed to fail without the lock before the lock was added.

`deploy/smoke_space.py` runs real inference against the live Space (four
synthetic QC fixtures; classes, output ranges, evidence boxes and hashes). It
is a deployment regression check, not an accuracy measurement.

### Running it locally

```bash
docker build -t cultureqc-api deploy/hf-space
docker run --rm -p 7860:7860 cultureqc-api
```

On Apple Silicon that build is `arm64` and HF Spaces run `x86_64`; add
`--platform linux/amd64` for the exact target. `requirements.txt` there uses
lower bounds rather than exact pins on purpose: the versions this code runs
against locally are Python 3.14 wheels, and the image is 3.11, where several of
them do not exist.

Measured with the models already resident, on an M-series laptop:

| Where | 256×256 tile | 704×520 field | Cold boot |
|---|---|---|---|
| host venv (Python 3.14, torch 2.14) | ~50 s | > 180 s | ~9 s (weights cached) |
| this Docker image (Python 3.11) | **21.8 s** | not measured | **63 s** (weights downloaded) |

HF CPU Basic is 2 vCPU and may be slower still. The two environments also
disagree very slightly on output (86.65 % vs 86.68 % confluency on the same
tile) because they resolve different library versions: a probability-map
threshold moving under a different BLAS, not a change in method.

## Frozen: the raw model demo — `LongGrainRice/cultureqc-demo`

`deploy/hf-space-demo/app.py` is a Gradio page over the same
`culture.pipeline.analyze()` that shows the model's own output (field, mask,
Grad-CAM heatmap, confluency, QC verdict, signed record) with no product UI in
front of it, on ZeroGPU. It was published to `cultureqc-demo` before the
console existed and is left as it is. The folder's Space card now names
`console.py` as the app, so `publish_demo_space.py` publishes the console, not
this page.

Run it locally (`@spaces.GPU` is a no-op outside a real ZeroGPU Space):

```bash
cd deploy/hf-space-demo
../../.venv/bin/pip install -r requirements.txt   # adds gradio + spaces to .venv
../../.venv/bin/python app.py                      # http://127.0.0.1:7860
```

ZeroGPU quota is per visitor, not a budget a backend can draw against on every
request, which suits "a link sent to one person", not automated traffic.
