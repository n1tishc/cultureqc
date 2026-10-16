# Evidence and reproduction log for the VP review

Date: 2026-10-15. Checkout: `confluency-evidence-v2`, `2cd691a158bcffad7d283fea5b8aa6629665246b`, plus existing working-tree edits. Parent: [review](2026-10-15-v4-vs-v2-vp-review.md). Remediation: [tickets](2026-10-15-v4-vs-v2-agent-backlog.md).

## Evidence classification

- **Reproduced:** executed locally during this review, with outputs below.
- **Source-confirmed:** follows from the cited current code or committed report; not a newly executed scientific experiment.
- **Observed live:** browser interaction with the published site on the review date. Local uncommitted edits are not assumed deployed.
- **Judgment/proposal:** VP interpretation, priorities, proposed policy changes and pilot design. These are not measured improvements or descriptions of the VP's actual opinion.

## Existing validation executed

From repository root:

```bash
.venv/bin/python -m pytest tests/test_rules_band.py tests/test_rules_anomaly.py tests/test_profiles_config.py tests/test_approvals.py tests/test_records_chain.py tests/test_record_events.py tests/test_console_cards.py tests/test_claims.py tests/test_readme_provenance.py -q
npm run build
node --test site/tests/verify.test.js
.venv/bin/python deploy/sync_space.py --check
```

Results: **120 Python tests passed in 24.17 s**; site production build passed; **2 JavaScript verifier tests passed**; generated Space copies match root `config/`, `configs/`, `culture/` for both Spaces.

This was a targeted review suite, not the full repository suite. No GPU inference, notebook retraining, remote deployment, or regeneration of benchmark results was performed. The build output is not a deployment. Existing scientific results and Space timing reports were read, not reproduced.

## Additional probes: observed results

| Probe | Actual result | Meaning / ticket |
|---|---|---|
| Current `msc_phase`, reading 90%, target 80%, 48 h since passage | `passage`, despite A2/A3/A4 being `not measurable` | Calibration status and passage eligibility are conflated; T03 |
| Reading 90%, band 5 pp, quality/anomaly unavailable | `passage` | Missing checks are not automatically blockers; policy must define required checks; T04 |
| NaN reading | `continue`: “Confluency nan% below target 80%. No action needed.” | Invalid number falls through to normal action; T04 |
| Reading 95%, target 80%, only 6 h since passage | `continue`: “Confluency 95.0% below target 80%. No action needed.” | Action avoids passage, but reason states a false comparison; T04 |
| Two writers initialized before either writes, then one append each | `verify_chain.ok=False`, status `broken`; second record's predecessor mismatches first record | Ordinary interleaving breaks the chain; T08 |
| TIFF with uint16 values 4095 | Decodes as uint8 maximum 15 under current pipeline read flag | Unsupported encoding silently changes intensity scale; T09 |
| Load A; replace its file with B and approve B; next reading | One model construction; output still A; check advertises B's new SHA-256 with success | Hash check describes disk file, not cached model that ran; T06 |
| Latest approval has `effective_from=2099-01-01T00:00:00+00:00` | `check(...).status == "match"` now | Effective timestamp is ignored; T07 |
| Stubbed full `analyze()` with MSC reading 90%, no anomaly banks | `passage`; quality gate null, anomaly unavailable; target/timing/line config/map hash absent from returned record | Confirms the public pipeline behavior and provenance omission without model variability; T04/T05 |

The model replacement probe uses small files and a deterministic stand-in loaded model. It tests the real singleton/approval lifecycle, not Cellpose's numerical accuracy. The pipeline probe stubs expensive model outputs and leaves the actual rules/record construction active.

## Re-run all nine probes without downloading weights

Run from repository root in the existing environment. This creates temporary files outside the repo and deletes them on exit. It deliberately observes current behavior rather than asserting that the behavior is correct. After a fix, expected outputs should change and permanent regression tests should assert the new contract.

```bash
PYTHONPATH=. .venv/bin/python - <<'PY'
import json
import tempfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import cv2
import numpy as np

from culture import approvals, pipeline, seg
from culture.anomaly import AnomalyResult
from culture.profiles import get_profile
from culture.records import RecordWriter, change_event, hash_file, verify_chain
from culture.rules import LineConfig, decide


def show(name, value):
    print(json.dumps({"probe": name, "result": value}, sort_keys=True))


arguments = dict(confluency_confidence=0.9, qc_flag=None, qc_confidence=None,
                 line_config=LineConfig(), hours_since_passage=48)
msc = get_profile("msc_phase")
show("msc_missing_dense_validation", {
    "acceptance": msc.entry["acceptance"],
    "decision_at_90": decide(90, band_pp=msc.band_pp, **arguments),
})
show("unavailable_checks_allow_passage", decide(
    90, band_pp=5, quality_passed=None, anomaly_flag=None, **arguments))
show("nan_reading", decide(float("nan"), band_pp=5, **arguments))
show("recent_passage_reason", decide(
    95, 0.9, None, None, hours_since_passage=6, band_pp=5))

with tempfile.TemporaryDirectory(prefix="cultureqc-vp-review-") as directory:
    root = Path(directory)
    log = str(root / "interleaved.jsonl")
    writer_first = RecordWriter(log)
    writer_second = RecordWriter(log)
    writer_first.append({"record_type": "reading", "value": 1})
    writer_second.append({"record_type": "reading", "value": 2})
    result = verify_chain(log)
    show("two_writers", {
        "ok": result.ok, "status": result.status, "reason": result.reason,
    })

    image_path = str(root / "12bit.tif")
    cv2.imwrite(image_path, np.full((16, 16), 4095, dtype=np.uint16))
    decoded = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
    show("12bit_image_decode", {
        "original_max": 4095, "decoded_max": int(decoded.max()),
        "decoded_dtype": str(decoded.dtype),
    })

    weights_path = root / "weights"
    approvals_path = str(root / "approvals.jsonl")
    weights_path.write_bytes(b"old")

    def approve(effective_from=None):
        event = change_event(
            "model", None,
            {"id": "cpsam_v2", "sha256": hash_file(str(weights_path))},
            "probe", [{"path": "probe", "sha256": "0" * 64}],
            "probe", "probe", effective_from=effective_from,
        )
        RecordWriter(approvals_path).append(event)

    class ModelStandIn:
        def __init__(self):
            self.pretrained_model = str(weights_path)
            self.loaded_bytes = weights_path.read_bytes()

        def eval(self, image, **kwargs):
            probability = np.full(image.shape, 2 if self.loaded_bytes == b"old" else -2)
            return np.zeros(image.shape), [None, None, probability], None

    approve()
    with patch.object(approvals, "APPROVALS_PATH", approvals_path), \
         patch.object(seg, "_cp_model", None), \
         patch.object(seg, "_new_model", side_effect=ModelStandIn) as factory:
        before = seg.cpsam_confluency(decoded)
        weights_path.write_bytes(b"new-longer")
        approve()
        after = seg.cpsam_confluency(decoded)
        show("approved_weight_swap", {
            "before_pct": before.pct, "after_pct": after.pct,
            "loaded_models": factory.call_count,
            "advertised_new_hash": after.extra["model_check"]["sha256"] == hash_file(str(weights_path)),
            "still_loaded_old_bytes": seg._cp_model.loaded_bytes == b"old",
        })
        approve("2099-01-01T00:00:00+00:00")
        show("future_approval", approvals.check(
            "model", "cpsam_v2", str(weights_path)).status)

    confluency = SimpleNamespace(
        pct=90.0, confidence=0.9, method="probmap", model_version="stand-in",
        extra={"pct_default_cutoff": 90.0, "model_check": {"status": "stand-in"}},
    )
    qc = SimpleNamespace(flag="normal", confidence=0.9, evidence_bbox=None,
                         calibrated=True, model_version="stand-in")
    with patch.object(pipeline, "cpsam_confluency", return_value=confluency), \
         patch.object(pipeline, "qc_classify", return_value=qc), \
         patch("culture.anomaly.score_frame", return_value=AnomalyResult(
             status="unavailable", reason="probe")), \
         patch("culture.weights.weights_hashes", return_value={}):
        record = pipeline.analyze(
            image_path, profile_id="msc_phase", hours_since_passage=48,
            hours_since_feed=12, log_path=str(root / "reading.jsonl"),
        )
        show("pipeline_record_inputs", {
            "action": record["recommended_action"],
            "missing_fields": [key for key in (
                "target_confluency", "hours_since_passage", "hours_since_feed",
                "line_config", "confluency_map_hash") if key not in record],
            "quality_gate": record["quality_gate"],
            "anomaly_status": record["anomaly_status"],
        })
PY
```

## Source-confirmed findings not presented as new runtime tests

| Finding | Primary location | Scope |
|---|---|---|
| Profile/config approval checks explicitly absent | `culture/approvals.py:18` | Existing documented boundary; enforcement is proposed work |
| Profile cache only keyed by path | `culture/profiles.py:71` | File mutation after first load is not invalidated |
| Config hashes computed from files at record construction | `culture/pipeline.py:23`, `culture/pipeline.py:212` | Can diverge from cached/runtime-selected configuration |
| Host capture time not accepted by library API | `culture/pipeline.py:40`, `culture/pipeline.py:175` | Timestamp is set after inference |
| Public API intentionally remains v2 | `deploy/README.md:5` | Deliberate deployment state, not an accidental outage |
| Existing chain checkpoint limits accurately documented | `culture/records.py:25` | Do not report the earlier checkpoint problem as unfixed |
| Current README says Analyze has no quality gate | `README.md:429` versus `demo/analysis.py:112` | Stale text: configured C2C12 gate runs; many other profiles have none |
| Product brief still positions demoted classifier boxes as central | `docs/PRODUCT.md:23` | Stale agent direction, not current shipped behavior |
| Dense decision coverage poor despite useful MAE gains | `results/confluency_mcellseg_swap.md:162` | Existing secondary research evidence, not a new deployed comparison |
| Real-size simulated contamination near chance | `results/contamination_scale.md` | Existing limitation; no new detector run performed |
| Commercial-use clearance unresolved | `README.md:574` | Repository's own status, not a new legal opinion |

## Browser and design evidence

Published surfaces inspected: [v4 home](https://cultureqc-cvoy.vercel.app), [records](https://cultureqc-cvoy.vercel.app/records), [release notes](https://cultureqc-cvoy.vercel.app/release-notes), [v2 home](https://cultureqc.vercel.app), and [review console](https://huggingface.co/spaces/LongGrainRice/cultureqc-console). The source branch and calibration evidence links also loaded.

- Live homepage stage “verify the chain” click navigated to `/#records` but stayed on the home page. Source: `Stage.jsx:331`; mount-only migration effect: `Home.jsx:75`.
- Records page verified 9/9 records. The “Change one number in record 5” control made both chain-alone and checkpoint verification fail; the explanation identified records 5 and 6. Reload restored baseline.
- The interactive chain contains seven readings and two changes; no review event. Schema difference (current 0.5 versus stored 0.4) is disclosed, not hidden.
- The v2 page still functions as a full product with upload/contamination presentation and no visible supersession notice or v4 return link. Do not silently change the preserved v2 deployment; this is a release-communication issue for owner review.
- At the observed desktop viewport, action and record fell below the opening view. At verified 390×844 CSS viewport, page width was 390 (no document overflow); horizontally scrolling navigation makes release-note discovery less immediate. Do not report invented overlap bugs.
- The console loaded its Running/ZeroGPU interface, stored examples and fine-tuned examples. No live Analyze inference was triggered for this review.

Independent UI Assessment A scored the persuasion/evaluation surface 23/36 using the Impeccable heuristics. Assessment B's `impeccable detect --json site/src` returned exit 0 with **21 advisories** in `site/src/styles.css`:

- `design-system-font-size` (6): lines 181, 351, 362, 2023, 2341, 2876.
- `design-system-color` (15): lines 408, 541, 1346, 1365, 1464, 1563, 1568, 1569, 1641, 1642, 1811, 1812, 2548, 2762, 2870.

These advisories are design-token/document consistency checks. Black masks/contours, syntax colors and meaningful state colors are potential false positives or justified exceptions. They do not justify distracting agents from the decision/provenance gaps.

Browser-overlay limitation: mutable-page preflight succeeded, but the Impeccable live server timed out starting. Cleanup reported no running live server; no detector overlay was injected. Assessment B's screenshot capture timed out, so it used semantic snapshots, viewport measurements and actual navigation. Assessment A separately inspected rendered screenshots. No overlay should be claimed as visible to the user.

## Changes deliberately not made during this review

No product code, rules, profiles, schemas, historical records, benchmark outputs, source branch settings, external websites or deployments were modified. Existing working-tree changes were retained. The only intended repository additions are the three review Markdown files in this directory; build output is generated/ignored. Reproduction files live in temporary directories, not production logs.
