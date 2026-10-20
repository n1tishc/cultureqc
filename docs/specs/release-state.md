# Release state and evaluation boundary

This page describes the repository and deployment state documented locally on
2026-10-19. Deployment rows below are repository/deployment-workflow observations,
not a fresh check of a live service. A branch name or publish script does not
prove that its remote currently matches this checkout.

The separate [host evaluation harness and contract](host-evaluation.md) defines
the offline host path; this page describes release identity and provenance.

## Surface and identity map

| Surface or artifact | Role and state | Product / rules / record schema | Model and configuration identity | Source and interpretation |
|---|---|---|---|---|
| Repository library in this checkout | Current local implementation; working tree contains unreleased changes | Library rules `rules_v0.7`; `RecordWriter` emits schema `0.8` | Model IDs: `cpsam_v2`, `qc_effnetb0_v1`, `quality_v1`, `facebook/dinov2-small`; exact loaded weight hashes are runtime-dependent and belong to each record. Source config includes `configs/qc.yaml`, `configs/anomaly.yaml`, `configs/quality.yaml`, `configs/confluency_profiles.yaml`, `configs/approved_changes.jsonl`, and `config/lines/A172.yaml`; optional configs appear in consumed snapshots when used. | Checkout branch `slice-1b-compute-cache`; not a claim of remote or deployment parity. See `culture/model_versions.py`, `culture/rules.py`, `culture/records.py`, and `culture/schema.json`. This row makes no blanket claim about legacy reader compatibility. |
| v0.4 product site | Product/evidence presentation; page displays stored examples and generated evidence | Site label v0.4. Generated metadata identifies local source at build time: `rules_v0.7`, schema `0.8`; individual historical readings retain schema `0.4` and `decided_by: rules_v0.5`. The separate illustrative review uses schema `0.8`. | Example records preserve model IDs/hashes and config hashes from their original runs; they are not live inference. The fictional review extends a copy, not the source log. | `site/`; deployment mapping is in [`deploy/README.md`](../../deploy/README.md). This site is not an analysis endpoint; local build metadata does not establish deployed identity. |
| Review console source and local generated Space tree | Interactive demo source; local Analyze path runs submitted images, while examples/replays are stored/replayed. Local tree is generated from root library/config plus `demo/` by `deploy/sync_space.py`. | Current local library rules `rules_v0.7`; `RecordWriter` emits schema `0.8`. The local Space README distinguishes current source from historical examples; it does not establish remote identity. | Same model IDs as the local library; runtime weight/config hashes depend on deployment. Optional fine-tuned comparison is demo-only and decides nothing. | Root `demo/app.py`/`demo/analysis.py`; console entry point `deploy/hf-space-demo/console.py`; copied code/config and untracked demo assets are produced by `deploy/sync_space.py`. Remote Space revision/parity is unverified here. |
| Local API source and generated pipeline tree | Local FastAPI API source plus generated `culture/`, `config/`, `configs/` copies. | `deploy/hf-space/api.py` explicitly returns schema `0.2`; current generated library files in that folder do not prove the endpoint uses the current record contract. | Generated model/config copies follow root only after sync; exact remote bundle is unknown. | `deploy/hf-space/api.py` and generated directories. Do not treat this local API source as a v4 endpoint or infer remote behavior from it. |
| Remote API Space | Remote service is described in repo docs as the v0.2 API, but its currently running revision and response schema have not been verified here. | Unknown live revision/schema. Local source's schema `0.2` is not evidence of the remote's present state. | Unknown live model/config identities until revision and runtime manifest are recorded. | Remote URL and project are listed in [`deploy/README.md`](../../deploy/README.md); verify immutably before relying on it. It is not a v4 integration endpoint. |
| Raw model demo | Separate legacy/frozen demo surface, not the review console | No current host record contract is claimed | Historical demo config/weights; exact live revision/hash not verified | `deploy/hf-space-demo/app.py` and `LongGrainRice/cultureqc-demo` in the local deployment map. |
| Stored site artifacts and older records | Historical evidence, not a release candidate or current-policy replay | Concrete example: `site/src/data.json` item `evican_ht29` stores schema `0.4`, `decided_by: rules_v0.5`; generated dataset metadata says schema `0.5` / `rules_v0.5`. | Preserve model/config identities recorded in each canonical record; never substitute current defaults. | `site/src/data.json`, source examples under `demo/examples/`, and original record-generation evidence. A stored result does not become current behavior when site code changes. |
| Experimental fine-tuned comparison | Limited research/demo comparison; does not decide | Separate demo path, not a new product policy/schema | `mcellseg_ftF_r2`; weights are private and downloaded only when the configured optional path is enabled | `docs/FINE_TUNING.md` and `configs/finetuned_models.yaml`; not a supported production model. |

`rules_v0.7` emits advisory policy results; no returned action authorizes a host
operation. Shipped calibration profiles remain measurement-only for automatic
passage. A host controls identity, access, signatures, scheduling, retries,
durable retention, configuration approval and any physical action. See
[`host_platform.md`](../host_platform.md) and its linked policy contracts.

## Component terms and commercialization gate

The repository's MIT licence applies to the repository code. It does not grant
commercial rights to every model, model weight, dataset, derived artifact, or
deployment dependency. The component-by-component evidence and known unknowns
are listed in [README: Licences and commercial use](../../README.md#licences-and-commercial-use).
That inventory reports unresolved restrictions; it is not legal advice or a
new legal conclusion based only on upstream dataset licences.

The documented pipeline is **not cleared for commercial use pending review**.
The owner-held gate includes at least the Cellpose-SAM weights used for every
confluency reading, the QC weights/data lineage, and the MSC calibration source
if that profile is in scope. The fine-tuned Cellpose path inherits the
Cellpose-SAM issue. DINOv2's terms do not resolve these other components.

| Gate role | Responsibility | Evidence to close |
|---|---|---|
| Repository/product owner | Name the accountable rights reviewer; choose either a documented clearance route or replacement model/data plan; define intended commercial scope | Written decision tied to specific model/checkpoint hashes, datasets and intended use; any licence/permission instruments; recorded exceptions and prohibited uses |
| Rights reviewer / counsel (owner-appointed) | Review rights and provenance for each shipped and optional component, including training data and derived weights | Written component-level assessment with citations to authoritative licence/permission sources and an explicit commercial-use conclusion or conditions |
| Model/release owner | Map the reviewed artifacts to the exact runtime bundle and remove or disable components outside the approved scope | Reproducible manifest of code commit, model hashes, configs and dataset-derived artifacts; verification that the deployed bundle matches the reviewed manifest |
| Host/evaluation owner | Confirm partner data rights, permitted purpose, retention and evaluation environment | Signed evaluation terms and data/retention instructions; host-specific approval and validation records |

No owner/reviewer assignment or closing evidence is recorded by this document.
An evaluation may proceed only within its separately agreed data, purpose and
deployment constraints; this page does not grant commercial clearance.

## Reconciliation plan (no remote actions)

1. The repository owner records the intended canonical source branch and commit
   for each release, and confirms the default branch and protected-branch rules.
2. Compare that source commit with the Vercel production branch and each Hugging
   Face Space revision. Record immutable commit/revision IDs, build timestamps,
   config/model hashes and runtime schema/policy IDs in a release manifest.
3. For the console Space, run `python deploy/sync_space.py --check` against the
   selected source revision; resolve generated-copy drift through the script,
   then review the exact resulting diff. Do not treat this local check as remote
   verification.
4. For the v0.2 API/site and raw demo, document whether each remains archived,
   is retired, or receives a separately approved update. Preserve v2 behavior
   and historical records unless an explicit migration plan is approved.
5. Reconcile recorded site examples against their source records and hashes;
   retain original schema, rules, model and config identities. Any regenerated
   artifact is labelled with its actual generating revision and policy.
6. Publish only after owner approval of the exact source revision, manifest,
   compatibility/migration plan and rights gate. This checklist authorizes no
   merge, tag, setting change, upload, deployment or publication.

## Vocabulary

- **Current source** means the implementation in the named local repository
  revision, not an assertion about a remote service.
- **Deployed** means a service revision verified against a recorded immutable
  source/build identity; a URL or workflow configuration alone is insufficient.
- **Live output** means inference executed for the current submitted image.
- **Stored output** means a previously generated record or site artifact shown
  without recomputing its original inference.
- **Replay** means a deterministic presentation or reconstruction from stored
  inputs/results; it is not a new model measurement.
- **Experimental** means exploratory and outside supported decision use.
- **Legacy** means retained for historical compatibility and not the current
  integration contract.
