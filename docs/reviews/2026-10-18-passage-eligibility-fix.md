# T03 — measurement calibration is not passage authorization

## Finding and root cause

The exact MSC probe (reading 90%, target 80%, 48 hours since passage, band
7.11 percentage points) returned `passage` under rules_v0.5. Its profile had
A1/A5 passes and A2/A3/A4 “not measurable.” The generator enabled measurement
parameters when all measurable criteria passed; the rules then used the band
as sufficient decision evidence. No separate action scope existed in either
caller. This was a policy gap, not proof the original preregistration was violated.

The deterministic regression was run red before implementation:

```sh
.venv/bin/python -m pytest tests/test_passage_eligibility.py -q
```

It failed on `assert action == "human_review"` with actual `passage`.
The original direct-call probe now returns `human_review`, preserving the
MSC cutoff of -1.5, band of 7.11 and numerical reading.

## Implemented locally

- rules_v0.6 adds explicit passage eligibility; supplying only a measurement
  band can no longer authorize passage.
- Profiles separately record measurement calibration, validated decision scope
  and action approval. All generated production entries are unsupported for
  automatic passage. No experimental evidence or approval was invented.
- Eligible synthetic fixtures require all A1–A5 passes, approval reference,
  exact setup/cell-line/loaded-model identity and inclusive reading/target ranges.
- Malformed profiles, invalid numeric bands/ranges and unknown explicit IDs
  fail rather than silently looking like a configured request.
- Library and console record evaluated eligibility and context; schema requires
  these fields under rules_v0.6. Historical records remain schema-compatible.
- Console copy distinguishes calibrated measurement from action authorization;
  stored examples explicitly remain historical policy replays.
- Deployment mirrors are regenerated locally. No result files, historical
  examples, approval events, commits, remote branches or deployments are changed.

Migration and host responsibilities: `docs/specs/passage-eligibility.md`.

## Validation

```sh
.venv/bin/python -m pytest tests/test_passage_eligibility.py tests/test_rules_band.py tests/test_rules_anomaly.py tests/test_profiles_config.py tests/test_record_model_identity.py tests/test_demo_examples.py tests/test_console_cards.py tests/test_record_events.py tests/test_live_calibration.py tests/test_console_lab_demo.py -q
```

**156 passed.** Includes synthetic approved passage, unsupported MSC, setup,
cell-line and model mismatches, range boundaries, malformed configurations,
finite input checks, console messaging, historical example/hash preservation,
schema acceptance and library/console parity. Integration inference is stubbed;
these tests establish software behavior, not detector efficacy or biological safety.

```sh
.venv/bin/python -m pytest deploy/hf-space/test_api.py tests/test_console_zerogpu.py -q
```

**33 passed**, with two existing Starlette/httpx/AnyIO deprecation warnings.
Combined validation: **189 passed**. Model downloads and startup inference are
stubbed in the ZeroGPU contract tests; no remote deployment is exercised.

Compile checks, `git diff --check`, and `deploy/sync_space.py --check` pass.
`git diff --name-only -- results demo/examples` is empty. The real-Cellpose CPU
parity run from the preceding step is documented separately; it was not rerun
for this rules-only change.

## Remaining boundaries

- T04 still owns missing required checks, unknown/invalid elapsed times,
  timing-hold explanations and advisory `continue`/`feed` output.
- T05 still owns complete reconstructibility of all decision inputs.
- Setup identity and profile approval references are host-managed declarations;
  this change does not authenticate them or activate configs transactionally.
  Existing cached profiles require a worker restart after configuration changes.
- Future eligible deployment needs real labelled action-range evidence and a
  reviewed source of approved scopes; the historical-profile generator does not
  create that approval. Synthetic test profiles must never be deployed as evidence.
- Human screen-reader and actual 200% zoom verification remain pending. Console
  copy is tested as rendered HTML, not claimed as a new browser/accessibility pass.
- The design skill reported stale design-sidecar metadata; optional `document`
  refresh was not performed as an unrelated change.

**Next code task:** T04, required-check and timing semantics. Nothing pushed.
