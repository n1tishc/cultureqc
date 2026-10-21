# C0 — Shared contracts

Status: complete as a planning artifact. Applies to every node. Direction approved 2026-10-16; no UI work is claimed complete.

## Product and layout contract

- Hero: **Read the culture. Understand the next step.**
- Supporting copy: “cultureQC turns a microscopy image into a confluency measurement, a rule-based recommendation and a traceable record for your team to review.”
- Order: proposition → one actual image/result workspace → workflow usefulness → host boundary → scoped evidence → offline evaluation.
- Preserve the scientific visual world in `docs/DESIGN.md`: light reading surface, dark microscopy workspace, cyan segmentation, magenta anomaly evidence, labelled action colors. No rebrand, decorative KPI strip, fake scanning, autoplay, invented logos or ROI.
- Essential result scope stays visible, not inside a tooltip or closed disclosure. Hashes, model arithmetic and specialist layers may be secondary. Stored analysis never implies live inference or physical action.

## Data contract

Render numeric values, action/reason, image/layer paths and exact record identity from the existing example object. The following are acceptance fixtures, not permission to hardcode UI outputs:

| Task | Stored ID | Expected result and visible qualification |
|---|---|---|
| Measure coverage | `c2c12_normal_20_40` | 39.41%; stored continue recommendation; no calibrated error band; normal-source label is not contamination clearance |
| Understand a review boundary (default since 2026-10-20) | `evican_ht29` | 52.91%; band 23.51–82.31%; target 80%; human review; mixed-setup EVICAN calibration not fully blind, C2C12 anomaly bank not calibrated for HT29 |

All seven existing IDs remain selectable in More examples and by deep link. Keep synthetic/oversized labels and relevant restrictions with those examples. Never create a passage-success fixture, treat different images as a time series, change historical output or add a threshold slider that appears to recompute it.

Keep the `Stage` public props (`examples`, `verify`, `liveParity`, `verifyError`) and named exports used by other components unless all consumers are explicitly updated within the owning task. Do not move verification or source ownership into an unrelated new abstraction just for this redesign.

## Route and state contract

| Action or existing URL | Required destination/behavior |
|---|---|
| Product / Explore an analysis | `/#demo` (same-page `#demo` allowed) |
| Evidence | `/validation` |
| Integration / See how it fits | `/records#integration` |
| Evaluate on your setup | `/#pilot`; section contains an actual offline evaluation proposal |
| Inspect this record | `/records?record=<encoded example ID>#chain` |
| Release history | `/release-notes`, secondary/footer |
| `/?example=<valid ID>#demo` | Select that exact stored example, including advanced examples |
| `/#records`, `/#integration`, `/#validation`, `/#limits`, `/#confluency`, `/#changes` | Preserve current redirects to records/integration/validation checks/detectability/confluency/release notes |
| `/#timeline`, `/#accuracy`, `/#passage`, `/#specs`, `/#scope`, `/#how` | Preserve existing targets; open the technical disclosure when necessary |
| `/#top`, `/#evidence`, `/#pilot`, `/#trail` | Preserve meaningful destinations; `#trail` may become a compact records handoff, not the full ledger |

Preserve clean-route direct refresh for `/`, `/records`, `/validation` and `/release-notes`, existing `#main` skip links and `#model-terms`. Record-to-reading links must return to the exact example. Use `#fit` for any new inline host diagram; do not collide with the legacy `#integration` redirect.

Example selection preserves unrelated query parameters, writes history once on an actual change, and updates image, outputs and record link atomically. Browser Back/Forward restores selection. Reset returns to the default example and initial layer state even when already on that example. Absence of `example` means default; an invalid ID must visibly say it was unavailable and that the default is being shown. Never silently substitute an example. A failed asset retains the selected identity and shows retry, not another sample.

## Claim contract

- Calibration estimates measurement error; it does not establish action eligibility on a partner instrument. Continue is a rule result, not a healthy/clean/cleared badge.
- If shown, MSC 8.19 → 3.43 pp is within-protocol calibration on 320 images, not v2/v4 performance. Only four dense-range images; dense criterion unmeasurable. Verify protocol language against source before publication.
- Fine-tuning is experimental and decides nothing in the shipped workflow. No claim of reliable real contamination detection, autonomous passage, turnkey HTTP integration, regulatory compliance or commercial clearance.
- Host owns capture, scheduling, identity, signatures, durable retention and physical action. Hash-chain verification checks integrity, not scientific validity or compliance. Stored chain has readings and changes, not an actual human-review event.
- Current callable integration must match `culture/pipeline.py` and `docs/host_platform.md`. Do not revive historical API contracts as current services.

## Change control

Do not edit `site/src/data.json`, source metrics, records, weights, policy or generated files. If observed fixtures disagree with this packet, stop the affected claim and report the mismatch; do not edit the data to pass acceptance. Read the current working tree, not only HEAD, so unrelated local changes survive. Any contract change must be recorded here before dependent tasks consume it.

## Recorded change, 2026-10-20 (owner direction, VP readability)

- The default and first task is **Understand a review boundary** (`evican_ht29`); **Measure coverage** is second. Invalid IDs fall back to HT29 with the same visible notice.
- The hero drops the licensing line; the footer and `#model-terms` keep it. Repeated scope sentences are cut to one line per example; each example keeps its material limit beside the result.
- The homepage adds a cited problem statement (Jaccard et al., Biotechnol. Bioeng. 2014;111:504–517, doi:10.1002/bit.25115) ahead of Measure/Understand/Trace, and a second evidence finding: the fine-tuning within-5-points count, labelled experimental and non-deciding with its failed criteria beside it. All numbers are read from `data.json`.
