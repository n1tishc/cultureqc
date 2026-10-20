"""Cached policy replay is reproducible without cache, models, network or git history."""

import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys

import pytest

REPO = Path(__file__).resolve().parents[1]
SCRIPT = REPO / "scripts/compare_decision_policies.py"
spec = importlib.util.spec_from_file_location("comparison", SCRIPT)
comparison = importlib.util.module_from_spec(spec)
spec.loader.exec_module(comparison)
BUNDLE = REPO / "results/policy_comparison_evican"


@pytest.fixture
def loaded():
    return comparison.load_bundle(BUNDLE)


def tree_hashes(directory):
    return {str(path.relative_to(directory)): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in directory.rglob("*") if path.is_file()}


def test_replay_matches_frozen_results_without_mutating_bundle():
    before = tree_hashes(BUNDLE)
    decisions, report = comparison.replay(BUNDLE)
    expected = [json.loads(line) for line in (BUNDLE / "replay/decisions.jsonl").read_text().splitlines()]
    assert decisions == expected
    assert report == json.loads((BUNDLE / "replay/report.json").read_text())
    assert comparison.markdown_report(report) == (BUNDLE / "replay/report.md").read_text()
    assert tree_hashes(BUNDLE) == before
    assert len(decisions) == 33 * 2 * 2
    assert len({row["image_sha256"] for row in decisions}) == 33


def test_cli_does_not_need_cache_git_or_models(tmp_path):
    checkout = tmp_path / "minimal"
    for relative in comparison.SOURCE_PATHS:
        destination = checkout / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(REPO / relative, destination)
    shutil.copytree(BUNDLE, checkout / "bundle")
    output = tmp_path / "replay"
    result = subprocess.run(
        [sys.executable, str(checkout / "scripts/compare_decision_policies.py"),
         "--bundle", str(checkout / "bundle"), "--out", str(output)],
        capture_output=True, text=True, timeout=20,
        cwd=checkout, env={"PATH": "", "PYTHONDONTWRITEBYTECODE": "1"},
    )
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)["inference_run"] is False
    for name in ("report.json", "decisions.jsonl", "report.md"):
        assert (output / name).read_bytes() == (BUNDLE / "replay" / name).read_bytes()


def test_refuses_to_overwrite_historical_output(tmp_path):
    output = tmp_path / "existing"
    output.mkdir()
    sentinel = output / "keep"
    sentinel.write_text("unchanged")
    with pytest.raises(SystemExit):
        comparison.main(["--out", str(output)])
    assert sentinel.read_text() == "unchanged"
    with pytest.raises(ValueError, match="never overwritten"):
        comparison.freeze(BUNDLE)


@pytest.mark.parametrize("filename", ["inputs.json", "baseline_rules.py"])
def test_artifact_tampering_fails_before_replay(tmp_path, filename):
    bundle = tmp_path / "bundle"
    shutil.copytree(BUNDLE, bundle)
    with (bundle / filename).open("a") as handle:
        handle.write("\n")
    with pytest.raises(ValueError, match="artifact mismatch"):
        comparison.replay(bundle)


def test_source_drift_fails_before_replay(tmp_path, monkeypatch):
    actual_digest = comparison.digest

    def changed_digest(path):
        return "0" * 64 if Path(path) == REPO / "culture/rules.py" else actual_digest(path)

    monkeypatch.setattr(comparison, "digest", changed_digest)
    with pytest.raises(ValueError, match="source mismatch"):
        comparison.replay(BUNDLE)


@pytest.mark.parametrize("field,value", [
    ("gt_pct", float("nan")), ("pct_cut0", 101), ("confidence_cut0", -1),
    ("quality_passed", True), ("anomaly_flag", False), ("truth_kind", "model_proxy"),
    ("qc_flag", "unknown"),
])
def test_invalid_or_relabelled_inputs_fail_even_with_updated_hash(tmp_path, field, value):
    bundle = tmp_path / "bundle"
    shutil.copytree(BUNDLE, bundle)
    rows = json.loads((bundle / "inputs.json").read_text())
    rows[0][field] = value
    (bundle / "inputs.json").write_text(json.dumps(rows))
    manifest = json.loads((bundle / "manifest.json").read_text())
    manifest["artifact_sha256"]["inputs.json"] = comparison.digest(bundle / "inputs.json")
    comparison.write_json(bundle / "manifest.json", manifest)
    with pytest.raises(ValueError):
        comparison.replay(bundle)


def test_pinned_baseline_classifier_and_confidence_precedence(loaded):
    manifest, rows, baseline = loaded
    row = {**rows[0], "pct_cut0": 90, "confidence_cut0": 0.9,
           "qc_flag": "contamination_suspected", "qc_confidence": 0.7}
    result = comparison.replay_row(row, manifest, baseline, 80, manifest["timing_scenarios"]["assumed_elapsed"])
    assert result["baseline"]["action"] == "human_review"
    assert result["baseline_classifier_demoted"]["action"] == "passage"
    row["confidence_cut0"] = 0.299
    result = comparison.replay_row(row, manifest, baseline, 80, manifest["timing_scenarios"]["assumed_elapsed"])
    assert result["baseline_classifier_demoted"]["action"] == "human_review"
    row["confidence_cut0"] = 0.3
    result = comparison.replay_row(row, manifest, baseline, 80, manifest["timing_scenarios"]["assumed_elapsed"])
    assert result["baseline_classifier_demoted"]["action"] == "passage"


def test_unknown_timing_is_not_fabricated_for_current_policy(loaded):
    manifest, rows, baseline = loaded
    row = {**rows[0], "pct_cut0": 90, "confidence_cut0": 0.9,
           "pct_configured": 90, "qc_flag": "normal", "qc_confidence": 1}
    outputs = comparison.replay_row(row, manifest, baseline, 80, manifest["timing_scenarios"]["unknown"])
    assert outputs["baseline"]["action"] == "passage"
    assert outputs["current_configured"]["action"] == "human_review"
    assert outputs["current_configured"]["reason_code"] == "passage_time_unknown"
    assert outputs["current_configured"]["timing"]["passage"]["hours"] is None


def test_frozen_current_outputs_preserve_advisory_and_missing_checks():
    decisions, _ = comparison.replay(BUNDLE)
    for row in decisions:
        for variant in comparison.VARIANTS[2:]:
            output = row["outputs"][variant]
            assert output["host_actionable"] is False
            assert output["checks"]["quality"]["status"] == "unavailable"
            assert output["checks"]["anomaly"]["status"] == "unavailable"
            assert output["checks"]["qc"]["status"] == "not_applicable"
            assert output["action"] != "passage"


def test_counts_do_not_reward_missing_ready_cases_or_empty_subsets():
    _, report = comparison.replay(BUNDLE)
    for row in report["summaries"]:
        assert sum(row["actions"].values()) == row["n_images"]
        if row["target_pct"] == 80:
            assert row["n_at_or_above_target"] == 0
            assert row["passage_evidence"] == "insufficient_no_target_reaching_cases"
        if row["n_images"] == 0:
            assert row["review_fraction"] is None
            assert row["threshold_correct_decided_coverage"] is None
        assert row["independent_biological_units"] is None
        assert row["uncertainty_interval"] is None


def test_threshold_metrics_separate_review_reimage_and_errors():
    rows = [{"gt_pct": truth, "outputs": {"fixture": {"action": action}}} for truth, action in (
        (20, "passage"), (90, "continue"), (20, "continue"), (90, "passage"),
        (90, "human_review"), (20, "reimage"), (20, "feed"),
    )]
    summary = comparison.summarize(rows, 80, "fixture")
    assert summary["early_passage"] == 1
    assert summary["ready_called_continue"] == 1
    assert summary["threshold_correct_decided_n"] == 2
    assert summary["threshold_correct_decided_coverage"] == 2 / 7
    assert summary["threshold_accuracy_among_decided"] == 2 / 4
    assert summary["review_fraction"] == summary["reimage_fraction"] == 1 / 7


def test_baseline_hold_normalization_retains_original(loaded):
    manifest, rows, baseline = loaded
    row = {**rows[0], "pct_cut0": 10, "confidence_cut0": 0.9,
           "qc_flag": "normal", "qc_confidence": 1}
    outputs = comparison.replay_row(row, manifest, baseline, 80, manifest["timing_scenarios"]["unknown"])
    assert outputs["baseline"]["raw_action"] == "hold"
    assert outputs["baseline"]["action"] == "continue"


def test_manifest_discloses_unverifiable_weights_and_local_identity(loaded):
    manifest, _, _ = loaded
    assert manifest["weights"]["seg"]["sha256"] is None
    assert manifest["weights"]["qc"]["sha256"] is None
    assert manifest["profile"]["band_pp"] == 29.4
    assert manifest["profile"]["entry"]["action_eligibility"]["status"] == "unsupported"
    assert manifest["baseline_commit"].startswith("e2274dd")
    assert set(manifest["source_sha256"]) == set(comparison.SOURCE_PATHS)
    assert manifest["comparison_kind"] == "cached_policy_replay"
