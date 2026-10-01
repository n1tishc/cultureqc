# cultureQC: everything done on the upgrade branch

As of 2026-09-28. Branch `slice-1b-compute-cache` (`git log main..HEAD` for
the full list). Nothing is merged to `main`; that happens only when the
owner says so. The detailed, row-by-row log is `docs/STATUS.md`; this file is
the readable overview. Every number here is copied from the results file named
next to it.

**Where things stand:** the pipeline was validated on real images (Phase A),
the parts that failed validation were demoted or captioned (Phase B), and a
review console is live on its own
Hugging Face Space with a GPU, plus two backups (Mac, Colab) that don't depend
on Hugging Face.

---

## 1. Ground rules kept throughout

- All work on this branch; `main` untouched.
- Every number comes from a script or a stored result, labelled real,
  synthetic, simulated visits or simulated faults.
  `tests/test_readme_provenance.py` checks the README's numbers against their
  sources; `tests/test_claims.py` blocks claims the evidence doesn't support
  (for example "Part 11 compliant").
- Seeds fixed; nothing tuned on held-out data (a 10 tuning / 14 held-out
  split of the C2C12 sequences, `results/replay_fleet_split.csv`).
- Colab runs copy data from Drive to local disk first, never run from Drive.
- The two Spaces already running (`cultureqc-demo`, `cultureqc-api`) were
  never changed; the console got its own Space.

## 2. Timeline

| Dates | What | Main commits |
|---|---|---|
| Sep 22 | Slice 1b: compute cache, real-image validation, dataset fetchers, Colab notebooks | `816a098` … `7c17eb5` |
| Sep 22 | Slice 2: visit summary schema, quality gate, history, replay, Flask Timeline tab | `9476b8b` … `7460c2b` |
| Sep 22 | Slice 3: growth model and passage forecast | `7f330e2`, `e86ce93` |
| Sep 25–26 | Phase A: C2C12 time-lapse data (`nb/03`), replay fleet, checks V1–V10, report | `d8f8395` … `68c490a` |
| Sep 26–27 | Phase B: classifier scale test (B0), detectability matrix (B4), calibration + demotion (B3), real replays (B1), anomaly check (B2) | `a0af827` … `6120328` |
| Sep 27–28 | B8: review console, 3D views, demo script, review rate, console Space, backups, ZeroGPU | `73e5441` … `b55e8ec` |
| Sep 28 | Rules v0.3 (a flag holds a passage); 3D motion and per-example cameras | `2bd61df`, `444fdee` |

## 3. Data and the compute cache (Slices 0, 1, 1b)

- **Baseline** before any change: tag `v1.0-pre-upgrade`, `docs/REPO_MAP.md`,
  `results/baseline_latency.md`.
- **Compute cache** (`culture/cache.py`): one GPU pass on Colab stores every
  model output (Cellpose-SAM confluency and probability maps, classifier
  logits, DINOv2 embeddings, quality metrics) so later work never re-runs a
  model. After `nb/03` the local `cache/` holds 6,983 images, including 2,088
  real C2C12 time-lapse frames (24 sequences) and 649 simulated fault frames
  (lamp dimming, contamination). Backup of the previous cache:
  `~/Desktop/projs/cultureqc_cache_backup_nb02`.
- **Fixes found on the way:** Drive's file system, not compute, was the
  ~16 s/tile bottleneck (hence the copy-to-local rule); manifest row counts
  were always 0; a no-op resume wiped shard hashes; the cache now flushes
  every 100 records and resumes without duplicates
  (`tests/test_cache_resume.py`).
- **Measurement noise:** field-of-view sampling noise measured on the C2C12
  frames themselves (`results/fov_noise_c2c12_summary.md`), since the first
  fit was almost entirely below 10% confluency.

## 4. New pipeline parts (Slices 2 and 3)

- `culture/quality.py`: a quality gate (blur, exposure, uniformity). A failed
  image gets **REIMAGE** and is left out of trends. Thresholds for C2C12 come
  from the tuning sequences (`results/quality_gate_c2c12.md`).
- `culture/history.py`, `culture/replay.py`: flask history and a replay mode
  that turns recorded time-lapse frames into simulated visits, from the cache
  only.
- `culture/growth.py`: per-flask growth fit, a passage-time forecast with an
  interval, and a one-step-ahead expected value.
- `schemas/visit_summary.v1.json`: the per-visit record.

## 5. Phase A: does the architecture hold up on real data? (V1–V10)

Full report: `docs/ARCHITECTURE_VALIDATION.md`. Summary (from the README):

| Check | Result | Verdict |
|---|---|---|
| V1 Confluency on real images (EVICAN) | MAE 8.35 pp (n = 33), reads low | Pass; the passage band is not measurable |
| V2 Growth between visits vs FOV noise | 0.35 / 0.65 at 1 FOV (6 h / 12 h); needs 2 | Fail |
| V3 Passage forecast | median abs. error 1.9–9.0 h (n = 5 sequences, 50% target) | No verdict: too few sequences |
| V4 Density-conditioned anomaly | Spearman ρ −0.16 binned vs −0.09 global | Fail |
| V5 Anomaly flag vs contamination | AUROC 1.00 (n = 2, bacteria pasted 16.5× too large); 0.48 with the same bacteria at real size | Pass, small and exaggerated; **Fail** at real size |
| V6 SPC on residuals | 3.75 false alarms / 100 visits; contamination 0/2, stall 0/2 | Fail |
| V7 Instrument vs culture drift | normal fleet drifts too | Fail for single flasks |
| V8 Classifier calibration | ECE 0.0139 (T = 1.5536) | Pass, synthetic only |
| V9 Live latency on CPU | 689 s per FOV | Fail |
| V10 Growth per experiment | doubling time 12.4–17.7 h | Informational |

What this meant: confluency (Cellpose-SAM) and the per-image anomaly check
are usable; SPC and instrument drift are not in the product; CPU is far too
slow for a live demo, so the demo needs a GPU (section 8).

## 6. Phase B: acting on the results

- **B0, classifier scale test (fail):** the QC classifier calls only 2.9% of
  held-out real normal frames normal even at matched scale
  (`results/classifier_scale_test.md`). Found on the way: the simulated
  bacteria are pasted 16.5× too large, so every contamination number is on an
  exaggerated fault, and the docs say so.
- **Contamination at real size (2026-09-28, after external feedback):** the
  same 97 frames rebuilt with the bacteria at their real size, same seed and
  density, frozen thresholds, scored on the Mac against the same frames with
  no fault (`scripts/contamination_scale.py`, `results/contamination_scale.md`).
  The flag is at chance (held-out AUROC 0.48; 1 of 97 flagged, 4 of 97 without
  bacteria), the quality gate fails no more often, and confluency reads a
  median 4.3 pp lower. Up to that density (400 per 256 px tile area; heavier
  not tested), per-visit contamination is not detected at this magnification,
  so the v0.3 hold gives no protection against it. The
  detectability row, README limits, validation report, anomaly card and demo
  script say so; the console's Detectability tab shows the side-by-side image.
- **B3, classifier demoted:** it still runs and is recorded, but the
  recommended action ignores it (`qc_used_in_decision: false`), its
  probabilities are temperature-scaled (T = 1.5536), and the UI shows it
  collapsed as "not used in the recommendation". Retraining was a no-go
  (owner decision, 2026-09-27).
- **B4, detectability matrix + claims check:** `configs/detectability.yaml`
  says, per fault type, what was tested and on what; shown in the
  Detectability tab; its hash goes in every record. `tests/test_claims.py`
  enforces the wording.
- **B2, per-image anomaly check:** DINOv2-small patch distance to banks of
  normal C2C12 patches, per confluency bin. Since `rules_v0.3` (owner
  decision, 2026-09-28) a flag holds a passage for human review; hold and
  feed are unchanged. Held-out normal flag rate 10.0%
  (`results/anomaly_summary.md`). Live and cached scores agree (largest
  difference 0.00015 on 10 real frames).
- **B1, Flask Timeline on real replays:** 5 held-out C2C12 flasks (normal ×2,
  contamination, slowdown, lamp dimming) with 3-FOV confluency, noise band,
  quality gate, anomaly flag and one passage forecast
  (`demo/replays/*.json`).

## 7. The review console (B8)

`demo/app.py`, three tabs:

- **Analyze:** 7 precomputed examples (C2C12 normal ×3, a contamination stress
  test with bacteria 16.5× too large, the same kind of frame with the bacteria at
  real size, EVICAN PC3 accurate, EVICAN HT29 error case), each labelled
  "Precomputed example" with script, device, date and credit; **Analyze** runs
  any image live. Cards: confluency with confidence, anomaly check with a
  zoomed heatmap, recommended action, rationale, and the hash-chained audit
  record ("Chain intact · record #N").
- **3D views (B8 part 2; motion added 2026-09-28):**
  - **Analyze → 3D:** Cellpose-SAM's cell-probability map as a surface
    (height = logit, labelled "not cell thickness"), the cutoff plane, the
    borderline band that sets the confidence. The map's SHA-256 is a record
    field (`confluency_map_hash`); the view re-hashes the map and says whether
    it matches the record, which ties the picture to the audit trail.
  - **Flask Timeline → 3D space × time:** one layer per visit from the cache's
    own maps, the 3 FOV boxes each visit's number came from, gate failures in
    red, fault onset marked; each layer re-hashed when drawn.
  - **Motion** (`demo/viz3d.py`): each example opens at its own camera angle
    (chosen from rendered candidates); the camera turns once, slowly, and
    stops where it started; the timeline stack builds up visit by visit. A
    click or drag stops it; nothing moves for viewers who ask for reduced
    motion; without the script the figures are complete and still.
- **Detectability:** the matrix from B4.
- **Review rate** (`results/review_rate.md`): the 0.30 confidence floor sends
  5.7% of held-out frames to human review, but 43.8% of those at 40–60%
  confluency. The anomaly hold adds 1 of 14 passage-eligible held-out frames at
  the 50% target (total 5.8%) and holds all 76 passage-eligible simulated
  contamination frames.
- **GMP scope** (in the demo script): tamper-evident with provenance, not
  Part 11 compliant on its own; `decided_by`, `reviewed_by`,
  `review_outcome` are there for the platform layer (`docs/audit_mapping.md`).
- **Demo script:** `docs/DEMO_SCRIPT.md`, about 9 minutes, confluency QC first,
  then the audit record.

## 8. Where the console runs

| Where | How | Live Analyze | Source |
|---|---|---|---|
| **Space `LongGrainRice/cultureqc-console`** (main) | ZeroGPU, a GPU attached per Analyze | median 3.28 s; 7 of 7 examples same flag and action as stored | `results/live_latency_zerogpu.md` |
| **Mac backup** | `deploy/run_console_mac.sh`, Cellpose-SAM on Apple's GPU, no Hugging Face at run time | median 16.43 s; 7 of 7 same | `results/live_latency_mac_mps.md` |
| **Colab backup** | `nb/05_console_colab.ipynb` + `~/Desktop/projs/cultureqc_console_bundle.zip` (console + all weights) | median 12.06 s on a Tesla T4; 7 of 7 same | `results/live_latency_colab_gpu.md` |
| CPU (for reference) | — | 689 s per FOV | `results/live_latency.md` |

- **Why ZeroGPU** (2026-09-28): no cost beyond PRO, no switching hardware on
  and off, and the link stays fast after the call. Dedicated GPU still works
  with no code change (`deploy/hf-space-demo/zerogpu.py` only activates on
  ZeroGPU).
- **Things only the Space showed:** Spaces cache examples by default (crashed
  on Gradio's CSV limit; now off); the 502s on 2026-09-28 were a Hugging Face
  outage, which is why the backups exist; after a hardware switch the old
  container keeps serving until the new one is up.
- **Checked on the live Space:** all 7 examples open, both 3D views match
  their hashes, the 3D motion runs and stops on a click, no page errors; a
  signed-out Analyze also works (contamination 1 live: Human Review under
  `rules_v0.3`). ZeroGPU shows a small "Successfully acquired a GPU" toast on
  each live Analyze.
- `cultureqc-demo` and `cultureqc-api` never changed.

## 9. Tests

`pytest` (the `tests/` suite plus the API Space's tests): 265 passed, 1
expected failure (2026-09-28). Includes the
README provenance check, the claims check, demo example parity, replay
re-export, device selection (`tests/test_seg_device.py`), the ZeroGPU mode
(`tests/test_console_zerogpu.py`), the v0.3 rule (`tests/test_rules_anomaly.py`)
and the 3D figures' motion contract (`tests/test_viz3d.py`).

## 10. Open decisions

1. ~~Contamination examples~~ **Resolved 2026-09-28:** the flag now holds the
   passage (`rules_v0.3`), so both contamination examples recommend human
   review. Their confluency still reads 86.6% / 88.6% (pasted bacteria count
   as cells), which the caption says.
2. ~~Contamination examples in the Analyze gallery~~ **Resolved 2026-09-28
   (owner):** one of each. Example 1 stays as the labelled stress test (the
   only on-screen case where the hold fires); example 2 became the same frame
   with the bacteria at real size (`c2c12_contamination_real_size`). That
   frame, fixed by the choice, happens to be the only one of 97 flagged at real
   size; it was kept (swapping would be cherry-picking), and its card says the
   flag is at chance.
3. Shifted synthetic tiles and V5(a) patch embeddings (`docs/STATUS.md`, open
   questions): defaults hold (not done).

## 11. What's left

| When | What | Who |
|---|---|---|
| Done 2026-09-29 | v0.3 Vercel project created (production branch `slice-1b-compute-cache`): https://cultureqc-cvoy.vercel.app, set in `site/index.html` | owner |
| Thu Oct 1 | Dry run: `scripts/space_dry_run.py` again; open both 3D views in the call browser; open the v0.3 site (https://cultureqc-cvoy.vercel.app) at 1280×720 | |
| Fri Oct 2 | Freeze | |
| Mon Oct 5 | Rehearsal with `docs/DEMO_SCRIPT.md` | |
| Tue Oct 6, 3 PM PDT | Call: open the Space 10 min early, signed in; Mac backup running | |
| After | Merge to `main` only on the owner's word | owner |
