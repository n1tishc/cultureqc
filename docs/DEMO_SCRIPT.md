# Demo script (≈12 min)

12 to 13 minutes of demo by the section times below, then questions. The
audience named two things that matter most, and the order follows them:
**confluency QC** first, then the **GMP-traceable audit record**. Everything
else supports those two.

Every number below is shown on screen by the console and comes from a stored
result: the example numbers from `demo/examples/examples.json`, the replay
numbers from `demo/replays/*.json`, and the rest from the `results/` files
cited in the README. One exception, marked where it comes: in section 2, step 5,
the calibration results are on the site's Validation page, not in the console;
they come from `results/confluency_profiles.md` and
`results/confluency_cutoff.md`. Say "precomputed" whenever a precomputed
example or replay is on screen; say "live" only after pressing Analyze.

## Before the call

- [ ] Space on ZeroGPU; the log shows `ZeroGPU`, `anomaly banks verified` and `models loaded`.
- [ ] `results/live_latency_zerogpu.md` from the dry run (`scripts/space_dry_run.py`) is committed; quote its numbers, not a guess.
      The 2026-09-29 run predates the calibration profiles: rerun it once the console Space carries them, and until then
      don't say live matches stored on 7 of 7.
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
   39.4%; the rules say continue (keep culturing). Point at the confluency
   card: "No error band": this microscope has no labelled images, so it has
   no calibration profile, and a reading at or above the target would go to a
   person. Below it, the quality gate calibrated for this microscope passed.
   Then the provenance card: which script, which machine, when.
2. Switch the view to **3D**. It turns once around on its own (about 26 s)
   and stops where it started; click or drag it to stop sooner and take
   over. The height is the model's cell-probability logit, not cell
   thickness; phase contrast does not measure height.
   - Green, above the plane: counted as cell. The confluency is that share of
     the full-resolution map. The plane sits at the setup's profile cutoff
     (logit 0 here, Cellpose-SAM's default, since C2C12 is uncalibrated).
   - Amber, the band around the plane: borderline pixels, 12.21% here. Their
     share is the boundary ambiguity (4 × borderline fraction, capped at 1),
     and the note shows the arithmetic. It is recorded, and no longer decides.
3. Click **C2C12 normal, 40-100% bin** and switch to 3D again. It reads
   51.4%, with 24.63% of the map borderline: a wide amber shelf instead of
   clean cliffs, boundary ambiguity 0.985. The rules say **continue**: 51.4%
   is below the 80% target.
   - Say what changed before he asks. Until `rules_v0.4` an ambiguity above
     0.70 sent this frame to review. It was called "confidence" until a check
     fixed in advance asked whether it predicts the reading's error, and it
     failed: on the 33 held-out EVICAN images, Spearman ρ −0.36 with a 95% CI
     reaching +0.02, and sorting by it is no better than random order
     (p = 0.303; `results/confidence_vs_error.md`). It tracks density instead
     (ρ −0.95 with the reading on held-out C2C12). So since `rules_v0.5` it
     stays in the record and no longer decides; the error band replaces it.
   - Expect "how often does it send work to a person?" From the cache, no
     model run (`results/review_rate.md`), on 1228 held-out C2C12 frames
     (14 sequences): at the 80% target none goes to review, because none
     reaches 80% (57.0% at most), and the quality gate sends 149 (12.1%)
     back to be re-imaged. At the replays' 50% target, 42 (3.4%) go to a
     person, all because this microscope is uncalibrated. Under `rules_v0.4`
     it was 5.7%, piled up at 40–60% confluency.
4. Click **EVICAN HT29 (real, band includes the target)**. Expert masks say
   51.6%; Cellpose-SAM reads **52.9%** with the EVICAN calibration profile
   (cutoff −3.5), against 29.3% at Cellpose-SAM's default cutoff. Point at
   the band on the bar: 23.5–82.3%. It includes the 80% target, so the rules
   send it to a person: **human_review**. The reading is now right, and the
   system still won't decide alone, because a calibration across mixed
   microscopes is loose and its band says so. This image is one of EVICAN's
   33 test images, not among the 65 the profile was fitted on (the caption
   says so).
5. The calibration and its limits (45 s). These numbers are **not in the
   console**; they are on the site's Validation page, from
   `results/confluency_profiles.md` and `results/confluency_cutoff.md`.
   - One profile per imaging setup: a cutoff fitted on labelled images from
     that setup, and a 90% error band measured on images left out of the fit.
     Method, splits and pass criteria were committed before any image was
     scored. On held-out images: MSC (stem cells, 320 images, each of 3
     populations tested with the profile fitted on the other two) 8.19 →
     3.43 pp, band ±7.11 pp; EVICAN 8.36 → 3.78 pp on 33 images, band ±29.40
     pp; LIVECell, a check only (Cellpose-SAM was trained on it), 2.14 → 2.05
     pp.
   - Say EVICAN's 3.78 is **not fully blind** before he asks: the cutoff
     idea came from error analysis of these 33 images, and a
     quarter-resolution sweep showing the evaluation curve was seen before the
     rule was written. The rule picked −3.5, which is not the evaluation-best
     (−3.0 gives 3.40 pp); calibration MAE is flat from −3.5 to −2.5
     (6.95–7.00 pp). The 33 are all under 500,000 px, while 28 of the 65
     calibration images are larger. MSC's 3.43 is the clean result.
   - Why EVICAN's band is so wide: a few calibration images are read far off
     (one at 2% against 65% expert), so at an 80% target any EVICAN reading of
     50.6% or more goes to a person. EVICAN never passages on its own, and
     that is the point of the band.
   - Say what "validated" covers: each profile passed every criterion its
     test images could measure. Neither has test images in the 60–90% band
     where passage decisions are made (MSC has 4 at 60–70%), so accuracy
     there is still untested.
   - The console's own C2C12 microscope has no labelled images, so it stays
     uncalibrated. A site would calibrate with its own labelled images; on
     MSC, 10 labelled images gave 3.81 pp against 3.43 pp from all of them
     (median of 20 draws).
   - Each profile went live through a **change record** approved by the
     repository owner: the first two records of the stored chain (section 3).

## 3. The audit record (2 min)

1. On the 51.4% example, open **Audit Record**. Walk through:
   - `image_hash`: SHA-256 of the image bytes;
   - `model_versions`, `model_weights_hash` and `config_hashes`: the models by
     name and weights, and each config by SHA-256;
   - `confluency_profile` and `confluency_interval`: the setup's profile by id
     and SHA-256, with its status, cutoff and band, and the band around this
     reading (none here: C2C12 is uncalibrated); `quality_gate`: its result
     and the thresholds it used;
   - `confluency_map_hash`: the SHA-256 of the map drawn in the 3D view (a
     1/4-resolution copy of the map the number was counted from). The 3D note
     says "matches the record": the map drawn is the one the record hashes,
     and the record is chained;
   - `prev_record_hash` and `record_hash`: each record is chained to the one
     before, so editing a past record breaks its own hash or the next link.
     Say the limit before he finds it: someone who rewrites a record and
     recomputes every later hash, or deletes the newest records, leaves a
     chain that still verifies. That is caught against an anchored
     checkpoint (record count + head hash) kept in the platform's own audit
     trail or WORM storage, which is why the record is built to attach to one.
     On the site's Records section, the two lower switches show both: "chain
     alone: passes", "against the anchored checkpoint: fails".
   - `anomaly_used_in_decision: true`, `qc_used_in_decision: false`,
     `decided_by: rules_v0.5`: the record says what fed the action, what
     didn't, and which version of the rules decided.
   - The stored chain opens with two `change` records: `uncalibrated` replaced
     by `evican_mixed`, then by `msc_phase`, each by SHA-256, with the
     evidence files by hash and `approved_by: repository owner`. That is how a
     calibration goes live under change control. The site's Records section
     shows them as records 1 and 2.
   - Scope, said before he asks: the record is tamper-evident with full
     provenance; it is not Part 11 compliant on its own. Signed-in users,
     electronic signatures with their meaning, access control and system
     validation belong to the platform around it. A person's review is its
     own `review` record, linked to the reading's hash, so the reading is
     never edited; it carries the reviewer and a reference to the platform's
     signature record. Field by field and clause by clause (Part 11, the draft Annex 22):
     `docs/audit_mapping.md`.
2. Press **Analyze** on the example shown to run it **live** on the GPU
   (to upload a different image instead, switch the view to Overlay first:
   the 3D view hides the upload area). A new record is appended; the card
   shows "Chain intact" and the record count going up, and the 3D note now
   says the map is held in memory for this view while the record keeps its
   hash. Precomputed examples are never written into this chain, and the card
   says so.
   - On the Space (ZeroGPU) a live Analyze took a median 3.28 s in the
     2026-09-29 dry run (`results/live_latency_zerogpu.md`), before the
     calibration profiles. Quote the live-vs-stored table only from a rerun
     against the current examples.
   - On the Mac backup (`results/live_latency_mac_mps.md`, 2026-10-04), flag
     and action are the same as stored on 7 of 7 examples, each read with its
     setup's profile. The stored examples were made on that Mac, so this
     checks the code path, not agreement across machines; across machines,
     the 51.4% frame reads 51.43% on the Mac and 51.45% in the Colab GPU
     cache.

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
more than that. So a realistically contaminated flask whose reading's band
cleared its target would be recommended for passage. Contamination is confirmed
by culture, Gram stain or PCR, which the row names.

Click **C2C12 contamination, bacteria at real size**: the stress test's second
frame, rebuilt. Confluency 12.2%, against 16.0% for the same frame without
bacteria, and the anomaly check happens to flag it: this is the only one of the
97 frames flagged at real size, while the same frames without bacteria are
flagged 4 of 97, so the flag is at chance (the card says so). The action is
**continue**: nothing irreversible was on the table. If he picks up on the flag:
"the one time it flagged, the clean frames flag as often."

Then the rules, if there is time or he asks: click **C2C12 contamination stress
test** (bacteria 16.5× too large). Cellpose-SAM counts the oversized bacteria
as cells and reads 86.6%, past the 80% target, and the anomaly check flags it.
But the quality gate decides first: the pasted bacteria darken the frame (mean
intensity 49.7, outside the 95.3–148.4 calibrated for this microscope), so the
action is **re-image** and no reading is acted on. The gate fails 91.8% of
these stress-test frames (`results/quality_gate_c2c12.md`); it is an image
quality check, not a contamination detector. Had the image passed, the flag
would still hold a passage for a person (since `rules_v0.3`): whenever the
flag fires, for any reason, the one irreversible action waits; continue and
feed are unchanged.
- If he asks about `continue`: it was called `hold` until `rules_v0.4`, which
  read as "put the flask on hold". The label changed and no decision did;
  that is in `CHANGELOG.md`, and the records' hashes changed with it.
- If asked what the gate costs: it sends 12.1% of healthy held-out C2C12
  frames back to be re-imaged (`results/quality_gate_c2c12.md`), mostly on
  exposure. Those thresholds are the 1st and 99th percentiles of the tuning
  frames, so a site sets its own.
- If asked about other cell lines: the anomaly banks hold only C2C12, so
  elsewhere the flag is uncalibrated and can stop a healthy flask's passage; it fails
  safe, and a site calibrates it (`scripts/site_calibrate.py`).

## 5. The flask over time (2 min), Flask Timeline tab

1. **Normal flask 1**, Curve: 3-FOV confluency per visit with its noise band.
   One passage forecast, at the first visit at 40%: 80.2 h for the 50% target;
   the recording actually crossed at 83.2 h. The caption gives the backtest it
   belongs to: n = 5 sequences, median error 9.0 h, 4 of 5 intervals covered,
   so this is one example, not a validated accuracy. It also says the passage
   goes to a person: this microscope has no calibration profile, so under
   `rules_v0.5` a passage at the target is never recommended on its own.
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

- If he asks why 50% here and 80% in Analyze: the held-out C2C12 recordings
  never pass 57.0% as Cellpose-SAM measures them (`results/review_rate.md`), so
  an 80% target would never be reached. The tab's header says so.
- The **Contamination** replay shows no passage time: its forecast is made after
  the pasted bacteria arrive and is driven by them, not by growth, so it is
  shown as suppressed with that reason. A passage there would go to a person
  anyway (no calibration profile), and the card adds that the anomaly check
  flagged the visit.

## 6. What it can't do, and what would fix it (1.5 min)

Open **Detectability**. At the tested setup (0.25-frame fields, 1–3 per visit,
every 6–12 h), growth stalls and instrument drift are not reliably
detectable; one visit's growth is smaller than the field-to-field noise (V2).
The ask: roughly half-frame fields, 3 per visit, twice a day. The estimated
growth-to-noise ratio goes from 1.12 to 2.71 (`results/growth_signal_summary.md`).
That is estimated, never replayed, and needs confirming on their data.

## 7. Questions for instrument integration (1 min)

- Imaging cadence per flask, and whether the flasks on one instrument are imaged in one round.
- FOVs per visit, and FOV size relative to the flask.
- Image format, bit depth and resolution.
- Does the instrument take z-stacks or any quantitative-phase image? That is
  what a true 3D cell view (thickness, volume) would need; today's 3D views
  show the model's cell-probability logit and time, not height.
- Which imager and magnification do the confluency reads come from, and at
  what pixel size? The tested setup is phase contrast at 1.3 µm/px.
- What triggers a passage today: a confluency threshold, a schedule, or a
  person? Is that trigger treated as GMP-critical?
- How are analysis parameters (thresholds, model versions) versioned and
  put under change control on the platform side?
- Could a few real sequences be shared for validation? They would replace
  C2C12 as the primary test set.

## If something breaks

- **The Space is down (5xx, as on 2026-09-28):** switch to the Mac tab
  (`deploy/run_console_mac.sh`). Same console, same examples and replays;
  live Analyze takes a median 16.48 s per C2C12 frame there
  (`results/live_latency_mac_mps.md`). Say it is running on the laptop.
- **Live Analyze is slow or errors:** stay on the precomputed examples and
  replays; they need no model. Say they are precomputed. The CPU time for a
  full frame is minutes (V9), so don't press Analyze on CPU.
- **3D view is blank:** WebGL is off in that browser; use the 2D overlay and
  the curve, and describe the 3D view from the note text.
- **Asked for an accuracy number not on screen:** point to the README's
  provenance table; don't quote from memory.
