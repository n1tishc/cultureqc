# Demo script: Celltrio call, Tue Oct 6, 3 PM PDT

About 9 minutes of demo, then questions. The audience named two things that
matter most, and the order follows them: **confluency QC** first, then the
**GMP-traceable audit record**. Everything else supports those two.

Every number below is shown on screen by the console and comes from a stored
result: the example numbers from `demo/examples/examples.json`, the replay
numbers from `demo/replays/*.json`, and the rest from the `results/` files
cited in the README. Say "precomputed" whenever a precomputed example or
replay is on screen; say "live" only after pressing Analyze.

## Before the call

- [ ] Space on the GPU tier; the log shows `cuda: True`, `anomaly banks verified` and the warm-up time.
- [ ] `results/live_latency_gpu.md` from the Thu Oct 1 dry run is committed; quote its median, not a guess.
- [ ] One live Analyze done after the warm-up, so the first click on the call isn't a cold start.
- [ ] Browser zoom so the 3D views fit; hardware acceleration on (the 3D views use WebGL). Open both 3D views on the GPU Space in the browser used on the call.
- [ ] The dry run's selfcheck table: live vs stored map points across the cutoff should be small; read it before the call.
- [ ] Fallback tab open: the same Space works on CPU for everything precomputed.

## 1. What it is (30 s)

One phase-contrast image in; out come a confluency estimate, an anomaly check
shown for review, a recommended action from fixed rules, and a hash-chained
record. It is built for an instrument to call on every image it captures; a
person steps in on exceptions and audits the trail.

## 2. Confluency QC (3 min), Analyze tab

1. Click **C2C12 normal, 20-40% bin** (precomputed). Cellpose-SAM reads
   39.4%, confidence 0.512; the rules say hold. Point at the provenance card:
   which script, which machine, when.
2. Switch the view to **3D**. The height is the model's cell-probability
   logit, not cell thickness; phase contrast does not measure height.
   - Green, above the plane: counted as cell. The confluency is that share of
     the full-resolution map.
   - Amber, the band around the plane: borderline pixels, 12.21% here. Their
     share sets the confidence (1 − 4 × borderline fraction), and the note
     shows the arithmetic.
3. Click **C2C12 normal, 40-100% bin** and switch to 3D again. It reads
   51.4%, but 24.67% of the map is borderline: a wide amber shelf instead of
   clean cliffs. Confidence is 0.013, below the 0.30 floor, so the rules
   return **human_review** instead of a number-driven action. This is the
   confluency QC: the system shows when not to trust its own measurement,
   and the picture shows why.
   - Expect "how often does it send work to a person?" From the cache, no
     model run (`results/review_rate.md`): 5.7% of held-out C2C12 frames
     (70 of 1228, 14 sequences), but 43.8% of the 160 frames at 40-60%
     confluency, the densest these recordings get (57.0% at most). Dense
     frames are where the amber shelf grows, as on the 51.4% frame, so
     review is concentrated around the replays' 50% passage target. Say it
     varies by sequence: at 40% or more, 4 of the 8 sequences sent none.
     C2C12 never reaches 60%, so the review rate at the Analyze tab's 80%
     target is unknown; say so rather than guess.
4. Click **EVICAN HT29 (real, error case)**. Expert masks say 51.6%;
   Cellpose-SAM reads 29.4%, and its confidence (0.266) is also below the
   floor, so it goes to review. On real held-out EVICAN images the mean
   absolute error is 8.35 pp, reading low (V1). Showing the error case is
   deliberate.

## 3. The audit record (2 min)

1. On the 51.4% example, open **Audit Record**. Walk through:
   - `image_hash`: SHA-256 of the image bytes;
   - `model_versions` and `config_hashes`: exactly which models and configs
     produced the number;
   - `confluency_map_hash`: the SHA-256 of the map drawn in the 3D view (a
     1/4-resolution copy of the map the number was counted from). The 3D note
     says "matches the record": the map drawn is the one the record hashes,
     and the record is chained;
   - `prev_record_hash` and `record_hash`: each record is chained to the one
     before, so editing any past record breaks every later link.
   - `anomaly_used_in_decision: false`, `qc_used_in_decision: false`: the
     record says what drove the action and what didn't.
   - Scope, said before he asks: the record is tamper-evident with full
     provenance; it is not Part 11 compliant on its own. Signed-in users,
     electronic signatures with their meaning, access control and system
     validation belong to the platform it attaches to (Bioflow's layer); the
     record has `decided_by`, `reviewed_by` and `review_outcome` for that
     layer to fill. The field-by-field mapping is `docs/audit_mapping.md`.
2. Press **Analyze** on the example shown to run it **live** on the GPU
   (to upload a different image instead, switch the view to Overlay first:
   the 3D view hides the upload area). A new record is appended; the card
   shows "Chain intact" and the record count going up, and the 3D note now
   says the map is held in memory for this view while the record keeps its
   hash. Precomputed examples are never written into this chain, and the card
   says so.

## 4. Contamination, honestly (1 min)

Click **C2C12 simulated contamination 1** (precomputed). The anomaly check
flags it for review, but the rules say **Passage**, because the pasted
bacteria are counted as cells (86.6%). That is why the flag is review-only by
design: an image-level flag goes to a person rather than silently changing
an action. Say plainly that the bacteria were pasted at 16.5× their real size,
so this is a stress test, not a detection claim.

## 5. The flask over time (2 min), Flask Timeline tab

1. **Normal flask 1**, Curve: 3-FOV confluency per visit with its noise band.
   One passage forecast, at the first visit at 40%: 80.2 h for the 50% target;
   the recording actually crossed at 83.2 h. The caption gives the backtest it
   belongs to: n = 5 sequences, median error 9.0 h, 4 of 5 intervals covered,
   so this is one example, not a validated accuracy.
2. Switch to **3D: space × time**. Each layer is one visit; green is where the
   frame's map counts cell; blue boxes are the 3 FOVs the visit's number came
   from. The boxes land somewhere different each visit, and that is the
   measurement noise: 6.593 pp SD for fields this size. Hovering a layer shows
   its recorded numbers and hashes; the maps are the cache's own, re-checked
   against their hashes when drawn.
3. **Lamp dimming**, 3D: the red dashed layers failed the quality gate
   (REIMAGE) and are left out of the trend instead of reading as a dip.

## 6. What it can't do, and what would fix it (1.5 min)

Open **Detectability**. At the tested setup (0.25-frame fields, 1–3 per visit,
every 6–12 h), growth stalls and instrument drift are not reliably
detectable; one visit's growth is smaller than the field-to-field noise (V2).
The ask: roughly half-frame fields, 3 per visit, twice a day. The estimated
growth-to-noise ratio goes from 1.12 to 2.71 (`results/growth_signal_summary.md`).
That is estimated, never replayed, and needs confirming on their data.

## 7. Questions for Celltrio (1 min)

- Imaging cadence per flask, and whether the flasks on one instrument are imaged in one round.
- FOVs per visit, and FOV size relative to the flask.
- Image format, bit depth and resolution.
- Does the instrument take z-stacks or any quantitative-phase image? That is
  what a true 3D cell view (thickness, volume) would need; today's 3D views
  show model confidence and time, not height.
- Could a few real RoboCell sequences be shared for validation? They would
  replace C2C12 as the primary test set.

## If something breaks

- **Live Analyze is slow or errors:** stay on the precomputed examples and
  replays; they need no model. Say they are precomputed. The CPU time for a
  full frame is minutes (V9), so don't press Analyze on CPU.
- **3D view is blank:** WebGL is off in that browser; use the 2D overlay and
  the curve, and describe the 3D view from the note text.
- **Asked for an accuracy number not on screen:** point to the README's
  provenance table; don't quote from memory.
