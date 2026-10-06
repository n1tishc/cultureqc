# Fine-tuned confluency profiles: the procedure, and where it stands

**Status: not in the product.** The pipeline reads every image with Cellpose-SAM `cpsam_v2`
(`culture/seg.py`) and loads no fine-tuned weights. This page sets out how a lab's fine-tuned profile would be
made and checked, using the procedure the mCellSeg tests followed. The product side (step 6) is not built.

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
5. **Recorded as a change.** If the profile passes and the repository owner approves it, its entry (cutoff,
   band, weights SHA-256) would replace the setup's previous one through a `change` record
   (`culture/records.py`, `change_event`), naming the evidence files by SHA-256 and the approver.
6. **Used in readings: not built.**
   - The pipeline would need to load a profile's own weights.
   - It would also need a run-time check that the weights and the profile match the approved record. Today the
     hashes are recorded but not checked against an approved set at run time (`docs/audit_mapping.md`, 10.2).
   - Until a profile is validated, it reads like an uncalibrated setup (`culture/profiles.py`).

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
