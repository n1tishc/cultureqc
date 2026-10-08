# Audit trail mapping: the cultureQC record against Part 11, the FDA–EMA AI principles and draft Annex 22

> **Disclaimer:** cultureQC is a portfolio/research project, not a validated GMP component.
> This maps the record and the evidence behind it to regulatory text as a pattern
> demonstration, not a compliance claim. GMP validation needs formal IQ/OQ/PQ, a risk
> assessment and organisational SOPs, all outside this project.

Checked against the primary texts on 2026-09-30:
[21 CFR 11.10](https://www.law.cornell.edu/cfr/text/21/11.10);
FDA and EMA, [*Guiding Principles of Good AI Practice in Drug Development*](https://www.fda.gov/media/189581/download), January 2026;
the European Commission's [consultation draft of EU GMP Annex 22: Artificial Intelligence](https://health.ec.europa.eu/document/download/5f38a92d-bb8e-4264-8898-ea076e926db6_en?filename=mp_vol4_chap4_annex22_consultation_guideline_en.pdf)
(consultation 7 July to 7 October 2025). No final Annex 22 text had been published as of
2026-09-30; clause numbers below are the draft's and may change.

Each row says what exists today and what does not. Gaps are listed, not hidden.

---

## What a record carries

One chain, three record types (schema `0.4`, `culture/schema.json`), written by
`culture/records.py::RecordWriter` in append mode:

- **reading**: one analysed image (`culture/pipeline.py::analyze`, and the
  console's `demo/analysis.py`).
- **review**: a person's decision on a reading, as a new record that points to
  the reading's `record_hash`. The reading is never edited, so a review cannot
  change what the model said, and a later reviewer sees both.
- **change**: a change under change control, such as a new confluency profile,
  rules version or model: what it replaces and what replaces it (by id and
  SHA-256), why, the validation evidence (by path and SHA-256), and who
  approved it.

Fields of a reading:

| Field | What it holds | Note |
|---|---|---|
| `record_type`, `record_id` | `reading`, UUID v4 | |
| `analysed_at` | UTC timestamp, set by the code at analysis time | |
| `captured_at` | Capture time | In use it comes from the imager, through the host platform |
| `flask_id`, `cell_line`, `protocol_stage` | Vessel or labware ID, cell line, the protocol step that took the image | Supplied by the host platform |
| `lineage` | Passage number and parent vessel | Supplied by the host platform; `null` in the demo |
| `imager_id`, `fov` | The instrument, and the field of view within the vessel | Supplied by the host platform; `null` in the demo |
| `environment` | A snapshot the host supplies at capture (e.g. temperature, CO₂), stored as given | cultureQC does not read it |
| `image_hash` | SHA-256 of the image bytes read | Identifies the bytes; `imager_id` says which instrument |
| `confluency_pct` | The reading at the profile's cutoff | |
| `confluency_profile` | The imaging setup's calibration profile: id, SHA-256 of its entry in `configs/confluency_profiles.yaml`, status, cutoff, error band | A setup with no labelled images is `uncalibrated`: default cutoff, no band |
| `confluency_interval` | Reading ± the profile's 90% error band, measured on held-out labelled images from that setup (`results/confluency_profiles.md`) | `null` for an uncalibrated setup |
| `confluency_confidence` | 1 − boundary ambiguity (the share of pixels near the cutoff). Recorded; decides nothing since `rules_v0.5`, because it tracks density and not the reading's error (`results/confidence_vs_error.md`) | |
| `confluency_method`, `confluency_map_hash` | `probmap`; SHA-256 of the probability map drawn in the console (a 1/4-resolution copy of the map the number was counted from) | The drawn map can be checked against the record |
| `quality_gate` | Pass or fail, reasons, which threshold set, and the three metrics | `null` where no gate is calibrated for the setup |
| `recovery_request` | `{"action": "reimage", "reasons": [...]}` when the gate fails: a machine-readable request for the host's scheduler | |
| `anomaly_*`, `anomaly_bin_confluency_pct` | Status, density bin, score, z, threshold, flag, `anomaly_bank_sha256`, `anomaly_used_in_decision`; the reading at the default cutoff that picked the bin (the banks were calibrated at that cutoff) | The bank's hash is checked before use (below) |
| `qc_*` | The demoted classifier's flag and confidence; `qc_used_in_decision: false` | Recorded, no vote |
| `recommended_action`, `action_reason` | `passage`, `feed`, `continue`, `human_review` or `reimage`, and the rules engine's one-sentence reason | |
| `qc_rationale` | A template sentence | `model_versions.vlm` reads `template`; no language model runs |
| `decided_by` | Rules version (`rules_v0.5`) | A person's decision is a review record |
| `model_versions` | Model names: `cpsam_v2`, `facebook/dinov2-small`, `qc_effnetb0_v1`, `template` | |
| `model_weights_hash` | SHA-256 of each model's weights file, keyed like `model_versions` | `null` for a file not on the machine |
| `model_check` | The segmentation model's weights checked against the latest approved change record for `cpsam_v2` in `configs/approved_changes.jsonl`: status, the file's SHA-256, the approved SHA-256, and the approvals log's head hash | A reading exists only when the status is `match` (below) |
| `finetuned_reading` | A fine-tuned model's reading of the same image, its check and its status (`not_validated`); `used_in_decision: false` | `null` unless asked for. If its weights don't match, `confluency_pct` is `null` and the check says why |
| `config_hashes` | SHA-256 of `anomaly.yaml`, `approved_changes.jsonl`, `calibration.yaml`, `confluency_profiles.yaml`, `detectability.yaml`, `finetuned_models.yaml`, `qc.yaml`, `quality.yaml` | |
| `prev_record_hash`, `record_hash` | The chain | See below |
| `schema_version` | `0.5` | `tests/test_record_events.py` validates all three types against the schema; 0.4 records still validate |

Fields of a review: `reviews_record_id` and `reviews_record_hash` (the
reading), `recommended_action`, `decision` (`accept` or `override`),
`final_action`, `reason` (required for an override), `reviewer` (`id`, `name`),
`signature_meaning` (`review`, `approval` or `rejection`), `signed_at`, and
`host_signature_ref`, a pointer to the host platform's electronic-signature
record. cultureQC does not sign: identity, authentication and the signature
belong to the host. The console's review form writes this record into its
session chain with the name typed there, which shows the shape, not a
signature.

### The chain

`RecordWriter` opens the log in append mode and never rewrites a line. Each
record's `record_hash` is the SHA-256 of its canonical JSON (every other field,
including `prev_record_hash`); the first record links to `"0" * 64`.
`culture/records.py::verify_chain` recomputes every hash and stops at the first
mismatch. The site does the same in the browser (`site/src/lib/verify.js`):
raise one reading by 10 points and that record's hash and the next record's
link both fail. Two more switches there show the rows below that a chain alone
passes: rewrite record 3 and every later hash, or delete the last two records.
Each is checked against a checkpoint of the seven stored records made when the
site is built (`site/assets/build_data.py`, with `culture.records.checkpoint`)
and fails against it, while the chain alone still verifies.

What the chain alone catches, and what it doesn't (one test per row in
`tests/test_records_chain.py`):

| Change to the log | Chain alone | Against a checkpoint |
|---|---|---|
| Edit a record, leave its hash | Caught at that record | Caught |
| Edit a record and recompute its own hash | Caught at the next record's link | Caught |
| Insert or reorder records | Caught | Caught |
| Edit a record and recompute **every later hash** | **Passes** | Caught (`rewritten`) |
| Delete the **newest** records | **Passes** | Caught (`truncated`) |
| Log missing, or empty | Fails (`missing_log`, `empty_chain`) | Fails |

The two rows that pass are a property of any unkeyed hash chain: whoever can
write the file can recompute it. They close only against a **checkpoint**, the
log's record count and head hash (`python -m culture.records checkpoint`),
stored outside the log's trust boundary. Fewer records than the checkpoint
counted is a truncation; a record at that position with a different hash is a
rewrite. Records appended after the checkpoint still pass, so checkpoints are
taken periodically, or one per record.

**Where the anchor lives.** In the intended deployment, each `record_hash`, or
a periodic checkpoint, is written into the platform's own audit trail or into
WORM storage. That copy is the anchor, and it is the reason the record is
designed to attach to an existing Part 11 audit trail rather than stand alone.
A checkpoint kept next to the log can be rewritten along with it. The
checkpoint can carry an HMAC-SHA256 (`--sign`, key from
`CULTUREQC_CHECKPOINT_KEY`, off by default) so an edited checkpoint file is
rejected, but that doesn't protect against anyone who holds the key; a separate
trust domain (the platform's trail, WORM storage, an RFC 3161 timestamp) does.

This is tamper evidence, not non-repudiation: records are not signed.

---

## 21 CFR Part 11, §11.10 (closed systems)

| §11.10 | Requirement (short) | What cultureQC provides | Left to the platform |
|---|---|---|---|
| (a) | Validation; ability to discern invalid or altered records | The hash chain, its two verifiers and the checkpoint (above; the checkpoint needs an anchor outside the log); V1–V10 in the README | System validation (IQ/OQ/PQ) |
| (b) | Accurate, complete copies, human-readable and electronic | Each record is one self-contained JSON line | Export and inspection copies |
| (c) | Protection and retrieval through the retention period | Append-only file | Storage, backup, retention |
| (d) | Limiting system access to authorised individuals | Nothing | Access control |
| (e) | Secure, computer-generated, time-stamped audit trails of operator entries and actions; changes must not obscure earlier entries | `analysed_at`, `record_hash`, `prev_record_hash`, append-only writes. A person's decision is a separate review record linked to the reading's hash, so it never overwrites the reading; a configuration change is a change record with what it replaced | Operator identity and authentication |
| (f) | Operational checks on the sequence of steps | The pipeline's order is fixed in code (segmentation, anomaly, classifier, rules, record) | Sequencing of instrument steps |
| (g) | Authority checks | `decided_by` names the rules version; a review names its reviewer and the meaning of the signature; nothing is checked | Authority checks, e-signatures |
| (h) | Device checks on the source of data input | `image_hash` fixes which bytes were read; `imager_id` and `fov` carry the instrument and position the host reports; the reading names the imaging setup's calibration profile | Checking that the image came from that instrument |
| (i), (j) | Training; written accountability policies | — | Organisational |
| (k) | Control of systems documentation | Git history; config files hashed into each record | Document control |

Electronic signatures (Subpart C) are not implemented. A review record carries
the fields §11.50 asks a signed record to show (the signer's printed name, the
date and time, and the meaning of the signature) and a reference to the host's
signature record; the binding of signature to record (§11.70) is the host's.

---

## FDA–EMA *Guiding Principles of Good AI Practice in Drug Development* (January 2026)

Ten principles. The ones this project can show evidence against:

| Principle | cultureQC |
|---|---|
| **4. Clear context of use** | Stated in the README and the detectability matrix: phase-contrast confluency and a per-image anomaly check at the tested setup, with what it cannot detect listed (contamination at real size, growth stalls, instrument drift). |
| **6. Data governance and documentation** | Every dataset's source and licence in `docs/DATASETS.md`; every number in the README's provenance table must appear in the `results/` file it cites (`tests/test_readme_provenance.py`). |
| **7. Model design and development practices** | Negative results kept: in v0.2 a Cellpose-SAM fine-tune on LIVECell showed no improvement, so segmentation stays zero-shot (from the v0.2 notes; the run is not reproduced in this repository); in v0.3 the classifier was demoted after failing on real C2C12 (`results/classifier_c2c12.md`). |
| **8. Risk-based performance assessment** | Real-image confluency on held-out images per imaging setup (`results/confluency_profiles.md`); the irreversible action (passage) waits for a person when the reading's error band includes the target, when the setup is uncalibrated, or when the anomaly flag fires (`rules_v0.5`). Human-AI interaction is not assessed. |
| **9. Life cycle management** | Versions and hashes in every record; a calibration profile changes only through a `change` record that names the profile it replaces, the evidence and the approver. Scheduled monitoring and re-evaluation are not built. |
| **10. Clear, essential information** | Limits are stated next to the results (README "Known limits", detectability matrix, V1–V10 with Fail marked). |

---

## EU GMP Annex 22, consultation draft, clause by clause

| Clause | The draft asks | cultureQC today | Gap |
|---|---|---|---|
| **1 Scope** | Static models with deterministic output; no generative AI or LLMs in critical applications | Frozen weights (Cellpose-SAM `cpsam_v2`, DINOv2-small, EfficientNet-B0); nothing learns in use. No language model in the decision path: `use_vlm=False` is hard-coded in `culture/pipeline.py` and the rationale is a template | Small cross-device differences: the dense C2C12 example's confidence is 0.015 stored (made on a Mac GPU) and 0.014 live on ZeroGPU (`results/space_dry_run_e6c44671.md`); action unchanged |
| **3.1 Intended use** | Intended use and input sample space described, approved by a process SME | README, detectability matrix, "Imaging requirement" section | No SME approval; input space characterised only for C2C12 and EVICAN |
| **3.2 Subgroups** | Split the input space, e.g. by decision output, site or equipment, defect type | By equipment: one calibration profile per imaging setup, each tested on its own held-out images, with errors reported per ground-truth band (`results/confluency_profiles.md`); anomaly thresholds per density bin | Three setups scored (EVICAN's mixed microscopes, an MSC phase-contrast setup, and LIVECell's instrument as an in-domain check); the console's C2C12 setup has no labelled images and is uncalibrated; no per-site data |
| **4.1–4.2 Metrics, acceptance criteria** | Defined and approved before acceptance testing | The profiles' criteria A1–A5 were committed before any image was scored (`results/confluency_profiles.md`, commit `1ef52cb`); V1 has a written decision rule (≲5 pp proceed; 5–10 pp proceed with error analysis; >10 pp stop); V1–V10 carry pass/fail | Written by the developer and approved by the repository owner, not a process SME |
| **4.3 No decrease** | At least as good as the process it replaces | Not measured | No manual baseline (eyeball or count) on the same images |
| **5.1–5.2 Representative, sufficient** | Test data spans the intended use, enough for statistical confidence | 33 held-out EVICAN images (30 cell lines) and 320 MSC images, leave one population out | The passage range is untested on held-out setups: no EVICAN test image is above 60% and four MSC images are at 60–70%, so the 60–90% criteria (A2–A4) are not measurable there; only LIVECell, an in-domain check, covers it |
| **5.3 Labelling** | Labels verified to a very high degree of correctness | EVICAN's published expert masks | Not re-verified here |
| **5.6 Data generation** | Generated test data not recommended; justify any use | V1 uses real images and real labels | Contamination (V5), lamp dimming (V7), growth stall (V6) and the classifier's tiles (V8) are simulated or synthetic; they are labelled so wherever shown and are stress tests, not acceptance evidence |
| **6.1–6.2 Independence** | Test data not used in development | Neither EVICAN nor the MSC set is in Cellpose-SAM's training list (`docs/DATASETS.md`); each profile's cutoff is picked on calibration images only, and MSC's test population is left out of its fold's fit | EVICAN's cutoff idea came from error analysis on the 33, and a sweep showing their curve was seen before the rule was written (`results/confluency_cutoff.md`). LIVECell is the model's training domain, so it is an in-domain check only. Public datasets, so no access control on test data |
| **6.3 Identification** | Record which test data was used, when, how many times | Every scored image, its split and its readings are in `results/confluency_profiles.csv`; the 33 EVICAN test images are listed in `results/confluency_real.csv` | The 33 have been used four times: V1 (2026-09-22), an uncommitted quarter-resolution sweep, the cutoff study (2026-09-30), the profiles study (2026-10-02) |
| **6.5 Staff independence** | People who saw test data don't train or validate alone (4-eyes) | — | Not met: one person built, tuned and tested everything |
| **7.3 Deviations** | Deviations documented and justified | Written into the results files, e.g. 33 of 98 images under a time budget, the LIVECell ground-truth switch in the cutoff study, the MSC dataset's licence, population count and magnification checked and written into the pre-registration before scoring (`2baa18f`), the C2C12 labels not made | |
| **8.1 Feature attribution** | Heat maps or attribution showing what drove the outcome | The probability map behind each reading is drawn (2D overlay and 3D), and its hash is in the record; the anomaly check shows its most distant patches | The demoted classifier's Grad-CAM is off |
| **8.2 Feature justification** | Review of those features as part of test approval | — | Not done formally |
| **9.1 Confidence score** | Log confidence for each prediction | `confluency_interval`: the reading ± its setup's 90% error band, measured on images left out of the fit (test coverage: MSC 89.4%, EVICAN 100%); anomaly score, z and threshold; `confluency_confidence` kept for the record | One band per setup, not per image; an uncalibrated setup has none; `confluency_confidence` does not predict the reading's error (`results/confidence_vs_error.md`) |
| **9.2 Threshold, "undecided"** | Low confidence flagged undecided rather than predicted | `rules_v0.5`: a reading whose error band includes the target returns `human_review`, and so does a reading at or above the target from an uncalibrated setup; boundary ambiguity no longer decides (`results/review_rate.md`) | The band is the setup's, so a gross miss is not flagged by it: EVICAN 15_Caco-2 (expert 65.1%) reads 2.1% at −3.5. Such misses are why EVICAN's band is ±29.4 pp, which sends any EVICAN reading above 50.6% to a person at an 80% target |
| **10.1 Change control** | Changes to model, system or process documented and assessed for retest | The cutoff and band are configuration (`configs/confluency_profiles.yaml`, written from the results by `scripts/write_profiles_config.py` and hashed into every record); replacing a profile is a `change` record with the profile it replaces and the new one by SHA-256, the evidence by SHA-256, the reason and the approver. Worked case: per-setup profiles, method and criteria committed before scoring, lower held-out MAE from 8.19 to 3.43 pp on MSC and from 8.36 to 3.78 pp on EVICAN (`results/confluency_profiles.md`; EVICAN's is not fully blind: its 33 test images had been used three times before, row 6.3) | Approval is the repository owner's alone, with no SME sign-off |
| **10.2 Configuration control** | Detect unauthorised change | Before the segmentation model reads an image, its weights' SHA-256 is compared with the latest approved `model` change record in `configs/approved_changes.jsonl`, a hash-chained log whose chain is verified whenever it changes; on any mismatch the model does not read (`culture/approvals.py`). A fine-tuned model is checked the same way, and a refusal is written into the reading's `finetuned_reading`. The anomaly banks are checked against the SHA-256 in `configs/anomaly.yaml` before use; a mismatch returns `unavailable`, never a score. Config hashes, the profile's SHA-256 and the model weights' SHA-256 are written into every record | A refused segmentation reading leaves no record, because there is no reading to record. The weights file is hashed when first checked and again when its size or modification time changes. The shipped model's file is hashed just after the model loads (Cellpose may download it on first use), so a file swapped between loading and hashing is not caught; a model whose file fails the check is dropped, not kept. The DINOv2 and classifier weights, the profiles and the configs are recorded, not checked against an approved set. The chain shows a change record was not edited later, not who wrote it |
| **10.3 Performance monitoring** | Regular monitoring to detect deterioration, e.g. a lighting change | Where a quality gate is calibrated for the setup (C2C12), it runs before any reading is used, in Analyze and in the replays, and a failed image returns `reimage` with a machine-readable `recovery_request` | No ongoing accuracy monitoring. The C2C12 gate fails 12.1% of held-out normal frames (`results/quality_gate_c2c12.md`). Separating instrument drift from culture change failed for single flasks (V7) |
| **10.4 Input sample space monitoring** | Monitor whether inputs stay within the sample space; drift metrics | Per-image anomaly check: DINOv2 patch distance to C2C12 reference banks per density bin. Held-out normal flag rate 10.0% against a 5% target (`results/anomaly_summary.md`) | A per-frame out-of-distribution flag, not drift monitoring over time; banks hold C2C12 only; SPC on residuals failed (V6) |
| **10.5 Human review** | Keep records of human review where a model informs a person's decision | A person's decision is its own `review` record, linked to the reading's hash, with the decision, final action, reason, reviewer, meaning of the signature and a pointer to the host's signature record (`culture.records.review_event`); `decided_by` separates rules from people | Identity and the signature itself are the host platform's (`docs/host_platform.md`) |

### What `rules_v0.5` and schema 0.4 changed, against the gaps above

- **9.1, 9.2:** each reading carries its setup's measured error band, and the band, not boundary ambiguity, decides when a person checks a passage.
- **10.1, 10.2:** the cutoff and band moved from code defaults into a hashed config under change control; model weights are hashed; `schema_version` is 0.4.
- **10.3:** the quality gate runs in Analyze, not only in the replays.
- **10.5:** a review is its own record, linked to the reading.

### What schema 0.5 changed

- **10.2:** the segmentation model's weights are checked at run time against the latest approved change record (`model_check`); a fine-tuned model's reading can be recorded beside the shipped one without deciding anything (`finetuned_reading`, `docs/FINE_TUNING.md`).

Still open: a process SME's approval of the criteria and the profiles (4.1–4.2), held-out evidence in the passage range (5.1–5.2), and independent test data and staff (6.1–6.5).

---

## What this is not

- **Not a validated GMP system.** Formal validation (IQ/OQ/PQ, risk assessment per GAMP 5 / ICH Q9) is outside scope.
- **Not Part 11 compliant on its own.** Access control, signatures, SOPs, training and backup are procedural and platform controls, not this software.
- **Not signed.** The chain gives tamper evidence, not non-repudiation.
- **Not anchored on its own.** A full rewrite or a deleted tail passes the chain alone; it is caught only against a checkpoint stored in the platform's trail or WORM storage ([The chain](#the-chain)).
- **Not a substitute for expertise.** It recommends; a qualified person decides on exceptions and audits the trail.

The value is the pattern: a structured, versioned, hash-chained record that says what
fed each decision and what did not, designed to be written into an existing audit
trail rather than to replace one.
