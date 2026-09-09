# Deploying cultureQC

```
Browser ──► Vercel (static)          ──►  HuggingFace Space (Docker + FastAPI)
            site/index.html               deploy/hf-space/
            no build step                 loads the models once, serves /analyze
```

Two independent deployments joined by one URL. Neither can break the other's
build, and the page keeps working — hashing files and building a verifiable
manifest — even when the API is asleep or gone.

## Layout

| Path | What it is |
|---|---|
| `deploy/hf-space/` | the Space, pushable as-is |
| `deploy/hf-space/api.py` | the FastAPI app; the only entrypoint |
| `deploy/hf-space/culture/`, `config/` | **generated** — see sync, below |
| `deploy/sync_space.py` | copies the pipeline into the Space |
| `vercel.json` | serves `site/` with no build |

`culture/` and `config/` inside the Space are copies. Keeping a second
hand-edited copy of the analysis code is how a deployed pipeline quietly stops
being the one in the repo, so they are generated:

```bash
python deploy/sync_space.py            # refresh the copies
python deploy/sync_space.py --check    # report drift, exit 1 if any
```

Run the sync after any change under `culture/` or `config/`, before pushing.

## Backend — HuggingFace Space

Create a Space: **SDK Docker**, hardware **CPU Basic**, visibility **Public**
(the frontend calls it without credentials). Then:

```bash
python deploy/sync_space.py
cd deploy/hf-space
git init && git remote add origin https://huggingface.co/spaces/LongGrainRice/cultureqc-api
git add -A && git commit -m "cultureQC API"
git push -u origin main
```

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

## Frontend — Vercel

The site is **one self-contained HTML file with no build step** — not a React
app, so there is no bundler, no `node_modules`, and no `VITE_*` environment
variable. The API URL is a constant in the page, set at assemble time:

```js
// site/src/template.html
const ANALYSIS_API = "https://longgrainrice-cultureqc-api.hf.space";
```

```python
# site/src/assemble.py
SITE_URL = "https://cultureqc.vercel.app"   # absolute URL for og:image
```

After editing either, rebuild and commit the result:

```bash
python site/src/assemble.py
```

Import the repo into Vercel. `vercel.json` already sets `outputDirectory: site`
and disables the build and install commands, so the framework preset should be
**Other** and no environment variables are needed.

### Why no `VITE_API_URL`

An env var would require a build step to substitute it, which would mean adding
a bundler to a page that does not need one. The constant is set by
`assemble.py`, which is the build step this project already has.

## Local development

One command gives you the page and the pipeline on the same origin:

```bash
python deploy/hf-space/api.py     # http://127.0.0.1:7860
```

`/` serves `site/index.html` when running from a checkout (the Space has no
`site/`, so there it stays JSON). The page prefers a local endpoint over the
hosted one whenever it is opened from localhost, a private LAN address, or
disk — so local work never silently tests the deployed service.

This replaces the previous `demo/serve.py`, which spoke an older contract (raw
request body, `{"ok": true}`) and would have drifted from the deployed API.

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

23 contract tests: readiness semantics, input validation, response shape, the
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
