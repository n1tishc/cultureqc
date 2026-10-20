"""Grouped cached workload replay, without treating model readings as truth."""

import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys

import pytest

REPO = Path(__file__).resolve().parents[1]
SCRIPT = REPO / "scripts/compare_c2c12_workload.py"
spec = importlib.util.spec_from_file_location("c2_workload", SCRIPT)
workload = importlib.util.module_from_spec(spec)
spec.loader.exec_module(workload)
BUNDLE = REPO / "results/policy_comparison_c2c12"


@pytest.fixture(scope="module")
def loaded():
    return workload.load_bundle(BUNDLE)


@pytest.fixture(scope="module")
def replayed():
    return workload.replay(BUNDLE)


def hashes(directory):
    return {str(path.relative_to(directory)): workload.common.digest(path)
            for path in directory.rglob("*") if path.is_file()}


def test_exact_replay_and_immutable_inputs(replayed):
    before = hashes(BUNDLE)
    decisions, report = workload.replay(BUNDLE)
    assert decisions == [json.loads(line) for line in (BUNDLE / "replay/decisions.jsonl").read_text().splitlines()]
    assert report == json.loads((BUNDLE / "replay/report.json").read_text())
    assert workload.markdown_report(report) == (BUNDLE / "replay/report.md").read_text()
    assert hashes(BUNDLE) == before
    assert report["n_unique_frames"] == 1228
    assert report["paired_context_rows"] == 4912
    assert report["n_sequences"] == 14
    assert report["n_experiment_groups"] == 3


def test_minimal_copy_needs_no_compute_cache_git_weights_or_root_configs(tmp_path):
    checkout = tmp_path / "minimal"
    for relative in workload.SOURCE_PATHS:
        target = checkout / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(REPO / relative, target)
    shutil.copytree(BUNDLE, checkout / "bundle")
    output = tmp_path / "output"
    process = subprocess.run(
        [sys.executable, str(checkout / "scripts/compare_c2c12_workload.py"),
         "--bundle", str(checkout / "bundle"), "--out", str(output)],
        cwd=checkout, env={"PATH": "", "PYTHONDONTWRITEBYTECODE": "1"},
        capture_output=True, text=True, timeout=30,
    )
    assert process.returncode == 0, process.stderr
    assert json.loads(process.stdout)["inference_run"] is False
    assert hashes(output) == hashes(BUNDLE / "replay")


def test_no_output_or_bundle_overwrite(tmp_path):
    with pytest.raises(ValueError, match="never overwrite"):
        workload.freeze(BUNDLE)
    with pytest.raises(SystemExit):
        workload.main(["--out", str(tmp_path)])
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize("artifact", workload.ARTIFACTS)
def test_artifact_drift_fails(tmp_path, artifact):
    bundle = tmp_path / "bundle"
    shutil.copytree(BUNDLE, bundle)
    with (bundle / artifact).open("a") as handle:
        handle.write("\n")
    with pytest.raises(ValueError, match="artifact mismatch"):
        workload.replay(bundle)


def test_source_drift_fails(monkeypatch):
    actual = workload.common.digest
    monkeypatch.setattr(workload.common, "digest",
                        lambda path: "0" * 64 if str(path).endswith("culture/quality.py") else actual(path))
    with pytest.raises(ValueError, match="source mismatch"):
        workload.replay(BUNDLE)


@pytest.mark.parametrize("field,value", [
    ("confluency_truth_pct", 50), ("split", "tuning"), ("kind", "contamination_onset"),
    ("experiment", "invented"), ("pct_cut0", float("nan")), ("frame_idx", -1),
    ("confidence_cut0", 2), ("anomaly_bin", "80-100"),
])
def test_relabelled_or_invalid_rows_rejected_even_with_updated_hash(tmp_path, field, value):
    bundle = tmp_path / "bundle"
    shutil.copytree(BUNDLE, bundle)
    rows = json.loads((bundle / "inputs.json").read_text())
    rows[0][field] = value
    (bundle / "inputs.json").write_text(json.dumps(rows))
    manifest = json.loads((bundle / "manifest.json").read_text())
    manifest["artifact_sha256"]["inputs.json"] = workload.common.digest(bundle / "inputs.json")
    workload.common.write_json(bundle / "manifest.json", manifest)
    with pytest.raises(ValueError):
        workload.load_bundle(bundle)


@pytest.mark.parametrize("field", ["quality_passed", "anomaly_flag"])
def test_gate_or_flag_cannot_be_changed_without_changing_observations(tmp_path, field):
    bundle = tmp_path / "bundle"
    shutil.copytree(BUNDLE, bundle)
    rows = json.loads((bundle / "inputs.json").read_text())
    rows[0][field] = not rows[0][field]
    workload.common.write_json(bundle / "inputs.json", rows)
    manifest = json.loads((bundle / "manifest.json").read_text())
    manifest["artifact_sha256"]["inputs.json"] = workload.common.digest(bundle / "inputs.json")
    workload.common.write_json(bundle / "manifest.json", manifest)
    with pytest.raises(ValueError):
        workload.load_bundle(bundle)


def test_current_quality_precedence_and_reasons(loaded):
    manifest, rows, baseline = loaded
    row = next(row for row in rows if not row["quality_passed"])
    outputs = workload.replay_outputs(row, manifest, baseline, 50, manifest["timing_scenarios"]["unknown"])
    assert outputs["current_configured"]["action"] == "reimage"
    assert outputs["current_configured"]["reason_code"] == "quality_failed"
    assert outputs["current_configured"]["host_actionable"] is False
    for reason in row["quality_reasons"]:
        assert reason.replace("_", " ") in outputs["current_configured"]["reason"]


def test_unknown_and_assumed_timing_keep_distinct_reasons(loaded):
    manifest, rows, baseline = loaded
    row = next(row for row in rows if row["pct_cut0"] >= 50 and row["quality_passed"])
    unknown = workload.replay_outputs(row, manifest, baseline, 50, manifest["timing_scenarios"]["unknown"])
    assumed = workload.replay_outputs(row, manifest, baseline, 50, manifest["timing_scenarios"]["assumed_elapsed"])
    assert unknown["current_configured"]["reason_code"] == "passage_time_unknown"
    assert assumed["current_configured"]["reason_code"] == "measurement_uncalibrated"
    assert unknown["current_configured"]["action"] == assumed["current_configured"]["action"] == "human_review"


def test_group_counts_add_to_pooled_and_empty_groups_have_null_rates(replayed):
    _, report = replayed
    for pooled in report["summaries"]:
        assert pooled["decision_accuracy"] is None
        assert pooled["confidence_interval"] is None
        assert sum(pooled["actions"].values()) == pooled["n_frames"]
        if not pooled["n_frames"]:
            assert pooled["review_fraction"] is None
        if pooled["group_kind"] != "pooled":
            continue
        for kind in ("sequence", "experiment"):
            grouped = [row for row in report["summaries"] if row["group_kind"] == kind
                       and all(row[key] == pooled[key] for key in ("target_pct", "timing_scenario", "subset", "variant"))]
            assert sum(row["n_frames"] for row in grouped) == pooled["n_frames"]
            for action in pooled["actions"]:
                assert sum(row["actions"][action] for row in grouped) == pooled["actions"][action]


def test_macro_rates_are_equal_group_not_frame_weighted(replayed):
    _, report = replayed
    for average in report["equal_group_averages"]:
        grouped = [row for row in report["summaries"] if row["n_frames"]
                   and all(row[key] == average[key] for key in ("target_pct", "timing_scenario", "subset", "variant", "group_kind"))]
        assert average["nonempty_groups"] == len(grouped)
        for metric in ("review_fraction", "reimage_fraction"):
            expected = sum(row[metric] for row in grouped) / len(grouped) if grouped else None
            assert average[f"equal_group_mean_{metric}"] == expected
    dense = [row for row in report["equal_group_averages"]
             if row["subset"] == "dense_reading_ge_40" and row["group_kind"] == "sequence"]
    assert all(row["nonempty_groups"] == 8 and row["total_groups"] == 14 for row in dense)


def test_observed_workload_counts_not_detection_accuracy(replayed):
    decisions, report = replayed
    pooled = [row for row in report["summaries"] if row["group_kind"] == "pooled"
              and row["variant"] == "current_configured" and row["target_pct"] == 80
              and row["timing_scenario"] == "assumed_elapsed" and row["subset"] == "all"][0]
    assert pooled["actions"]["human_review"] == 0
    assert pooled["actions"]["reimage"] == 149
    assert pooled["anomaly_flag_count"] == 123
    assert pooled["reading_at_or_above_target"] == 0
    assert all(row["outputs"]["current_configured"]["host_actionable"] is False for row in decisions)
    assert all(row["outputs"]["current_configured"]["action"] != "passage" for row in decisions)
    assert "Anomaly flag rate is not human-review rate" in report["metric_boundary"]


def test_bank_file_and_array_identity_are_distinct(loaded):
    manifest, rows, _ = loaded
    provenance = manifest["anomaly_provenance"]
    assert provenance["configured_bank_array_sha256"] == provenance["observed_bank_array_sha256"]
    assert provenance["bank_file_sha256"] != provenance["observed_bank_array_sha256"]
    assert manifest["weights"]["exact_weight_sha256"] is None
    assert all(row["confluency_truth_pct"] is None for row in rows)
