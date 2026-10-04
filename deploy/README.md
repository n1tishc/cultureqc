# Deploying cultureQC

## Current working deployment

The product frontend is hosted at https://cultureqc.vercel.app, confirmed live
again as of September 11, 2026 (the `DEPLOYMENT_NOT_FOUND` noted here on
September 9 has resolved). It talks cross-origin to the Space, which is the
model and the `/analyze` API — nothing else. The Space briefly also served the
built frontend as a same-origin fallback while Vercel was down; that fallback
has been removed now that Vercel is back, so a visitor opening the Space URL
directly sees API metadata (or the Gradio demo below), not the product site.

Publish from the repository with your existing Hugging Face login:

```bash
python deploy/sync_space.py
.venv/bin/python -m pytest deploy/hf-space/test_api.py -q
.venv/bin/python deploy/publish_space.py
# Wait for /health to report models_loaded: true, then run real inference:
.venv/bin/python deploy/smoke_space.py
```

The publisher stages only Space source files — no frontend build. Model
weights continue to load from their existing repositories. The smoke test runs
four synthetic QC fixtures and verifies classes, output ranges, evidence boxes,
input hashes, and returned record hashes. It is a deployment regression check,
not a measurement of real-world detection accuracy. CPU inference takes minutes
for larger fields; a healthy endpoint alone does not prove inference works.

API records now receive their public image filename before signing. Rewriting
`image_ref` after signing invalidated the returned hash in the previous version.
Responses also include `record_canonical`, the exact signed JSON text, because
JavaScript normalizes Python values such as `80.0` to `80`. The upload UI checks
the image digest and, when supplied, the canonical record before accepting it.

```
Browser ──► Vercel (React + Vite)    ──►  HuggingFace Space (Docker + FastAPI)
            site/ ──► site/dist           deploy/hf-space/
            npm run build                 loads the models once, serves /analyze
```

Two independent deployments joined by one URL. Neither can break the other's
build, and the page keeps working — hashing files and building a verifiable
manifest — even when the API is asleep or gone.

## Layout

| Path | What it is |
|---|---|
| `deploy/hf-space/` | the product's backend Space, pushable as-is |
| `deploy/hf-space/api.py` | the FastAPI app; the only entrypoint |
| `deploy/hf-space-demo/` | a separate Gradio + ZeroGPU demo Space |
| `deploy/hf-space-demo/app.py` | the Gradio Blocks app; the only entrypoint |
| `*/culture/`, `*/config/` | **generated** in both Spaces — see sync, below |
| `deploy/sync_space.py` | copies the pipeline into both Spaces |
| `vercel.json` | builds `site/` with Vite and serves `site/dist` |

`culture/` and `config/` inside each Space are copies. Keeping a second
hand-edited copy of the analysis code is how a deployed pipeline quietly stops
being the one in the repo, so they are generated:

```bash
python deploy/sync_space.py            # refresh the copies in both Spaces
python deploy/sync_space.py --check    # report drift, exit 1 if any
```

Run the sync after any change under `culture/` or `config/`, before pushing
either Space.

## Backend — HuggingFace Space

Create a Space: **SDK Docker**, hardware **CPU Basic**, visibility **Public**
(the frontend calls it without credentials). Then push it — `deploy/hf-space/`
is tracked directly in this repo (no nested `.git`), so publishing goes through
the Hub API rather than a git remote:

```bash
python deploy/sync_space.py
.venv/bin/python deploy/publish_space.py
```

`publish_space.py` uploads `deploy/hf-space/` via `HfApi().upload_folder`,
ignoring `.git`/`__pycache__`. Don't `git init` inside `deploy/hf-space/` —
that would create a nested repo the main checkout can no longer track (this
happened to `deploy/hf-space-demo/` and had to be undone).

The image builds locally, which is worth doing before pushing — a failed Space
build is a slow way to find a dependency problem:

```bash
docker build -t cultureqc-api deploy/hf-space
docker run --rm -p 7860:7860 cultureqc-api
```

One caveat: on Apple Silicon that build is `arm64` and HF Spaces run `x86_64`.
Dependency resolution is the shared risk and a local build settles it; if you
want the exact target, add `--platform linux/amd64`.

`requirements.txt` there uses lower bounds rather than exact pins on purpose:
the versions this code runs against locally are Python 3.14 wheels, and the
image is 3.11, where several of them do not exist.

Build takes roughly 3–5 minutes. Verify:

```bash
curl https://longgrainrice-cultureqc-api.hf.space/health
curl -X POST https://longgrainrice-cultureqc-api.hf.space/analyze \
     -F "image=@test-data/contam_00015.png" -F "cell_line=Huh7" -F "target_confluency=80"
```

`/health` answers immediately and reports `models_loaded: false` until both
models are resident. `/analyze` returns **503 + Retry-After** while warming
rather than queueing, which is what the page's warming state reads.

No weights need uploading. `culture/qc.py` already pulls its checkpoint from
`LongGrainRice/cultureqc-qc-effnetb0-v1` via `hf_hub_download`, and Cellpose-SAM
downloads itself on first construction.

## Demo — Gradio + ZeroGPU

`deploy/hf-space-demo/` is a second, separate Space: a Gradio UI over the same
`culture.pipeline.analyze()`, for sending a link to one person so they can see
the raw model output — the field, the mask, the Grad-CAM heatmap, the
confluency estimate, the QC verdict, the full signed record — without the
product's UI in front of it. It does not carry the product's `/analyze`
contract and the product does not call it; see `deploy/hf-space-demo/README.md`
for why it is a separate Space rather than the same one repurposed.

Create a Space: **SDK Gradio**, hardware **ZeroGPU** (a repo setting you choose
on the Space's own Settings page after creating it — ZeroGPU needs a signed-in
HF account and, per Hugging Face, works best on a Pro account; plain CPU Basic
also runs it, just without the GPU burst). Then push it the same way as the
API Space — `deploy/hf-space-demo/` is tracked directly in this repo too, so:

```bash
python deploy/sync_space.py
.venv/bin/python deploy/publish_demo_space.py
```

Test locally first — `@spaces.GPU` is a documented no-op outside a real
ZeroGPU Space, so this exercises every code path except the actual GPU
attachment:

```bash
cd deploy/hf-space-demo
../../.venv/bin/pip install -r requirements.txt   # adds gradio + spaces to .venv
../../.venv/bin/python app.py                      # http://127.0.0.1:7860
```

Two things worth knowing before relying on this for speed:

- **ZeroGPU quota is per visitor**, not a budget a backend can draw against on
  every request — which is the reason this is not how the product's own
  `/analyze` gets faster. It suits "a link I send to someone," not automated
  traffic.
- **The `@spaces.GPU(duration=...)` on `_run_analysis` in `app.py` is a
  starting guess (60s)**, not a measured number — this repo has no real
  ZeroGPU timing yet. `hf-space/README.md`'s CPU figures (21.8s for a 256×256
  tile in the Docker image) are the closest reference. Watch the first few
  real runs and adjust; too generous a duration fails a low-quota visitor with
  `quota exceeded` before the call even starts, too small risks the run being
  cut off.

## Call-day console — `LongGrainRice/cultureqc-console` on ZeroGPU

For the dry run (Thu Oct 1), the rehearsal (Mon Oct 5) and the call (Tue Oct 6)
the review console (`console.py` → `demo/app.py`) runs on its own Space,
`LongGrainRice/cultureqc-console`, published from `deploy/hf-space-demo/`. It
is a separate Space so that nothing already running changes:
`LongGrainRice/cultureqc-demo` keeps the raw-output page on ZeroGPU and
`LongGrainRice/cultureqc-api` keeps serving the frontend. Nothing is pushed
without the owner's go-ahead.

```bash
python deploy/sync_space.py                     # mirrors culture/, config/, configs/, demo/, banks
.venv/bin/python -m pytest deploy/hf-space/test_api.py tests/test_console_zerogpu.py -q
.venv/bin/python deploy/publish_demo_space.py   # refuses unless the banks match configs/anomaly.yaml
.venv/bin/python scripts/space_dry_run.py       # live Analyze on the Space, timed and compared
```

**Why ZeroGPU rather than a dedicated GPU tier** (chosen 2026-09-28): it costs
nothing beyond the PRO plan, needs no switching on before the call or back to
CPU after it, and stays fast after the call if the link is opened again. The
same models already run on ZeroGPU in `cultureqc-demo`. The costs: a GPU is
attached per live Analyze (in the 2026-10-04 dry run, `results/space_dry_run_e6c44671.md`,
the first took 6.22 s and the rest a median 3.22 s; in the 2026-09-28 run, commit `0210c79`, one of 7
took 18.50 s, cause not measured), each Analyze draws on the viewer's ZeroGPU
quota (a signed-out Analyze also ran, checked once on EVICAN PC3), and the startup self-check cannot
run (no GPU at startup), so the dry run is `scripts/space_dry_run.py` from
outside instead. `zerogpu.py` is active only when `SPACES_ZERO_GPU` is set, so
switching the Space to a dedicated GPU tier instead needs no code change (then
the startup self-check, `CULTUREQC_SELFCHECK=5`, works as before).

1. The Space log should show `ZeroGPU (a GPU per live Analyze …)`, `anomaly
   banks verified` and `models loaded in … s`.
2. Dry run: `scripts/space_dry_run.py` uploads each of the 7 precomputed
   examples' images, runs Analyze live on the Space signed in with the local
   token (the owner's quota), times each one from the client and compares
   the record with the stored example; it writes
   `results/live_latency_zerogpu.md`. Then open both 3D views (Analyze → 3D,
   Flask Timeline → 3D) in the browser that will be used on the call: they
   need WebGL.
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
12.06 s per C2C12 frame (`results/live_latency_colab_gpu.md`). A public `gradio.live` link
(`CULTUREQC_SHARE=1`) goes through Gradio's share servers, which Hugging Face
runs, so the Colab proxy window is the one to rely on.

`demo/` and `cache/anomaly/banks.npz` inside `hf-space-demo/` are written by
the sync and git-ignored (the banks are not in git at all; they come from
`scripts/eval_anomaly.py`). The Hub stores the 67 MB banks file through LFS.

## Frontend — Vercel

Two Vercel projects build this repo. `cultureqc` (production from `main`,
`cultureqc.vercel.app`) is the v0.2 site and is left as it is. The v0.3 site
is its own project whose production branch is `slice-1b-compute-cache`, so it
gets a public URL (https://cultureqc-cvoy.vercel.app) while `main` stays
untouched; its domain is set in
`site/index.html` (`canonical`, `og:url`, `og:image`, which crawlers need
absolute). Preview deployments sit behind Vercel's login; the production
domain is public.

The v0.3 site has no analysis path of its own. The v0.2 API Space
(`cultureqc-api`) runs the old pipeline on CPU, where Cellpose-SAM takes
minutes per frame (V9), so the page shows the pipeline's stored output and
links to the console Space for a live run.

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
own output (the console's examples and records, the replays and their maps,
`configs/detectability.yaml`, and the README's two results tables, whose
numbers `tests/test_readme_provenance.py` checks against their sources):

```bash
python site/assets/build_data.py            # data.json
python site/assets/build_data.py --images   # and the layers, thumbnails, maps, og.jpg
```

Each record ships as the exact canonical JSON `culture/records.py` hashed; the
generator checks every SHA-256 on export, and the page re-hashes the same bytes
in the browser (`site/src/lib/verify.js`, tested by `site/tests/verify.test.js`).
CI re-runs the generator and fails if `data.json` differs.

## Local development

Two processes. The API on 7860, and the Vite dev server proxying `/health` and
`/analyze` to it — so the browser makes same-origin calls and there is no CORS
difference between development and the deployed page:

```bash
python deploy/hf-space/api.py           # http://127.0.0.1:7860
cd site && npm run dev                  # http://localhost:5173
```

The page prefers a local endpoint over the hosted one whenever it is opened from
localhost or a private LAN address, so local work never silently tests the
deployed service.

`api.py` also serves the *built* page at `/` when it can find `site/dist`, which
is how the same-origin path gets exercised against a production-shaped bundle:

```bash
cd site && npm run build
python deploy/hf-space/api.py           # now / serves the build too
```

That route stays JSON in the Space, which has no `site/` at all.

## The one path worth re-checking after you deploy

Everything else can be tested locally. The shipping path — a page on the Vercel
origin talking cross-origin to a strict-CORS Space — is covered here by running
the container with `SPACE_ID` set and pointing the page at it from
`https://cultureqc.vercel.app`, which is the real topology. If you change
`ORIGINS` in `api.py` or the Vercel domain, that pairing is where a mistake
shows up, and it shows up silently: the page falls back to "Analysis
unavailable" and keeps hashing, which looks like a sleeping Space rather than a
misconfiguration.

After the first deploy, open the browser console on the live page. A CORS
rejection names the origin it refused; add that exact string to `ORIGINS`.

One limitation of the local version of that test, so nobody is misled by it: the
page's own `fetch` is routed to the container through Playwright, and that proxy
does not forward a multipart body — the service receives an empty one and
correctly answers 400. So the cross-origin **GET** is exercised through the real
page, while the cross-origin **multipart POST** is sent straight at the container
with the production `Origin` header. The in-page multipart path is covered
same-origin instead. Together they cover what a deployed page does, but the
single combined path is genuinely only proven once the Space is live.

## Tests

```bash
python -m pytest deploy/hf-space/test_api.py -q
```

28 contract tests: readiness semantics, input validation, response shape, the
evidence-box arithmetic, the CORS allowlist in both Space and local modes, that
the inference is off the event loop, and that twelve concurrent uploads leave
the hash chain intact.

The models are stubbed — a real Cellpose-SAM call is tens of seconds, so a suite
that ran them would be testing the models rather than the API. The concurrency
test is the exception: it drives the **real** `RecordWriter`, because the bug it
guards is in the write path, not in inference. It was confirmed to fail without
the lock before the lock was added.

End-to-end verification is the curl above, plus the Playwright suite against a
running server.

## What to expect in production

**Analysis is slow on CPU**, and how slow depends on the environment. Measured
with the models already resident, on an M-series laptop:

| Where | 256×256 tile | 704×520 field | Cold boot |
|---|---|---|---|
| host venv (Python 3.14, torch 2.14) | ~50 s | > 180 s | ~9 s (weights cached) |
| this Docker image (Python 3.11) | **21.8 s** | not measured | **63 s** (weights downloaded) |

The container is the number that matters, and it is roughly the plan's estimate
rather than the host's. HF CPU Basic is 2 vCPU and may be slower still. Treat
20–60 s per image as the planning figure, not 10–20 s.

The two environments also disagree very slightly on output — 86.65 % vs 86.68 %
confluency on the same tile — because they resolve different library versions.
That is a probability-map threshold moving under a different BLAS, not a change
in method, but it is worth knowing before comparing a hosted run to a local one.

This has consequences worth deciding on before a demo:

- The page's 200-file batch cap is far beyond what is practical here. A ten-file
  batch is already several minutes at three concurrent requests.
- Vercel does not proxy these calls, so there is no platform timeout to hit —
  but browsers and intermediaries can still drop a very long request.
- For the recording, use small tiles (`test-data/contam_00015.png` and friends
  are 256×256) rather than full fields, and warm the Space first.

If per-image latency matters, the lever is hardware: an upgraded Space with a
GPU changes this by roughly an order of magnitude. `culture/seg.py` already
selects the device with `torch.cuda.is_available()`, so no code change is needed.

**Sleep.** A CPU Basic Space sleeps when idle and reloads its models on the next
request. The page handles this: it shows a warming state and polls `/health`
every 5 s until ready. Before recording, hit `/health` a couple of minutes early.

**The audit chain is per-boot.** Space disks are wiped on restart, so
`prev_record_hash` links records within one boot and no further. `/health` says
so in its `audit` field, and the browser builds and verifies its own chain over
an upload batch, which is where continuity actually lives for a visitor. For a
durable chain, enable persistent storage and set `CULTUREQC_LOG=/data/events.jsonl`.

**Pricing.** HF CPU Basic (2 vCPU, 16 GB) is listed as free; the $5/month in the
original plan may have been the Pro subscription rather than this hardware tier.
Worth confirming on the Space's hardware settings page before assuming a cost.
