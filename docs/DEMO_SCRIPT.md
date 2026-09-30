# Demo script: Celltrio call, Tue Oct 6, 3 PM PDT

12 to 13 minutes of demo by the section times below, then questions. The
audience named two things that matter most, and the order follows them:
**confluency QC** first, then the **GMP-traceable audit record**. Everything
else supports those two.

Every number below is shown on screen by the console and comes from a stored
result: the example numbers from `demo/examples/examples.json`, the replay
numbers from `demo/replays/*.json`, and the rest from the `results/` files
cited in the README. One exception, marked where it comes: in section 2, step 5,
the HT29 card shows the calibrated cutoff's reading and the 8.36 to 3.78 pp
result, but the rest of that step is not on screen; it comes from
`results/confluency_cutoff.md`. Say "precomputed" whenever a precomputed
example or replay is on screen; say "live" only after pressing Analyze.

## Before the call

- [ ] Space on ZeroGPU; the log shows `ZeroGPU`, `anomaly banks verified` and `models loaded`.
- [ ] `results/live_latency_zerogpu.md` from the dry run (`scripts/space_dry_run.py`) is committed; quote its numbers, not a guess.
- [ ] Signed in to huggingface.co in the call browser, Space opened from huggingface.co/spaces/LongGrainRice/cultureqc-console (Analyze then uses the PRO GPU quota).
- [ ] Space opened 10 minutes early (it sleeps after 48 h without visitors; a boot takes minutes) and one live Analyze done; in the 2026-09-29 dry run the first took 6.45 s and the rest a median 3.28 s; in the 2026-09-28 run (commit `0210c79`) one of 7 took 18.50 s.
- [ ] Expect a small "Successfully acquired a GPU" toast (top right) on each live Analyze: that is ZeroGPU attaching
      the GPU. If asked, it is the live run on a GPU, not a precomputed result.
- [ ] The 3D views turn on their own at the dry run. If they don't, check macOS System Settings →
      Accessibility → Display → Reduce motion: the page honours it and stays still when it is on.
- [ ] Browser zoom so the 3D views fit; hardware acceleration on (the 3D views use WebGL). Open both 3D views on the GPU Space in the browser used on the call.
- [ ] The dry run's table: live vs stored confluency, flag and action; read it before the call.
- [ ] Fallback tab open: the same Space works on CPU for everything precomputed.
- [ ] Mac backup started once that day (`deploy/run_console_mac.sh`, then
      http://127.0.0.1:7860 in the call browser). It needs no Hugging Face:
      Cellpose-SAM runs on Apple's GPU from local weights.

## 1. What it is (30 s)

One phase-contrast image in; out come a confluency estimate, an anomaly check
shown for review, a recommended action from fixed rules, and a hash-chained
record. It is built for an instrument to call on every image it captures; a
person steps in on exceptions and audits the trail.

## 2. Confluency QC (4 min), Analyze tab

1. Click **C2C12 normal, 20-40% bin** (precomputed). Cellpose-SAM reads
   39.4%, confidence 0.512; the rules say hold. Point at the provenance card:
   which script, which machine, when.
2. Switch the view to **3D**. It turns once around on its own (about 26 s)
   and stops where it started; click or drag it to stop sooner and take
   over. The height is the model's cell-probability logit, not cell
   thickness; phase contrast does not measure height.
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
     target is unknown; say so rather than guess. The anomaly hold (section 4)
     adds little on healthy flasks: at the 50% target it held 1 of 14
     passage-eligible held-out frames (review 5.8% instead of 5.7%).
4. Click **EVICAN HT29 (real, error case)**. Expert masks say 51.6%;
   Cellpose-SAM reads 29.4%, and its confidence (0.266) is also below the
   floor, so it goes to review. On real held-out EVICAN images the mean
   absolute error is 8.35 pp, reading low (V1). Showing the error case is
   deliberate.
5. The fix, and why it is not live (45 s). Point at the note under the HT29
   caption, "Calibrated cutoff: validated, not live"
   (`demo/examples/cutoff_calibrated.json`, from
   `results/confluency_cutoff.csv`). The floor, bin and LIVECell numbers
   below are **not on screen**; they are from `results/confluency_cutoff.md`.
   - The under-read is the cutoff: a pixel counts as cell only above logit 0,
     and on real images that is too strict. A new cutoff was picked on the
     65 EVICAN eval images that are not among the 33, by a rule fixed before
     scoring: −3.5. On the 33 held-out images the error goes from 8.36 to
     3.78 pp, and images off by more than 10 pp from 13 to 3. This HT29
     image reads 52.9% at confidence 0.829, against the experts' 51.6%.
   - 8.36 rather than V1's 8.35: the study reran the model, and the rerun
     differs by 0.01 pp.
   - It is held back on purpose. At −3.5 the confidence floor would send
     none of the held-out C2C12 frames to review (69 on the same
     quarter-resolution maps at the shipped cutoff; 70 at full resolution in
     `results/review_rate.md`), and 471 of 1228 frames move anomaly bin. On
     six dense LIVECell frames (in Cellpose-SAM's training set, so a check
     only) it reads 3–9 pp high, where the shipped cutoff is within about
     3 pp on five of the six. So the floor and the bins get re-derived
     before it ships, and it goes out as a release, not a hot fix.
   - Say "shipped 8.35, validated fix 3.78". The console runs the shipped
     cutoff; never present 3.78 as what is running. The passage range stays
     untested either way: EVICAN has no image at or above 66%.

## 3. The audit record (2 min)

1. On the 51.4% example, open **Audit Record**. Walk through:
   - `image_hash`: SHA-256 of the image bytes;
   - `model_versions` and `config_hashes`: the models by name, and each
     config by SHA-256. The model weights and the Cellpose-SAM cutoff are not
     hashed yet; say so if asked;
   - `confluency_map_hash`: the SHA-256 of the map drawn in the 3D view (a
     1/4-resolution copy of the map the number was counted from). The 3D note
     says "matches the record": the map drawn is the one the record hashes,
     and the record is chained;
   - `prev_record_hash` and `record_hash`: each record is chained to the one
     before, so editing any past record breaks every later link.
   - `anomaly_used_in_decision: true`, `qc_used_in_decision: false`,
     `decided_by: rules_v0.3`: the record says what fed the action, what
     didn't, and which version of the rules decided.
   - Scope, said before he asks: the record is tamper-evident with full
     provenance; it is not Part 11 compliant on its own. Signed-in users,
     electronic signatures with their meaning, access control and system
     validation belong to the platform around it; the record has
     `decided_by`, `reviewed_by` and `review_outcome` for that layer to
     fill. Field by field and clause by clause (Part 11, the draft Annex 22):
     `docs/audit_mapping.md`.
2. Press **Analyze** on the example shown to run it **live** on the GPU
   (to upload a different image instead, switch the view to Overlay first:
   the 3D view hides the upload area). A new record is appended; the card
   shows "Chain intact" and the record count going up, and the 3D note now
   says the map is held in memory for this view while the record keeps its
   hash. Precomputed examples are never written into this chain, and the card
   says so.
   - On the Space (ZeroGPU) a live Analyze took a median 3.28 s in the dry
     run (`results/live_latency_zerogpu.md`); the 51.4% frame read confidence
     0.014 live against 0.013 stored, still human_review.
   - On the Mac backup, the 51.4% frame reads confidence 0.015 live against
     0.013 stored (Apple's GPU; still below the floor, still human_review).
     If asked, the live-vs-stored table is `results/live_latency_mac_mps.md`:
     flag and action the same as stored on 7 of 7 examples.

## 4. Contamination, honestly (1–2 min)

Say the limit first, before anything is on screen: per visit, at this
magnification, cultureQC does not detect bacterial contamination. Open the
**Detectability** tab: the contamination row says so, and the image under the
table shows why. Left to right: a clean tile; the stress test the contamination
examples come from, with bacteria pasted 16.5× too large (each cell-sized rod is
one "bacterium"); the same bacteria at their real size, with and without the
simulator's haze. At real size the anomaly flag is at chance (held-out AUROC
0.48; flagged on 1 of 97 frames, against 4 of 97 for the same frames without
the bacteria) and confluency reads a median 4.3 pp lower, not higher
(`results/contamination_scale.md`). That is up to 400 bacteria per 256 px tile
area, the original ramp; heavier contamination was not tested, so don't claim
more than that. So a realistically contaminated flask that
reached its target would be recommended for passage. Contamination is confirmed
by culture, Gram stain or PCR, which the row names.

Click **C2C12 contamination, bacteria at real size**: the stress test's second
frame, rebuilt. Confluency 12.2%, against 16.0% for the same frame without
bacteria, and the anomaly check happens to flag it: this is the only one of the
97 frames flagged at real size, while the same frames without bacteria are
flagged 4 of 97, so the flag is at chance (the card says so). The action is
**hold**: nothing irreversible was on the table. If he picks up on the flag:
"the one time it flagged, the clean frames flag as often."

Then the rule, if there is time or he asks: click **C2C12 contamination stress
test** (bacteria 16.5× too large). Cellpose-SAM counts the oversized bacteria
as cells and reads 86.6%, past the 80% target; the anomaly check flags it, and
a flagged image is never passaged automatically: **human review**
(`rules_v0.3`). This is a safety precedence, not a contamination detector:
whenever the flag fires, for any reason, the one irreversible action waits for
a person; hold and feed are unchanged.
- If asked what it costs: at the 50% target, 1 of 14 passage-eligible healthy
  held-out frames was held (`results/review_rate.md`). All 76 passage-eligible
  stress-test frames were held too, which says nothing about real
  contamination.
- If asked about other cell lines: the anomaly banks hold only C2C12, so
  elsewhere the flag is uncalibrated and can hold a healthy flask; it fails
  safe, and a site calibrates it (`scripts/site_calibrate.py`).

## 5. The flask over time (2 min), Flask Timeline tab

1. **Normal flask 1**, Curve: 3-FOV confluency per visit with its noise band.
   One passage forecast, at the first visit at 40%: 80.2 h for the 50% target;
   the recording actually crossed at 83.2 h. The caption gives the backtest it
   belongs to: n = 5 sequences, median error 9.0 h, 4 of 5 intervals covered,
   so this is one example, not a validated accuracy.
2. Switch to **3D: space × time**. The stack builds up visit by visit, in
   time order, while the camera turns once; click the plot to show every
   layer and stop the turn before hovering. Each layer is one visit; green is where the
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
- Which imager and magnification do the confluency reads come from, and at
  what pixel size? The tested setup is phase contrast at 1.3 µm/px.
- What triggers a passage today: a confluency threshold, a schedule, or a
  person? Is that trigger treated as GMP-critical?
- How are analysis parameters (thresholds, model versions) versioned and
  put under change control on the platform side?
- Could a few real RoboCell sequences be shared for validation? They would
  replace C2C12 as the primary test set.

## If something breaks

- **The Space is down (5xx, as on 2026-09-28):** switch to the Mac tab
  (`deploy/run_console_mac.sh`). Same console, same examples and replays;
  live Analyze takes a median 16.43 s per C2C12 frame there
  (`results/live_latency_mac_mps.md`). Say it is running on the laptop.
- **Live Analyze is slow or errors:** stay on the precomputed examples and
  replays; they need no model. Say they are precomputed. The CPU time for a
  full frame is minutes (V9), so don't press Analyze on CPU.
- **3D view is blank:** WebGL is off in that browser; use the 2D overlay and
  the curve, and describe the 3D view from the note text.
- **Asked for an accuracy number not on screen:** point to the README's
  provenance table; don't quote from memory.
