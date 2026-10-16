---
version: 1
slug: "site-src-pages-home-jsx"
primary_target: "site/src/pages/Home.jsx"
related_targets: ["site/src/components/Stage.jsx", "site/src/components/Journey.jsx", "site/src/components/Shell.jsx", "site/src/styles.css", "site/src/components/GuidedStage.css"]
---

# site/src/pages/Home.jsx — v2 to v4 VP journey

Scope: current public React site. Visitor mode: **Persuade**, supported by inspectable evidence and record tools. This brief supersedes the page strategy in `site-src-app-jsx.md`; that file remains historical context for the v0.3 site. The incumbent category-standard visual world in `docs/DESIGN.md` still governs tokens, type, color and microscopy stages. No rebrand is approved.

Audience: a returning lab-automation VP who saw v2 and needs to decide whether to sponsor a bounded evaluation on one imaging setup. Job: understand what v4 changed, why the recommendation follows from the stored measurement, where the evidence stops, and what the proposed pilot requires. Primary action: walk through the evidence. Closing action: review the pilot plan. The live console is optional corroboration.

Proof: the site displays generated data from `site/src/data.json`, backed by source results and stored records. The three guided cases are EVICAN HT29 (human review at a target-crossing setup error band), EVICAN PC3 (stored continue recommendation, not universal clearance), and C2C12 oversized synthetic contamination stress test (re-image from the image-quality gate, not a realistic contamination success). All seven stored examples remain inspectable with their computed layers. Each selected reading links to its exact `/records?record=<id>#chain` destination. The records page verifies the chain and checkpoint and provides a reversible local tamper demonstration. Live output is always labelled separately from stored output.

Constraints: no fabricated matched v2/v4 accuracy comparison, action validation, human-review event, ordinary contamination vignette, ROI, commercial clearance or host actuation. Show setup-level error as an estimate from held-out images, not the known error of this frame. Fine-tuned readings are experimental and decide nothing. The EVICAN evaluation is mixed-setup and not fully blind; its anomaly bank is not calibrated for those cell types. The C2C12 stress test used bacteria pasted at 16.5× real size. Preserve research scope and the shipped/experimental distinction at the point of use. Follow the [technical backlog](../../../docs/reviews/2026-10-15-v4-vs-v2-agent-backlog.md) for unresolved correctness work and the [five-minute script](../../../docs/DEMO_SCRIPT.md) for presentation order.

## Direction contract

THESIS: Move from an open-ended pipeline tour to an inspectable proposal for one-setup offline evaluation. Lead with the change since v2, then let the visitor test the decision boundary and trace a specific result.

OWN-WORLD: Keep the approved light reading surface, restrained scientific typography, hairline rules and dark microscopy stages. Cyan denotes segmentation, magenta denotes anomaly evidence, and action hues always accompany words and icons. Use real frames and source-labelled measurements; preserve the incumbent CSS tokens and components.

STORY: v2 established workflow and hash-chained readings; v4 adds real-image evaluation, setup calibration, measured uncertainty and stronger provenance. The guided HT29 → PC3 → re-image sequence explains the stored rule outcomes, then the exact record, the dense-range evidence limit and a pilot with partner/project responsibilities complete the five-minute path. Technical replay, architecture and full results stay available as drill-downs.

FIRST VIEWPORT: state the v2 → v4 proposition and give a compact path into the walkthrough. On the stage, present scenario, stored state, action and reason before optional mechanics. Keep the setup band or its absence, target, research scope and exact record reachable without inspecting raw model arithmetic. At 1280×800 retain image and summary together; on mobile place the result before advanced controls.

FORM: Persuade through a real instrument output and traceable evidence, not sales decoration. Use the approved site tokens in `docs/DESIGN.md`; source/protocol/n stay beside evidence. The core path has three scenario steps with next/back/reset and stable `?example=<id>#demo` links, while an advanced disclosure keeps layer toggles and the seven-example explorer.

FINISH: verify 1280×800 and 390×844 journeys, keyboard focus, URL back/forward, unavailable assets and verification failure, stored/live wording, exact record handoff and production build. Rehearse against `docs/DEMO_SCRIPT.md` without rewriting evidence claims. Existing `docs/DESIGN.md` and `.impeccable/design.json` are historical design-system artifacts; report drift for a separately approved scan rather than changing tokens during this content handoff.
