# VP core demo (5-minute target)

This is the standalone product walkthrough for a VP considering a one-setup
offline evaluation. Use the **stored website analyses**, not the live console.
The timings below are a proposed run of show, **not a passed rehearsal**.
I1–I4 and scoped V1/V2 checks are complete locally. Human screen-reader and
real 200% zoom checks, plus the timed V3 rehearsal, remain pending.
Nothing in this script establishes production readiness.

## Start and reset

Use [the local homepage](http://127.0.0.1:5173/) with no example query. The
expected opening is **Read the culture. Understand the next step.**, followed
by the actual image/result workspace. Do not assume the public deployment
contains these uncommitted changes.

For a clean restart, navigate to `http://127.0.0.1:5173/` and reload the page.
The default is **Measure coverage**, C2C12 mid density, with Segmentation
selected. Within the workspace, **Reset** also restores this example and its
contour-only view, even when it is already selected. A selection may add
`?example=c2c12_normal_20_40#demo`; that is expected.

If the server is not running, start it from the repository root with
`npm --prefix site run dev -- --host 127.0.0.1 --port 5173 --strictPort`.
Use the existing server if that port is already serving this project; do not
start a second instance or stop an unrelated process.

## Preflight before presenting

- [ ] Confirm the local homepage and direct refreshes of `/records` and
      `/validation` work. Verify the new opening and **Evaluate on your setup**
      CTA rather than relying on a public-site bookmark.
- [ ] Open both primary examples below. Confirm the microscopy image loads
      and **Raw image** / **Segmentation** visibly remove/restore the cyan
      contour. These controls annotate a stored analysis; they do not run a model.
      Asset paths relative to the site root:
      `img/v3/ex/c2c12_normal_20_40.webp`,
      `img/v3/ex/c2c12_normal_20_40_contour.json`,
      `img/v3/ex/evican_ht29.webp`,
      `img/v3/ex/evican_ht29_contour.json`.
- [ ] Check the fixture outputs: coverage **39.41%**, **CONTINUE**, no calibrated
      error band; HT29 **52.91%**, band **23.51–82.31%**, target **80%**,
      human-review recommendation. Keep each example's visible scope in view.
- [ ] **Inspect this exact record** must select coverage record **4** at
      `/records?record=c2c12_normal_20_40#chain`, or HT29 record **9** at
      `/records?record=evican_ht29#chain`. Wait for verification to finish;
      confirm both chain and checkpoint pass, not just that JSON is visible.
- [ ] From the HT29 record, **Return to this reading** must open
      `/?example=evican_ht29#demo`. Exercise browser Back/Forward between the
      two analysis selections and check image, result and record link agree.
      Reset before the audience joins.
- [ ] Confirm `/records#integration`, `/#evidence`, `/validation#profiles`
      and `/#pilot` resolve. Have the local source
      [calibration protocol](../results/confluency_profiles.md) and
      [host boundary](host_platform.md) available if source links are offline.
- [ ] Label the run **stored research demonstration**. No live inference,
      physical action, contamination clearance or compliant host integration
      is being demonstrated. The separate live console is optional Q&A only.
- [ ] Check the presenting viewport and text size manually. Earlier functional
      checks passed, but automated screenshot capture timed out; visual signoff
      is still pending. Start a fresh timer for the later V3 rehearsal.

## Core click sequence

Routes below are relative to `http://127.0.0.1:5173`.

| Time | Screen, action and expected output | Short spoken prompt |
| --- | --- | --- |
| 0:00–0:40 | Open `/` with no query. Point to the real image, adjacent measurement, recommendation and record link; click **Explore an analysis** to reach `/#demo`. | “cultureQC turns a microscopy image into a measurement, a rule-based recommendation and a record your team can inspect. These are stored results, not a live run.” |
| 0:40–1:40 | Stay on **Measure coverage**, or click **Reset**. Switch **Raw image**, then **Segmentation**. Expect **39.41%**, **CONTINUE**, and the visible absent-band notice. | “The cyan contour shows what was counted. This reading has no calibrated error band. Continue is the stored rule result—not a health finding, contamination clearance or validated instruction to act.” |
| 1:40–2:30 | Click **Understand a review boundary**. URL becomes `/?example=evican_ht29#demo`. Point to **52.91%**, **23.51–82.31%**, target **80%**, and human review. | “The band crosses the target, so the rules ask a person. This is mixed-setup EVICAN calibration, not fully blind, and the C2C12 anomaly bank is not calibrated for HT29. The band estimates measurement error; it does not validate an action.” |
| 2:30–3:15 | Click **Inspect this exact record**. At `/records?record=evican_ht29#chain`, confirm record **9** is selected. Show verification, then **Follow this exception into an illustrative review**. Do not run tamper modes in the core path. | “This is the exact result. A review adds a new record pointing to it; it never edits the reading. This separate example uses a fictional reviewer, not a real approval or signature. Hash verification checks integrity, not biological validity or compliance.” |
| 3:15–4:10 | Click top-nav **Integration** to `/records#integration`; point to supplied inputs, returned outputs and host responsibility. Then open `/#evidence` for the one MSC finding. | “The current interface is a Python call, not a deployed partner service. Your host owns capture, scheduling, identity, signatures, retention and action. On 320 MSC images, leave-one-population-out calibration gave 3.43 pp error versus 8.19 at the default cutoff. Only four images were dense; passage-range criteria were unmeasurable.” |
| 4:10–5:00 | Click **Evaluate on your setup** to `/#pilot`. Show inputs, proposed readout and **Define the gate before starting**. | “The next decision is an offline evaluation on one setup: representative images, independent labels and an intended target. Before scoring, freeze the protocol and decision gate. Measure error, review and re-image burden, useful decision coverage and latency. Agree stop, gather-more or proceed—not actuation.” |

Recovery return path from Records: **Return to this reading** →
`/?example=evican_ht29#demo`; then **Reset** if restarting the whole story.
Use the header CTA for evaluation, not **Research live console**.

## If the core path breaks

| Failure | Honest recovery |
| --- | --- |
| Image or contour unavailable | Keep the selected identity; use **Retry media**. If only the contour fails, show **Raw image** and explicitly say the segmentation visual is unavailable. If the image fails, skip the visual demonstration and identify the remaining numbers as stored outputs. Do not silently substitute another sample. |
| Unexpected/invalid example URL | Acknowledge the unavailable-example notice; use **Open coverage example**, then **Reset**, or navigate to the exact starting URL and reload. Check the intended ID before continuing. |
| Verification pending, failed or no match | Do not claim success. On Records use **Retry verification**, or **Reset local demonstration** after tampering; reload if needed. If failure persists, say integrity could not be checked in this session and skip that claim. On the homepage, reload to retry. |
| Website unavailable | Restore the local server or pause the interactive demo. Discuss the checked-in protocol and intended evaluation as documents; do not imply an unavailable visual, fresh analysis or verification was shown. |
| External source/live console unavailable | Use the checked-in source documents. Keep the core path on the labelled stored website analyses. A stored result is never a successful fallback inference run. |
| Time runs short | Skip optional Q&A, not the limitations or evaluation gate. Record the overrun; do not mark the five-minute rehearsal passed. |

## Optional Q&A only

- On Records, the three tamper switches change a temporary browser copy.
  A simple edit breaks a hash; a full rewrite or deleted tail can pass the
  chain-alone check but fail the anchored checkpoint. Use **Reset local
  demonstration** and confirm original verification returns before leaving.
- **More examples** retains all seven stored analyses. Synthetic stress
  examples are labelled and are not evidence of realistic contamination
  detection; they are not the centerpiece of the core walkthrough.
- The fine-tuned model is experimental and decides nothing. The pooled
  mCellSeg view is secondary, and the swapped primary comparison did not
  replicate; use `/validation#dense` with its qualifications.
- The **Research live console** is a separate surface. If used, identify a
  fresh run explicitly and disclose failure or queueing as such. Host shadow
  use must follow the [local host-evaluation contract](specs/host-evaluation.md)
  and [release boundary](specs/release-state.md). Target-host validation,
  commercial clearance and production integration remain separate gates.
- The preserved technical appendix below is a longer console-specific
  reference, not the current five-minute website sequence or a passed live
  preflight. Check its historical service assumptions and source results
  before using them in Q&A.

# Technical appendix

# Demo script (≈15 min)

15 to 16 minutes of demo by the section times below, then questions. The
audience named two things that matter most, and the order follows them:
**confluency QC** first, then the **GMP-traceable audit record**. Everything
else supports those two.

Every number below is shown on screen by the console and comes from a stored
result: the example numbers from `demo/examples/examples.json`, the replay
numbers from `demo/replays/*.json`, and the rest from the `results/` files
cited in the README. Two exceptions, marked where they come: in section 2,
step 5, the calibration results, and in step 6, the sealed-test results, are
on the site's Validation page, not in the console; they come from
`results/confluency_profiles.md`, `results/confluency_cutoff.md`,
`results/confluency_mcellseg.md` and `results/confluency_mcellseg_swap.md`. Say "precomputed" whenever a precomputed
example or replay is on screen; say "live" only after pressing Analyze.

## Before the call

- [ ] Space on ZeroGPU; the log shows `Cellpose-SAM weights downloaded, match` (or `present, match`), `ZeroGPU`,
      `anomaly banks verified` and `models loaded`.
- [ ] The dry run (`scripts/space_dry_run.py`) of the published Space is committed: `results/space_dry_run_0fb0ffa0.md`
      (2026-10-20, Space commit `0fb0ffa0`, `rules_v0.7`, record schema 0.8, each example read with its setup's
      profile); quote its numbers, not a guess. Rerun it after any republish.
- [ ] Signed in to huggingface.co in the call browser, Space opened from huggingface.co/spaces/LongGrainRice/cultureqc-console (Analyze then uses the account's GPU quota). A visitor who is not signed in gets a few live runs, then Hugging Face refuses more; the stored examples still open.
- [ ] Space opened 10 minutes early (it sleeps after 48 h without visitors; a boot takes minutes) and one live Analyze done; in the 2026-10-20 dry run the first took 4.89 s and the rest a median 3.47 s; on 2026-10-11 two of seven runs took 17–19 s, and in the 2026-09-28 run (commit `0210c79`) one of 7 took 18.50 s.
- [ ] A viewer's own image must be an 8-bit grayscale or RGB file (PNG, JPEG or 8-bit TIFF). A 16-bit TIFF or a
      transparent PNG is refused with a message, by design: no per-image contrast conversion is applied.
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

## 2. Confluency QC (7 min), Analyze tab

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
6. The fine-tuned demo set (3 min). The row of four buttons under the
   examples, "Fine-tuned demo set". Press one, then **Analyze** (live; each
   took 3.6–4.6 s in the 2026-10-20 dry run of Space `0fb0ffa0`,
   `results/space_dry_run_0fb0ffa0.md`; one took 13.6 s on 2026-10-11). Two cards appear: the shipped
   reading, which decides as always, and the fine-tuned card, marked "not
   validated · decides nothing", with the experts' value from the lab's own
   outlines.
   - Say what it is first: the same Cellpose-SAM model, fine-tuned on 79
     labelled images from one public lab (mCellSeg). These four are test
     images from that lab it never trained on. Its reading sits beside the
     shipped one; the shipped reading and the rules still decide.
   - The console's model, `mcellseg_ftF_r2`, is a retrain of the model scored
     in the sealed test (same recipe, same 79 images; that one was not kept).
     On the 90 test images the two read a mean absolute 0.23 pp apart, at most
     1.52 pp (`results/confluency_finetune_figure.md`).
   - The image opens on the **Shipped** view: green is what the shipped model
     counted, yellow the experts' outline of every cell. Switch to
     **Fine-tuned** to show the other model on the same outline.
   - Running order, target 80%; this lab's microscopes have no calibration
     profile. Readings from the dry run above, experts' values from
     `results/confluency_mcellseg.csv`:
     1. **HUVEC · CD7_09**: experts 77.3%; shipped 43.5% → continue;
        fine-tuned 78.7%.
     2. **HEK · FumGW**: experts 74.2%; shipped 56.1% → continue;
        fine-tuned 75.4%.
     3. **HEK · 5A**: experts 88.5%; shipped 84.3% → human review;
        fine-tuned 89.9%. The live reason reads "Passage timing is unknown":
        the console is not told when the flask was last passaged, and
        `rules_v0.7` checks that first. Without a calibration, a reading at
        or above the target would go to a person anyway.
     4. **HEK · FumGW z2, the failing case**: experts 77.9%; shipped 83.3% →
        human review; fine-tuned 83.4%. Show it as a failure: the fine-tuned
        reading is above the target, so if it decided it would call passage
        early. On dense images it reads high: +4.91 pp at 60–90% in the sealed
        test, missing its own ±3 pp mark.
   - Where it stands (on the site's Validation page, not in the console;
     `results/confluency_mcellseg.md`, `results/confluency_mcellseg_swap.md`):
     on the 90 sealed test images, MAE 2.65 pp fine-tuned against 7.80 pp
     for the calibration profile. With the halves swapped, the gain was not
     replicated by the rule fixed beforehand. One lab, two cell lines. The
     weights inherit Cellpose-SAM's non-commercial terms and are not
     published.

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
     On the site's Records page (`/records`), the two lower switches show both: "chain
     alone: passes", "against the anchored checkpoint: fails".
   - `anomaly_used_in_decision: true`, `qc_used_in_decision: false`,
     `decided_by: rules_v0.5`: the record says what fed the action, what
     didn't, and which version of the rules decided.
   - The stored chain opens with two `change` records: `uncalibrated` replaced
     by `evican_mixed`, then by `msc_phase`, each by SHA-256, with the
     evidence files by hash and `approved_by: repository owner`. That is how a
     calibration goes live under change control. The site's Records page
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
   - On the Space (ZeroGPU) a live Analyze took a median 3.47 s in the
     2026-10-20 dry run (`results/space_dry_run_0fb0ffa0.md`), and flag and
     action were the same as stored on 7 of 7 examples, each read with its
     setup's profile; readings were within 0.04 pp of the stored ones. Live
     records are schema 0.8 under `rules_v0.7`; the stored examples keep
     their original schema and rules, and the live reason text differs (for
     HT29 it names the unknown passage timing, not the band).
   - On the Mac backup (`results/live_latency_mac_mps.md`, 2026-10-04), flag
     and action are the same as stored on 7 of 7 examples, each read with its
     setup's profile. The stored examples were made on that Mac, so this
     checks the code path, not agreement across machines; across machines,
     the 51.4% frame reads 51.43% on the Mac, 51.47% on the Space's GPU and
     51.45% in the Colab GPU cache.

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
- **The fine-tuned demo-set buttons are missing:** the Space did not get the
  weights at startup, so the demo set is off. Skip section 2, step 6, and show
  the before/after figure on the site's Validation page (`/validation#dense`)
  instead; say it is a stored figure, not a live reading.
- **Asked for an accuracy number not on screen:** point to the README's
  provenance table; don't quote from memory.
