# Audit Trail Mapping — cultureQC Record → Regulatory Requirements

> **Disclaimer:** cultureQC is a portfolio/research project, not a validated GMP component.
> This document maps the record design to regulatory expectations as a pattern demonstration,
> not a compliance claim. Actual GMP validation requires formal IQ/OQ/PQ, risk assessment,
> and organizational SOPs beyond the scope of this project.

---

## 21 CFR Part 11 — Electronic Records; Electronic Signatures

Part 11 governs electronic records and signatures in FDA-regulated environments.
The cultureQC audit record is designed so that each field maps to a specific
§11.10 requirement.

| Record Field | §11.10 Clause | Requirement | How cultureQC Addresses It |
|---|---|---|---|
| `record_id` (UUID) | (a) Validation | Each record is uniquely identifiable | UUID v4, never reused |
| `analysed_at` (ISO-8601) | (e) Audit trails — time-stamped | Record the date and time of operator actions | UTC timestamp generated at analysis time |
| `record_hash` (SHA-256) | (e) Audit trails — computer-generated | Audit trail entries shall be computer-generated | SHA-256 computed from canonical JSON; not editable by humans |
| `prev_record_hash` | (e) Audit trails — cannot be modified | Changes shall not obscure previously recorded information | Hash chain: any modification to any prior record breaks the chain and is detectable by `verify_chain.py` |
| `image_hash` (SHA-256) | (e) Audit trails — independent of record | Link the record to the original data | SHA-256 of the raw image bytes; proves which image was analysed |
| `model_versions` | (a) Validation — system reproducibility | Ensure accuracy, reliability, and ability to discern invalid records | Exact model identifiers (e.g. `cpsam_v2`, `qc_effnetb0_v1`) |
| `model_weights_hash` | (a) Validation — reproducibility | | SHA-256 of each weights file; proves which exact checkpoint produced the output |
| `decided_by` | (d) Limiting system access | Authority checks and device checks | Records whether the decision was made by `rules_v0.2` (deterministic) or a human reviewer |
| `reviewed_by` | (g) and (h) Authority checks, device checks | Persons who develop, maintain, or use the system | Nullable; filled by the human who reviewed the automated decision; `null` = unreviewed |
| `review_outcome` | (g) Authority checks | | Records the human's accept/reject/override of the automated recommendation |
| `confluency_method` | (a) Validation | | Which algorithm produced the confluency number (`cpsam_v2_probmap`, `threshold_baseline`) |
| `qc_rationale` | (e) Audit trails | Reason for action | Two-sentence, evidence-referencing explanation of the QC flag and recommended action |
| `recommended_action` | (e) Audit trails — operator actions | | The action the system recommended (`passage`, `feed`, `hold`, `human_review`) |
| `action_reason` | (e) Audit trails — reason for action | | One-sentence deterministic explanation from the rules engine |
| `schema_version` | (a) Validation | | Version of the record schema; enables forward/backward compatibility checks |

### Append-only JSONL log

The event log (`events.jsonl`) is append-only: `RecordWriter` opens the file in
append mode (`'a'`) and never rewrites existing content. Each line is a self-contained
JSON record. The hash chain (SHA-256 of each record linked to the previous record's
hash via `prev_record_hash`) provides tamper evidence:

- **Genesis record:** `prev_record_hash` = `"0" * 64`
- **Subsequent records:** `prev_record_hash` = `record_hash` of the previous line
- **Verification:** `verify_chain.py` recomputes every hash from the canonical JSON
  and stops at the first mismatch. Any insertion, deletion, modification, or reordering
  of records is detected.

This is not cryptographic non-repudiation (no digital signatures), but it is
tamper evidence sufficient for a research/prototype audit trail.

---

## FDA–EMA Guiding Principles of Good AI Practice (January 14, 2026)

The ten joint principles emphasize a human-centric, risk-based approach to AI
across research, clinical trials, manufacturing, and safety monitoring.
cultureQC's design aligns with several:

| Principle | cultureQC Design Element |
|---|---|
| **Transparency and documentation** | Every decision produces a structured, human-readable record with a rationale. Model versions and weights hashes are logged. |
| **Human oversight** | The rules layer decides; the VLM/template recommends. Both are logged. `reviewed_by` and `review_outcome` fields exist for human sign-off. QC flags above threshold always route to `human_review`. |
| **Risk-proportionate validation** | The QC classifier is validated per-class and per-severity, with the headline metric being early-stage contamination recall. Limitations (synthetic training data, unvalidated real-world transfer) are stated explicitly. |
| **Data quality and relevance** | Training data provenance is documented per source (LIVECell CC BY-NC, DeepBacs CC BY, Trizna CC BY), with licence tracks separated. |
| **Robustness and reliability** | Cross-morphology generalization tested on a held-out cell line. Negative results (uniform dilation, fine-tuning) are documented to show what was tried and why it didn't work. |

---

## EU Annex 22 — AI in GMP Manufacturing (Draft, consultation closed Oct 2025)

The European Commission's draft Annex 22 to the EU GMP guide specifically addresses
AI/ML in pharmaceutical manufacturing. Final text is expected mid-2026.

Key requirements and how cultureQC maps to them:

| Annex 22 Theme | cultureQC Design Element |
|---|---|
| **Auditability** | Hash-chained, append-only event log with per-record rationales. Every decision is traceable to a specific model version, weights, image, and timestamp. |
| **Attributability** | `decided_by` distinguishes automated vs human decisions. `reviewed_by` records the human reviewer. `model_versions` and `model_weights_hash` identify the exact software that produced the output. |
| **Model lifecycle management** | `model_versions` and `model_weights_hash` fields enable tracking which model version was active at any point. Schema versioning (`schema_version: "0.2"`) enables forward compatibility. |
| **Human-in-the-loop** | Any QC flag above the confidence threshold triggers `human_review` before further automated action. The system recommends; it does not act autonomously on safety-critical decisions. |
| **Explainability** | `qc_rationale` provides a human-readable, evidence-referencing explanation. The rules engine is fully deterministic and inspectable. |

**Caveat:** Annex 22 is draft text. The final version may shift specific requirements.
This mapping is based on the consultation draft and should be reviewed against the
final text when published.

---

## What This Is Not

- **Not a validated GMP system.** Formal validation (IQ/OQ/PQ, risk assessment per GAMP 5 / ICH Q9) is outside scope.
- **Not Part 11 compliant out of the box.** Compliance requires organizational controls (access management, SOPs, training, backup/recovery) that are procedural, not software.
- **Not a substitute for human expertise.** The system is a "second opinion" layer; final decisions rest with qualified personnel.
- **Not cryptographically signed.** The hash chain provides tamper evidence, not non-repudiation. Digital signatures (e.g. PKCS#7) would be needed for true Part 11 electronic signatures.

The value claim is the **pattern**: a structured, versioned, hash-chained, evidence-referencing record
that is designed to sit inside an existing audit trail system (e.g. Bioflow) and that maps
naturally to the regulatory requirements labs are already subject to.
