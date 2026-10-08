# Fine-tuned confluency profiles: the procedure, and where it stands

**Status: shown beside the reading, never deciding.** Every decision still comes from Cellpose-SAM `cpsam_v2`
(`culture/seg.py`) and the setup's calibration profile. The pipeline can also read an image with a fine-tuned
model, after checking its weights against an approved change record, and record that reading beside the shipped
one; the rules never see it (step 6). One fine-tuned model is approved for this, `mcellseg_ftF_r2`, the model in
the before/after picture (`results/confluency_finetune_figure.md`). In the console Space it reads four of that
lab's test images only, beside the shipped reading (`demo/lab_demo.py`); its weights are downloaded at startup from
a private model repo, not published. This page sets
out how a lab's fine-tuned profile would be made and checked, using the procedure the mCellSeg tests followed.

## Why consider it

- **mCellSeg, a dense dataset from a lab the model had never seen** (`results/confluency_mcellseg.md`,
  `results/confluency_mcellseg_swap.md`; each half scored once):
  - Sealed test: the comparison fixed in advance held. On the 60–90% test images, the fine-tuned reading's
    error was 4.45 pp lower than calibration alone (95% interval +0.83 to +7.94).
  - Halves swapped: a difference of about the same size (+4.84 pp), but its interval (−0.80 to +12.29)
    includes zero, so by its own rule it is not a replication.
  - Both halves together (secondary): +4.60 pp (+1.36 to +8.06). Average error 2.21 pp against 7.61 on all 169
    images.
  - It still falls short of the passage-call mark over both halves: 15 of 17 decided calls agree with the
    experts, against 95%.
- **MSC development runs** (`results/confluency_finetune_dev.md`; images already scored before, recipe fixed
  in advance, each donor population read by a model that never trained on it): error on dense regions 11.99 pp
  with calibration alone, 2.67 pp fine-tuned on 20 images.

## The procedure

1. **Images and outlines from the lab's own setup.**
   - Transmitted-light images with every cell outlined (instance masks). The mCellSeg tests used 79 and 90
     images, pooled over four setups.
   - A band needs at least 9 calibration images per setup (`MIN_CALIB` in `scripts/confluency_mcellseg.py`). A
     criterion on a subset, such as the 60–90% images, is measurable with at least 10 test images (`MIN_IMAGES`).
   - Images that may share a field, well or z-stack form one unit, and a unit never straddles the split
     (`unit_of`).
   - Untested: whether cheaper labels, such as one binary mask per image, work on held-out images. The MSC
     development runs trained on connected components of binary masks, which is development evidence only.
2. **Split and plan, committed before any model reads the images.**
   - Within each setup, units ranked by expert confluency alternate between calibration and test (`split`), so
     both halves span the density range.
   - The plan names the arms, the criteria and the comparison, and says what was already looked at.
     Template: `results/confluency_mcellseg.md`.
3. **Training on a GPU.** The pattern is `nb/06`–`nb/08`.
   - Colab runs from a bundle of the plan's commit. Before anything trains, it checks the shipped Cellpose-SAM
     weights and the committed plan files byte for byte.
   - The recipe is the one Cellpose documents for fine-tuning Cellpose-SAM: learning rate 1e-5, weight decay
     0.1, 100 epochs, batch size 1. It was not tuned here.
   - Cross-fit: two models, each trained on half of the calibration units, read the other half. Their readings
     give the cutoff and the band. A final model trained on all calibration images reads the test images.
   - Only per-image readings at every cutoff, run manifests (training images, weights SHA-256) and logs come
     back. Weights stay in storage the lab controls, identified by their SHA-256.
4. **Scored once, on a CPU.**
   - The readings are committed before scoring.
   - `score` refuses to run a second time. Pass marks: error ≤ 5 pp on all images and at 60–90%, |bias| ≤ 3 pp
     at 60–90%, ≥ 95% of decided passage calls agreeing with the experts, and ≥ 85% of images within the band.
5. **Recorded as a change.** The weights are approved with a `model` change record in
   `configs/approved_changes.jsonl`, a hash-chained log (`scripts/approve_change.py`): the model id and its
   weights' SHA-256, the record it replaces, the reason, the evidence files by SHA-256 and the approver. A later
   record for the same id replaces the earlier one. `mcellseg_ftF_r2` was approved this way to read beside the
   shipped model only; the shipped `cpsam_v2` has a baseline record in the same log.
6. **Used in readings: shown, not deciding.**
   - `analyze(..., finetuned_id=...)` (`culture/pipeline.py`, `culture/finetuned.py`) reads the image with the
     fine-tuned model too, at Cellpose's default cutoff with no band, as a profile that is not validated does
     (`culture/profiles.py`). The reading goes into the record's `finetuned_reading` with
     `used_in_decision: false`.
   - Before it loads, the model's weights are checked against the latest approved change record for its id
     (`culture/approvals.py`). On a mismatch, a missing file or no approval, nothing loads: `finetuned_reading`
     records the refusal, with `confluency_pct` null and the reason. The shipped model gets the same check
     before every reading; if its weights don't match, it does not read and no record is written
     (`docs/audit_mapping.md`, 10.2).
   - Not built: a fine-tuned profile that decides. That needs a profile that passes its criteria on held-out
     images, and a calibration profile tied to the fine-tuned weights.
   - Product path checked on Colab (`results/finetuned_product_readings.md`, rules fixed before the run): the 90
     sealed test images read through `analyze` with both models. The fine-tuned readings were within 0.01 pp of
     the research scripts' readings of the same weights, the shipped readings within 0.01 pp of the committed
     ones, and every check matched. A copy of the fine-tuned weights with one byte changed was refused, and that
     image's shipped reading and action were the same as in its first record.

## What the tests taught

- **A fine-tuned band can be too narrow.** On `lsm_hek_1024` the cross-fit band (±3.59 pp) covered 12 of 18
  test images, and both early passage calls came from that setup. Bands measured on two half-size models may
  understate the final model's error.
- **The gain is largest where calibration alone is stretched.** In the sealed test, the three setups whose
  calibrated cutoff sat at the bottom of the grid, with bands of ±19.7 to ±26.4 pp, gained 3.7 to 7.9 pp in
  error on all test images. `lsm_hek_1024`, where calibration alone worked best, gained 2.0 pp. In the
  swapped half, fine-tuning read worse than calibration there at 60–90% (4.11 against 2.61 pp).
- **The rule that sends a reading to a person when its band includes the target stays.** Fine-tuning reduced
  the share sent to a person, but it did not remove it.
- **Each lab needs its own held-out check.** The evidence so far is one lab, 20× and 40× objectives, and two
  cell lines.

## Costs and limits

- **Labelling.** Outlining every cell on dozens of dense images is the largest cost.
- **GPU time.** Training took 22 min on 79 images and 25 min on 90 images on an A100 (the run manifests).
- **Licences.** Fine-tuned weights inherit Cellpose-SAM's non-commercial status (`README.md`, "Licences and
  commercial use"), and the training images' licences carry over too. For example, the MSC images are
  CC BY-NC-SA.
- **Evidence.** One dataset from one lab, cut two ways.
