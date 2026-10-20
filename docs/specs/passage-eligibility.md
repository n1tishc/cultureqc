# Passage eligibility — rules_v0.6

The scope gate below is retained in rules_v0.7. Its additional missing-check,
timing and advisory-only behavior is specified in
[missing checks and timing](missing-checks-and-timing.md).

## Policy boundary

This is a new conservative product policy, not a reinterpretation of the old
preregistration. A fitted measurement band and `status: validated` are not
authorization to recommend passage. No shipped profile is currently eligible.

Three concepts are separate:

1. Measurement: cutoff, band, historical acceptance status and
   `measurement_calibrated`. Numerical calibration remains usable for research.
2. Validated operating scope: `validated_scope`, null until explicitly approved.
3. Action approval: `action_eligibility` with status, reason and, for eligibility,
   a nonempty host approval reference. A1–A5 must all pass; “not measurable” is
   insufficient. Passing criteria alone does not generate approval or scope.

## Scope contract

An eligible scope contains exactly `setup_id`, `cell_line`, `model_sha256`,
`reading_range_pct` and `target_range_pct`. Ranges are inclusive, ordered finite
percentages in 0–100. The model hash is the loaded inference artifact's SHA-256,
not a later read of the model file. The host's setup ID must resolve to a
versioned, change-controlled microscope/objective/modality/pixel-scale/capture
and preprocessing configuration. The library cannot independently verify that
the host's claimed identity describes the image; this remains a host duty.

`culture.pipeline.analyze(..., setup_id=...)` and
`demo.analysis.analyze_image(..., setup_id=...)` compute the same scope check.
The console has no host-attested setup input and therefore cannot accidentally
select itself into approval. Direct rule callers must pass both `profile` and
`setup_context`; the supplied band must equal that profile's active band.

The evaluated `passage_eligibility` record stores eligible/reason plus setup,
cell line, loaded model hash, reading and target. It describes one request,
not unconditional permission to passage. QC, image-quality, anomaly, band and
timing rules still apply. JSON schema requires these fields for rules_v0.6
while accepting historical records without them.

## Migration

- Generated profile config advances to version 2; all current entries explicitly
  carry null scope and unsupported eligibility. The generator cannot fabricate
  an approval from historical scores. Future approved scopes need a reviewed
  source of configuration; do not hand-edit generated output to enable them.
- Legacy version-1 entries load measurement-only when action metadata is absent.
- Unknown explicit IDs (including empty strings) raise `ValueError`; only `None`
  selects the generic uncalibrated profile. Invalid status/value combinations,
  bands and scopes fail on load, not silently during inference.
- Profile hashes change because new policy metadata is pinned. Deploy under
  host change control; restart workers to load configuration. Do not rewrite
  historical records, change events, examples, model outputs or result files.
- Historical demo examples retain rules_v0.5 and their original profile hashes.
  The console labels them historical policy replays, not current authorization.
- New live records retain schema version 0.5 with additive fields conditional on
  rules_v0.6. Consumers enforcing the old closed schema must update first.

## Synthetic example and acceptance

`tests/conftest.py::synthetic_passage_profile` is an invented approval/scope for
rule tests only. It proves software behavior, not biological suitability.
`tests/test_passage_eligibility.py` covers the MSC 90%/80% regression, approved
synthetic passage, scope misses, malformed configs, unsupported legacy profiles,
input bounds, schema requirements and library/console record parity.

## Deliberately not claimed

This does not validate contamination or growth-stall detection, make missing
quality/anomaly/timing checks acceptable, or make `feed`/`continue` host-actionable.
Those failure semantics are now implemented by T04 in rules_v0.7. Full decision reconstruction is T05;
authenticated/transactional configuration activation is a separate gate. An
approval reference here is not cryptographically checked against an approval
service. No clinical, biological or operational validation is supplied by this patch.
