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

One JSON line per analysed image, written by `culture/pipeline.py::analyze` and
appended by `culture/records.py::RecordWriter`. Values below are from the seven
stored example records (`demo/examples/examples.json`).

| Field | What it holds | Note |
|---|---|---|
| `record_id` | UUID v4 | |
| `analysed_at` | UTC timestamp, set by the code at analysis time | |
| `captured_at` | Capture time | Set to analysis time in this prototype; in use it should come from the imager |
| `image_hash` | SHA-256 of the image bytes read | Identifies the bytes, not the instrument that made them |
| `confluency_pct`, `confluency_confidence` | The reading, and `confidence` = 1 − min(1, 4 × share of pixels within ±1 logit of the cutoff). The console and the site show 1 − it as **boundary ambiguity**: a pre-registered check found the score tracks density and does not predict the reading's error (`results/confidence_vs_error.md`). The field keeps its name so the schema doesn't change before the freeze | The name: it is a review trigger, not a confidence in the reading |
| `confluency_method` | `probmap` | |
| `confluency_map_hash` | SHA-256 of the probability map drawn in the console (a 1/4-resolution copy of the map the number was counted from) | The drawn map can be checked against the record |
| `anomaly_*` | Status, density bin, score, z, threshold, flag, `anomaly_bank_sha256`, `anomaly_used_in_decision` | The bank's hash is checked before use (below) |
| `qc_*` | The demoted classifier's flag and confidence; `qc_used_in_decision: false` | Recorded, no vote |
| `recommended_action`, `action_reason` | `passage`, `feed`, `continue` or `human_review`, and the rules engine's one-sentence reason. `continue` was `hold` up to `rules_v0.3` (label only) | |
| `qc_rationale` | A template sentence | `model_versions.vlm` reads `template`; no language model runs |
| `decided_by` | Rules version (`rules_v0.4`) | Would name a person once a reviewer decides |
| `model_versions` | Model names: `cpsam_v2`, `facebook/dinov2-small`, `qc_effnetb0_v1`, `template` | Names only |
| `model_weights_hash` | `null` in every record today | **Gap:** the weights files are not hashed |
| `config_hashes` | SHA-256 of `anomaly.yaml`, `calibration.yaml`, `detectability.yaml`, `qc.yaml` | The Cellpose-SAM cutoff and band are code defaults in `culture/seg.py`, not in a config, so they are not covered (**gap**) |
| `reviewed_by`, `review_outcome` | `null` until a reviewer fills them | For the platform's review workflow |
| `prev_record_hash`, `record_hash` | The chain | See below |
| `schema_version` | `0.3` | `culture/schema.json` now matches what the pipeline writes, and `tests/test_demo_examples.py` validates every stored record against it. It said `0.2` until the pre-freeze pass: v0.3 had added the `anomaly_*`, `config_hashes` and `confluency_map_hash` fields without a bump |

### The chain

`RecordWriter` opens the log in append mode and never rewrites a line. Each
record's `record_hash` is the SHA-256 of its canonical JSON (every other field,
including `prev_record_hash`); the first record links to `"0" * 64`.
`culture/records.py::verify_chain` recomputes every hash and stops at the first
mismatch. The site does the same in the browser (`site/src/lib/verify.js`):
raise one reading by 10 points and that record's hash and the next record's
link both fail.

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
| (e) | Secure, computer-generated, time-stamped audit trails of operator entries and actions; changes must not obscure earlier entries | `analysed_at`, `record_hash`, `prev_record_hash`, append-only writes | Operator identity; the trail of human actions |
| (f) | Operational checks on the sequence of steps | The pipeline's order is fixed in code (segmentation, anomaly, classifier, rules, record) | Sequencing of instrument steps |
| (g) | Authority checks | `decided_by` records who or what decided, but checks nothing | Authority checks, e-signatures |
| (h) | Device checks on the source of data input | `image_hash` fixes which bytes were read; `pixel_size_um` is null in the examples | Which instrument produced the image |
| (i), (j) | Training; written accountability policies | — | Organisational |
| (k) | Control of systems documentation | Git history; config files hashed into each record | Document control |

Electronic signatures (Subpart C) are not implemented.

---

## FDA–EMA *Guiding Principles of Good AI Practice in Drug Development* (January 2026)

Ten principles. The ones this project can show evidence against:

| Principle | cultureQC |
|---|---|
| **4. Clear context of use** | Stated in the README and the detectability matrix: phase-contrast confluency and a per-image anomaly check at the tested setup, with what it cannot detect listed (contamination at real size, growth stalls, instrument drift). |
| **6. Data governance and documentation** | Every dataset's source and licence in `docs/DATASETS.md`; every number in the README's provenance table must appear in the `results/` file it cites (`tests/test_readme_provenance.py`). |
| **7. Model design and development practices** | Negative results kept: in v0.2 a 60-epoch Cellpose-SAM fine-tune on LIVECell showed no improvement, so segmentation stays zero-shot; in v0.3 the classifier was demoted after failing on real C2C12 (`results/classifier_c2c12.md`). |
| **8. Risk-based performance assessment** | Real-image confluency on held-out EVICAN (V1); the irreversible action (passage) waits for a person whenever the anomaly flag fires (`rules_v0.3`). Human-AI interaction is not assessed. |
| **9. Life cycle management** | Versions and hashes in every record; the cutoff change below is held for release, not hot-patched. Scheduled monitoring and re-evaluation are not built. |
| **10. Clear, essential information** | Limits are stated next to the results (README "Known limits", detectability matrix, V1–V10 with Fail marked). |

---

## EU GMP Annex 22, consultation draft, clause by clause

| Clause | The draft asks | cultureQC today | Gap |
|---|---|---|---|
| **1 Scope** | Static models with deterministic output; no generative AI or LLMs in critical applications | Frozen weights (Cellpose-SAM `cpsam_v2`, DINOv2-small, EfficientNet-B0); nothing learns in use. No language model in the decision path: `use_vlm=False` is hard-coded in `culture/pipeline.py` and the rationale is a template | Small cross-device differences: the dense C2C12 example's confidence is 0.013 stored, 0.014 live on ZeroGPU, 0.015 on a Mac GPU (`results/live_latency_zerogpu.md`, `results/live_latency_mac_mps.md`); action unchanged |
| **3.1 Intended use** | Intended use and input sample space described, approved by a process SME | README, detectability matrix, "Imaging requirement" section | No SME approval; input space characterised only for C2C12 and EVICAN |
| **3.2 Subgroups** | Split the input space, e.g. by decision output, site or equipment, defect type | V1 reported by confluency band; review rate by band; anomaly thresholds per density bin | One imaging setup per dataset; no per-instrument or per-site data |
| **4.1–4.2 Metrics, acceptance criteria** | Defined and approved before acceptance testing | V1 has a written decision rule (≲5 pp proceed; 5–10 pp proceed with error analysis; >10 pp stop; `results/confluency_real_summary.md`); V1–V10 carry pass/fail | Written by the developer, not a process SME |
| **4.3 No decrease** | At least as good as the process it replaces | Not measured | No manual baseline (eyeball or count) on the same images |
| **5.1–5.2 Representative, sufficient** | Test data spans the intended use, enough for statistical confidence | V1: 33 real held-out images, 30 cell lines | All 33 are under 500,000 px; three are in the 40–70% band and none at or above 66%, so the passage range is untested |
| **5.3 Labelling** | Labels verified to a very high degree of correctness | EVICAN's published expert masks | Not re-verified here |
| **5.6 Data generation** | Generated test data not recommended; justify any use | V1 uses real images and real labels | Contamination (V5), lamp dimming (V7), growth stall (V6) and the classifier's tiles (V8) are simulated or synthetic; they are labelled so wherever shown and are stress tests, not acceptance evidence |
| **6.1–6.2 Independence** | Test data not used in development | EVICAN is not in Cellpose-SAM's training list (`docs/DATASETS.md`); the calibrated cutoff was picked on the other 65 eval2019 images by a rule fixed before scoring (`results/confluency_cutoff.md`) | The cutoff idea came from the error analysis on the 33, and a preview sweep showing their curve was seen before the rule was written (disclosed there). Public dataset, so no access control on test data |
| **6.3 Identification** | Record which test data was used, when, how many times | The 33 are listed in `results/confluency_real.csv` | Used at least three times: V1 (2026-09-22), an uncommitted quarter-resolution sweep, the cutoff study (2026-09-30) |
| **6.5 Staff independence** | People who saw test data don't train or validate alone (4-eyes) | — | Not met: one person built, tuned and tested everything |
| **7.3 Deviations** | Deviations documented and justified | Written into the results files, e.g. 33 of 98 images under a time budget, the LIVECell ground-truth switch in the cutoff study | |
| **8.1 Feature attribution** | Heat maps or attribution showing what drove the outcome | The probability map behind each reading is drawn (2D overlay and 3D), and its hash is in the record; the anomaly check shows its most distant patches | The demoted classifier's Grad-CAM is off |
| **8.2 Feature justification** | Review of those features as part of test approval | — | Not done formally |
| **9.1 Confidence score** | Log confidence for each prediction | `confluency_confidence`, anomaly score, z and threshold, `qc_confidence`, in every record | `confluency_confidence` does not predict the reading's error (`results/confidence_vs_error.md`); no per-reading error estimate is logged |
| **9.2 Threshold, "undecided"** | Low confidence flagged undecided rather than predicted | Boundary ambiguity above 0.70 (the record's `confidence` below 0.30) returns `human_review` instead of a number-driven action (`rules_v0.4`): 70 of 1228 held-out C2C12 frames, 5.7% (`results/review_rate.md`) | The trigger tracks density, not error, and a complete miss reads as unambiguous: EVICAN 15_Caco-2 (expert 65.1%) reads 0.0% at confidence 1.0 (ambiguity 0), because its map never comes within 1 logit of the cutoff. The floor was set at the shipped cutoff and must be re-derived with any new one (next row) |
| **10.1 Change control** | Changes to model, system or process documented and assessed for retest | Model names, rules version, config and bank hashes in every record; git history. Worked case: a cutoff calibrated off the evaluation images lowers held-out MAE from 8.36 to 3.78 pp (n = 33, `results/confluency_cutoff.md`; not fully blind: the idea came from error analysis of the same 33, an early sweep showing their curve was seen before the rule was written, and the rule's pick, −3.5, is not the evaluation-best, −3.0 at 3.40 pp) and is **held back**: at that cutoff the review trigger would send none of the held-out C2C12 frames to review, and 471 of 1228 frames change anomaly bin, so the floor, the bins, the examples and the replays must be re-derived and retested before it ships | The cutoff and band are code defaults, not in a hashed config; `schema_version` was not bumped for v0.3 |
| **10.2 Configuration control** | Detect unauthorised change | The anomaly banks are checked against the SHA-256 in `configs/anomaly.yaml` before use; a mismatch returns `unavailable`, never a score. Config hashes are written into every record | Model weights are not hashed (`model_weights_hash: null`); config hashes are recorded, not checked against an approved set |
| **10.3 Performance monitoring** | Regular monitoring to detect deterioration, e.g. a lighting change | Replays run a per-visit quality gate that sends failed frames to REIMAGE (simulated lamp dimming in the Flask Timeline) | No ongoing accuracy monitoring. The Analyze path runs no quality gate. Separating instrument drift from culture change failed for single flasks (V7) |
| **10.4 Input sample space monitoring** | Monitor whether inputs stay within the sample space; drift metrics | Per-image anomaly check: DINOv2 patch distance to C2C12 reference banks per density bin. Held-out normal flag rate 10.0% against a 5% target (`results/anomaly_summary.md`) | A per-frame out-of-distribution flag, not drift monitoring over time; banks hold C2C12 only; SPC on residuals failed (V6) |
| **10.5 Human review** | Keep records of human review where a model informs a person's decision | `reviewed_by`, `review_outcome` in every record; `decided_by` separates rules from people | Empty until a review workflow fills them; none is built here |

### What the release that ships the calibrated cutoff has to include

Drawn from the gaps above (clauses 9.2, 10.1, 10.2):

1. The cutoff and band move from code into a config that is hashed into `config_hashes`.
2. The review trigger (the `confidence` floor) and the anomaly bins are re-derived at the new cutoff, on tuning data only.
3. The examples, replays and review rate are regenerated, and V1 re-scored once, recorded as a fourth use of the 33.
4. `model_weights_hash` is filled and `schema_version` bumped.

Until then the live path runs the shipped cutoff (0.0).

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
