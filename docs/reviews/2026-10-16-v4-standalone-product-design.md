# cultureQC: standalone product-site design proposal

Date: 2026-10-16. Status: **direction approved by owner; implementation specifications prepared**. Execute via the [implementation DAG and packets](../specs/standalone-product-site/README.md). The website has not yet been changed to this direction.

The owner rejected comparison-first storytelling. That decision supersedes the narrative and information architecture in the [previous upgrade plan](2026-10-15-vp-demo-upgrade-plan.md) and backlog T01. This document proposes the replacement. Implementation history, scientific findings and correctness tickets remain valid. No UI changes, new results, deployment or readiness claims follow from this proposal.

## 1. The correction

**Present cultureQC as a useful product, not a report about how its developers improved it.** A VP should understand the product without knowing v2 existed. Improvement should be felt through a clearer workflow, a convincing interactive result and a credible integration boundary—not through a before/after table.

The current implementation puts release comparison ahead of microscopy, invites visitors to walk through evidence rather than experience the product, and makes edge-case-oriented examples the main narrative. Lengthy record explanations and pilot qualifications can make the homepage feel like a technical defense. These are hierarchy problems, not reasons to suppress limitations or invent stronger results.

Keep the analysis, exact-record handoff, verification tools and visual identity. Recompose the page around their usefulness. Version comparisons remain optional release-history/internal-evaluation material.

## 2. Lessons from online references

Method: first-party page text and image descriptions, not rendered visual or conversion testing. See the [four-product research note](2026-10-16-product-site-reference-research.md). These are observed patterns; their suitability for cultureQC is our design inference.

| Reference | Observed pattern | Proposed adaptation |
|---|---|---|
| [Benchling](https://www.benchling.com/product-overview) | Product proposition, immediate demo path, workflow-specific detail | One understandable promise and an early working example |
| [Automata LINQ](https://www.automata.tech/linq) | Connects hardware, software and integration boundaries | Explain where cultureQC sits inside a host system |
| [CellXpress.ai](https://www.moleculardevices.com/products/3d-biology/cellxpress-ai-automated-cell-culture-system) | Product imagery and culture workflow before specifications | Real microscopy and its result dominate the demonstration |
| [Incucyte software](https://www.sartorius.com/en/products/live-cell-imaging-analysis/live-cell-analysis-software) | Analysis workflow and demo; release updates later | Analysis experience first, release history last |

[NN/g's progressive-disclosure guidance](https://www.nngroup.com/articles/progressive-disclosure/) supports keeping essential information visible while making specialist detail available on demand. Here, output scope and missing calibration are essential; model arithmetic and full hashes are specialist detail.

Do not borrow enterprise logos, autonomous hardware promises, customer outcomes, labor savings or compliance claims. None is earned by adopting a polished layout.

## 3. Positioning and first impression

Audience: a lab-automation VP assessing usefulness, fit and the next investment, plus scientific and engineering reviewers needing inspectable detail.

Recommended opening copy:

> **Read the culture. Understand the next step.**
>
> cultureQC turns a microscopy image into a confluency measurement, a rule-based recommendation and a traceable record for your team to review.

Primary action: **Explore an analysis**. Secondary: **See how it fits**. Closing action: **Evaluate on your setup**, linking to the actual offline evaluation proposal—not an unconnected sales form.

Keep a concise “Research demo · stored analysis” label in the stage. Neither a release number nor a wall of disclaimers should be the headline. Attach important limitations to the result or claim they qualify.

## 4. Proposed homepage

Navigation: **Product · Evidence · Integration**, plus **Evaluate on your setup**. Product links to the stage; Evidence to `/validation`; Integration to `/records#integration`; evaluation to `#pilot`. Records remain one click from every result. Release notes go in the footer. Preserve old URLs and anchors.

```text
Logo       Product / Evidence / Integration       Evaluate on your setup

Read the culture. Understand the next step.
One short explanation. Two useful actions.

┌────────────────────────────────┬───────────────────────────┐
│ Actual microscopy              │ Selected sample / Stored  │
│                                │ Confluency measurement    │
│ Raw image ↔ segmentation       │ Recommendation + reason   │
│                                │ Calibration / scope       │
│                                │ Inspect this record       │
└────────────────────────────────┴───────────────────────────┘
Measure coverage / Understand a review boundary     More examples

Measure what is there → Understand the recommendation → Trace the result
Designed to fit your workflow: host → cultureQC → host
Evidence for this setup: finding + qualification + source
Evaluate on your setup: inputs / outputs / decision gate
Footer: documentation / records / release history
```

The top stage is the actual reusable product interaction, not a decorative screenshot followed by another copy of the demo. Start it within the first desktop viewport; fit image and summary together at 1280×800. Show useful output before project history.

## 5. Signature interaction: one image, an understandable result

Use two task-labelled entry points, not a mandatory three-step wizard:

1. **Measure coverage.** Open the actual C2C12 mid-density stored example: 39.41% confluency. A raw/segmentation toggle makes measurement tangible. Display the stored recommendation and reason faithfully, with “No calibrated error band for this example” beside the measurement. Its normal-source label is not a health or contamination-clearance claim.
2. **Understand a review boundary.** Select the actual HT29 example: 52.91%, setup-level band 23.51–82.31%, target 80%, human review. Show the interval crossing the target on an annotated scale, with the rule's reason. This demonstrates the stored rule, not validated HT29 action performance; evaluation and anomaly-bank scope stay visible.

Each entry opens its exact record. Show compact provenance first; full hashes, chain verification and reversible local tampering stay in Records. Do not repeat the whole ledger on the homepage or imply a recorded human-review event exists.

All seven examples remain under “More examples,” including PC3 and synthetic stress tests. Remove the oversized-bacteria re-image case from the default story. A future ordinary image-quality vignette needs a real pipeline-produced fixture, image and record before promotion; it is not a frontend mock outcome.

No editable threshold or simulated live progression in this phase: these require genuine recomputation or an explicitly separate simulator. Different examples are not a time series from one vessel. Never invent a successful automatic-passage example to smooth the story.

## 6. Visual and interaction direction

**A precise scientific product, not a slide deck or generic AI landing page.** Preserve `docs/DESIGN.md` tokens: light reading surface, dark workspace, cyan segmentation, magenta anomaly evidence and labelled action colors. Improve composition rather than rebrand.

- Give microscopy the largest visual area; align the result panel with it instead of surrounding it with equal-weight cards.
- Use a strong editorial headline, short paragraphs, generous section spacing and tabular numerals. One dominant idea per section; no decorative KPI strip.
- Use short user-triggered overlay transitions and subtle selection feedback. No autoplay, scroll hijacking, fake scanning, count-ups or 3D microscope illustration. Respect reduced motion.
- Mobile order: headline, image, compact result, task selector, details. Action/reason precedes specialist controls; no horizontal result table or clipped navigation.
- Provide keyboard selection, visible focus, labelled controls, readable contrast and status text beyond color. Preserve predictable URLs, browser history and exact record selection.
- Handle unavailable image, failed overlay, invalid example and verification failure explicitly. A failed request must not silently substitute a different sample or success message. Stored output never impersonates live processing.

## 7. How this earns a VP's attention

| VP question | Product experience | Claim boundary |
|---|---|---|
| What does this do? | Image, segmentation and readable result immediately | Single-image analysis, not an autonomous lab |
| Where would it help? | Clear measurement and review-reason workflow | Time savings/review reduction are evaluation hypotheses |
| Could it fit our platform? | Host captures/context → cultureQC analyzes → host reviews/acts/retains | Designed boundary, not production integration |
| Can my team investigate? | Exact sample-to-record handoff | Integrity checks are not regulatory compliance |
| What investment comes next? | One-setup offline evaluation with agreed gates | Correctness and commercial clearance remain separate work |

Evidence supports rather than opens the pitch. Show dataset, protocol, sample count and relevant limit next to each finding. Do not headline MSC's overall calibrated error without its sparse dense-range evidence. Never rename within-protocol calibration gains as v2/v4 gains. Fine-tuning stays experimental and does not drive shipped recommendations.

The integration diagram shows the host owning capture, scheduling, identity, signatures, durable audit and physical actions. Ground any sample call in the current Python interface and `docs/host_platform.md`; do not advertise an invented current HTTP service or turnkey connector.

## 8. Five-minute presentation

| Time | Demonstration |
|---|---|
| 0:00–0:40 | Product promise and image; what enters and comes back |
| 0:40–1:40 | Coverage example; toggle segmentation and read output with scope |
| 1:40–2:30 | Review boundary; why a person remains involved |
| 2:30–3:15 | Follow the exact result to its record; optional verification |
| 3:15–4:10 | Host boundary and one evidence finding with qualification |
| 4:10–5:00 | Agree the one-setup evaluation question and inputs |

No version-comparison segment. Update `docs/DEMO_SCRIPT.md` after approval, preserving its technical appendix and unrelated user edits.

## 9. Bounded implementation handoff after approval

| Order / owner | Targets and deliverable | Acceptance |
|---|---|---|
| S1 — narrative/layout | `Home.jsx`, `Journey.jsx`, `Shell.jsx`, CSS, metadata | No homepage v2/v4 pitch; stage replaces comparison-first opening; coherent navigation/CTA |
| S2 — interaction | `Stage.jsx`, `GuidedStage.css`, scenario configuration/tests | Two task entries, truthful fields, raw/overlay, exact records, all examples retained; reuse mechanics |
| S3 — proof/integration | Evidence/records surfaces, `docs/DEMO_SCRIPT.md` | Contextual proof, honest host boundary, new five-minute script; no altered records/metrics |
| S4 — independent acceptance | Build/tests, desktop/mobile browser checks, timed walkthrough | Screenshots/checks at 1280×800 and 390×844; keyboard/reduced motion/error cases; source-to-result audit |

One frontend owner handles S1/S2 to avoid overlapping edits. An independent reviewer checks claims/tests; delegate bounded work only. Runtime T03–T09 remain separate; this redesign does not resolve them.

Success test: a fresh reviewer can explain what cultureQC does, why the recommendation appears, who retains control and what evaluation requires without hearing about v2. This is qualitative acceptance, not a conversion promise. If screenshots cannot be captured, visual acceptance remains pending.

**Approval recorded:** the owner accepted the product-first composition and two-task demonstration and requested implementable specifications and a DAG. The [execution packets](../specs/standalone-product-site/README.md) replace the coarse S1–S4 handoff above. This planning task does not claim UI implementation or acceptance is complete.
