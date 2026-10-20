# I3 — Evidence and integration drilldowns

Dependency: C0. Owner: evidence/integration builder. May run alongside I1 → I2.

Execution status: implemented 2026-10-16; source audit, build, scoped regression and record interaction checks pass. Full independent/visual gates remain pending. See the [I3 handoff](../../reviews/2026-10-16-i3-proof-handoff.md).

Owned files: `site/src/pages/ValidationPage.jsx`, `site/src/pages/RecordsPage.jsx`, `site/src/components/Sections.jsx`, `site/src/components/Profiles.jsx`, `site/src/components/DenseTest.jsx`, `site/src/components/Records.jsx` only where this scope requires changes. Preserve shared exports used on Home. Do not edit global CSS, Shell or Journey; request changes from I2. No backend/schema changes.

Scope clarification, 2026-10-16: the orchestrator also aligns description/Open Graph metadata in `site/validation.html` and `site/records.html`; metadata must not repeat the scientific or review-event overclaims removed from those pages. No route or evidence contract changes.

Owner-directed refinement, 2026-10-17: lead Evidence with measured fine-tuning gains and audit inspection; remove the public architecture V1–V10 catalogue/tally. Preserve the source reports and material adverse findings, put full scientific tables behind labelled disclosures, and retain `#checks` as a legacy destination for detection scope. This supersedes retaining that catalogue in item 5, not the prohibition on misrepresenting adverse evidence. See [capabilities and thresholds review](../../reviews/2026-10-17-capabilities-and-thresholds.md). No model or threshold change follows from this presentation update.

## Implementation

1. Audit the evidence page's opening and headline summaries as well as its tables. Pair each highlighted finding with dataset, protocol, n, source and material limitation at the point of claim. Do not let a qualified lower section excuse an overclaiming hero.
2. Keep calibration improvements distinct from release comparisons and from experimental fine-tuning. Qualify broad held-out/blindness wording using each actual source. Surface insufficient dense-range evidence wherever an aggregate result might imply readiness near passage.
3. Keep the record explorer's exact ID selection, query preservation, verifier, tamper/reset and canonical-byte handling. Explain compactly what integrity establishes and what it cannot. The historical chain has no review event. T12 adds a separate, explicitly illustrative extension linked to HT29; never imply a real review, signature or approval occurred.
4. Make `/records#integration` explain inputs, current Python callable, outputs and host-owned work before specialist implementation detail. Check any snippet against the current function signature and `docs/host_platform.md`; it must not promise a live HTTP endpoint or durable host integration that is absent.
5. Preserve all section IDs and drilldowns. Do not remove adverse evidence to simplify the pitch. Keep license/commercial and production limitations accessible in the evaluation/technical path.

## Acceptance

- **I3-A:** Every prominent scientific number has an audit entry: page/claim → repository source → protocol/n → qualification. Source disagreement is reported, not patched by editing results.
- **I3-B:** C0's prohibited claims are absent; experimental output is not represented as driving shipped decisions. Neither a green check nor successful verification implies biological safety or compliance.
- **I3-C:** Opening the record link from each primary example selects that exact record. Tamper changes only local display state; Reset restores verification of original bytes. Verifier failure cannot report success.
- **I3-D:** The integration call is consistent with actual code; host ownership of capture, scheduling, identity/signatures, retention and actuation is explicit. No added external service or model run is necessary to read this page.
- **I3-E:** Existing component exports/anchors remain compatible with Home. Page-local improvements do not change global styling underneath I2.

Handoff: changed paths, source-to-claim ledger for V1, checks performed, and any homepage copy suggestions delivered to I2. New scientific evidence is outside this node.
