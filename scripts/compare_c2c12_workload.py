"""Freeze and replay C2C12 action burden; cached readings are not ground truth."""

from __future__ import annotations

import argparse
from collections import Counter
import csv
from dataclasses import asdict
import json
import math
from pathlib import Path
import sys
from types import ModuleType

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "scripts"))

import compare_decision_policies as common
from culture.anomaly import bank_hash, bin_index, bin_label
from culture.profiles import Profile, get_profile
from culture.quality import evaluate_thresholds
from culture.rules import CheckPolicy, LineConfig, RULES_VERSION, evaluate_decision

DEFAULT_BUNDLE = REPO / "results/policy_comparison_c2c12"
SOURCE_PATHS = (*common.SOURCE_PATHS, "scripts/compare_c2c12_workload.py",
                "culture/quality.py", "culture/provenance.py", "culture/anomaly.py")
VARIANTS = ("baseline", "baseline_classifier_demoted", "current_configured")
ARTIFACTS = ("inputs.json", "baseline_rules.py", "quality.yaml", "anomaly.yaml", "split.csv")


def heldout_members(split_path):
    with Path(split_path).open() as handle:
        rows = [row for row in csv.DictReader(handle) if row["kind"] == "base" and row["split"] == "heldout"]
    if len({row["sequence_id"] for row in rows}) != len(rows):
        raise ValueError("Duplicate held-out sequence membership")
    return {row["sequence_id"]: row["experiment"] for row in rows}


def freeze(bundle):
    import numpy as np
    import pandas as pd
    import yaml

    if bundle.exists():
        raise ValueError("Freeze requires a new directory; never overwrite a historical bundle")
    source_paths = (
        "cache/images.parquet", "cache/confluency.parquet", "cache/logits.parquet",
        "cache/quality.parquet", "cache/anomaly/scores.parquet", "cache/anomaly/banks.npz",
        "cache/MANIFEST.json", "configs/quality.yaml", "configs/anomaly.yaml",
        "configs/confluency_profiles.yaml", "results/replay_fleet_split.csv",
        "scripts/eval_anomaly.py",
    )
    before = {path: common.digest(REPO / path) for path in source_paths}
    members = heldout_members(REPO / "results/replay_fleet_split.csv")
    scores = pd.read_parquet(REPO / "cache/anomaly/scores.parquet")
    scores = scores[(scores.kind == "normal") & (scores.split == "heldout")].copy()
    if len(scores) != 1228 or set(scores.base_sequence_id) != set(members):
        raise ValueError("Expected the complete 1,228-frame held-out unmodified cohort")
    images = pd.read_parquet(REPO / "cache/images.parquet")
    images = images[(images.dataset == "c2c12") & images.sequence_id.isin(members)]
    if set(images.image_sha256) != set(scores.image_sha256) or len(images) != len(scores):
        raise ValueError("Anomaly cohort does not exactly match held-out base images")
    joined = scores.merge(images[["image_sha256", "sequence_id", "frame_idx"]],
                          on="image_sha256", validate="one_to_one", suffixes=("", "_image"))
    if not (joined.base_sequence_id == joined.sequence_id).all() or not (joined.frame_idx == joined.frame_idx_image).all():
        raise ValueError("Score/image lineage mismatch")
    conf = pd.read_parquet(REPO / "cache/confluency.parquet")
    conf = conf[(conf.model_name == "seg") & (conf.model_version == "cpsam_v2") & (conf.crop_spec == "full")]
    joined = joined.merge(conf[["image_sha256", "pct", "confidence"]], on="image_sha256",
                          how="left", validate="one_to_one", suffixes=("", "_reading"))
    if not (joined.pct == joined.pct_reading).all():
        raise ValueError("Anomaly-bin readings differ from full-frame segmentation cache")
    logits = pd.read_parquet(REPO / "cache/logits.parquet")
    logits = logits[(logits.model_name == "qc") & (logits.model_version == "qc_effnetb0_v1") & (logits.crop_spec == "full")]
    joined = joined.merge(logits[["image_sha256", "logits"]], on="image_sha256", how="left", validate="one_to_one")
    quality = pd.read_parquet(REPO / "cache/quality.parquet")
    quality = quality[(quality.model_name == "quality") & (quality.model_version == "quality_v1")]
    metrics = ["blur_laplacian_var", "exposure_mean", "uniformity_block_std"]
    joined = joined.merge(quality[["image_sha256", *metrics]], on="image_sha256", how="left", validate="one_to_one")
    if joined[["confidence", "logits", *metrics]].isna().any().any():
        raise ValueError("Missing segmentation/classifier/quality cache values")
    anomaly = yaml.safe_load((REPO / "configs/anomaly.yaml").read_text())
    with np.load(REPO / "cache/anomaly/banks.npz", allow_pickle=False) as banks:
        array_hash = bank_hash([banks[name] for name in sorted(banks.files)])
    if array_hash != anomaly["bank"]["sha256"]:
        raise ValueError("Bank array-content hash differs from the configured bank")
    profile = get_profile("c2c12_ker2018")
    if (profile.cutoff != 0 or profile.band_pp is not None or profile.quality != "c2c12"
            or profile.entry["action_eligibility"]["status"] != "unsupported"):
        raise ValueError("Protocol requires the uncalibrated, unsupported C2C12 profile")
    rows = []
    for row in joined.sort_values(["sequence_id", "frame_idx"]).to_dict("records"):
        qc_logits = json.loads(row["logits"])
        qc_flag, qc_confidence = common.qc_prediction(qc_logits)
        quality_metrics = {key: float(row[key]) for key in metrics}
        gate = evaluate_thresholds(*quality_metrics.values(), dataset="c2c12")
        rows.append({
            "image_sha256": row["image_sha256"], "sequence_id": row["sequence_id"],
            "experiment": members[row["sequence_id"]], "frame_idx": int(row["frame_idx"]),
            "kind": "normal", "split": "heldout", "dataset": "c2c12",
            "confluency_truth_pct": None, "pct_cut0": float(row["pct"]),
            "confidence_cut0": float(row["confidence"]), "qc_logits": qc_logits,
            "qc_flag": qc_flag, "qc_confidence": qc_confidence,
            "quality_metrics": quality_metrics, "quality_passed": bool(gate.passed),
            "quality_reasons": gate.reasons, "anomaly_flag": bool(row["flag_binned"]),
            "anomaly_bin": row["bin_label"], "anomaly_score": float(row["score_binned"]),
            "anomaly_z": float(row["z_binned"]),
        })
    baseline_commit = common.git_output("rev-parse", common.BASELINE_REF).decode().strip()
    baseline_source = common.git_output("show", f"{baseline_commit}:culture/rules.py")
    if before != {path: common.digest(REPO / path) for path in source_paths}:
        raise ValueError("An input changed while freezing")
    bundle.mkdir(parents=True)
    common.write_json(bundle / "inputs.json", rows)
    (bundle / "baseline_rules.py").write_bytes(baseline_source)
    for source, name in (("configs/quality.yaml", "quality.yaml"), ("configs/anomaly.yaml", "anomaly.yaml"),
                         ("results/replay_fleet_split.csv", "split.csv")):
        (bundle / name).write_bytes((REPO / source).read_bytes())
    common.write_json(bundle / "manifest.json", {
        "protocol_version": 1, "comparison_kind": "cached_policy_workload_replay", "inference_run": False,
        "sample_count": len(rows), "sequence_count": len(members), "experiment_group_count": len(set(members.values())),
        "baseline_commit": baseline_commit, "current_parent_commit": common.git_output("rev-parse", "HEAD").decode().strip(),
        "current_identity": "Dirty local implementation identified by source hashes, not parent commit",
        "current_rules": RULES_VERSION, "freeze_python_version": sys.version.split()[0],
        "source_sha256": {path: common.digest(REPO / path) for path in SOURCE_PATHS},
        "input_source_sha256": before, "artifact_sha256": {name: common.digest(bundle / name) for name in ARTIFACTS},
        "profile": asdict(profile), "line_config": asdict(LineConfig()),
        "check_policy": asdict(CheckPolicy(qc="not_applicable")),
        "targets_pct": [80.0, 50.0],
        "timing_scenarios": {
            "unknown": {"hours_since_passage": None, "hours_since_feed": None},
            "assumed_elapsed": {"hours_since_passage": 48.0, "hours_since_feed": 12.0},
        },
        "timing_provenance": "No actual passage/feed times; 48h/12h are explicit diagnostic assumptions",
        "dense_reading_min_pct": 40.0,
        "anomaly_provenance": {
            "configured_bank_array_sha256": anomaly["bank"]["sha256"], "observed_bank_array_sha256": array_hash,
            "hash_method": "culture.anomaly.bank_hash: contiguous array bytes in sorted bank-key order, not NPZ file bytes",
            "bank_file_sha256": before["cache/anomaly/banks.npz"],
            "scoring_scope": "Historical centre tile, not current experimental whole-frame coverage",
            "score_binding": "Score parquet has no per-row bank/config identity; source pipeline describes held-out scoring against full tuning banks",
            "threshold_check": "Cached held-out flags agree with frozen serialized thresholds; scores are not recomputed",
        },
        "weights": {"seg_cache_version": "cpsam_v2", "qc_cache_version": "qc_effnetb0_v1",
                    "anomaly_backbone": "facebook/dinov2-small", "exact_weight_sha256": None},
        "limitations": [
            "Workload-only cached-policy replay, not end-to-end v2/v4 or fine-tuned model evidence.",
            "Normal means unmodified source frames, not independently adjudicated healthy cultures.",
            "No independent confluency truth: no accuracy, early-passage or ready-called-continue metrics.",
            "The 14 sequence groups share 3 experiment groups; all 3 occur in tuning too. Not experiment-held-out.",
            "Frames and repeated contexts are correlated; no frame-independent confidence intervals.",
            "50% is diagnostic, not a recommended passage threshold; no cached reading reaches 80%.",
            "No synthetic faults or growth-stall resampling; their absence does not imply detection success.",
            "No exact historical weight authentication or per-row score-to-bank binding; raw images are not rehashed.",
            "No observed review duration, workflow retry cost, saved time or ROI.",
            "Current outputs are advisory and the shipped C2C12 profile cannot authorize passage.",
        ],
    })


def load_bundle(bundle):
    import yaml

    manifest = json.loads((bundle / "manifest.json").read_text())
    if manifest["protocol_version"] != 1 or manifest["current_rules"] != RULES_VERSION:
        raise ValueError("Unsupported frozen protocol or policy version")
    for path in SOURCE_PATHS:
        if common.digest(REPO / path) != manifest["source_sha256"][path]:
            raise ValueError(f"Frozen source mismatch: {path}")
    for name in ARTIFACTS:
        if common.digest(bundle / name) != manifest["artifact_sha256"][name]:
            raise ValueError(f"Frozen artifact mismatch: {name}")
    members = heldout_members(bundle / "split.csv")
    rows = json.loads((bundle / "inputs.json").read_text())
    if (not rows or len(rows) != manifest["sample_count"]
            or len({row["image_sha256"] for row in rows}) != len(rows)
            or len({(row["sequence_id"], row["frame_idx"]) for row in rows}) != len(rows)
            or set(row["sequence_id"] for row in rows) != set(members)
            or len(members) != manifest["sequence_count"]
            or len(set(members.values())) != manifest["experiment_group_count"]):
        raise ValueError("Frozen cohort membership/count mismatch")
    anomaly = yaml.safe_load((bundle / "anomaly.yaml").read_text())
    for row in rows:
        if (row["kind"] != "normal" or row["split"] != "heldout" or row["dataset"] != "c2c12"
                or row["confluency_truth_pct"] is not None or row["experiment"] != members[row["sequence_id"]]):
            raise ValueError("Unsupported cohort, truth or group identity")
        for field, maximum in (("pct_cut0", 100), ("confidence_cut0", 1), ("qc_confidence", 1)):
            value = row[field]
            if type(value) not in (int, float) or not math.isfinite(value) or not 0 <= value <= maximum:
                raise ValueError(f"Invalid input {field}")
        numeric = [*row["quality_metrics"].values(), row["anomaly_score"], row["anomaly_z"]]
        if any(type(value) not in (int, float) or not math.isfinite(value) for value in numeric):
            raise ValueError("Nonfinite quality/anomaly cache values")
        if (type(row["frame_idx"]) is not int or row["frame_idx"] < 0
                or any(value < 0 for value in row["quality_metrics"].values())
                or row["quality_metrics"]["exposure_mean"] > 255):
            raise ValueError("Invalid frame index or quality metric range")
        flag, confidence = common.qc_prediction(row["qc_logits"])
        if flag != row["qc_flag"] or not math.isclose(confidence, row["qc_confidence"], rel_tol=0, abs_tol=1e-14):
            raise ValueError("Classifier prediction differs from logits")
        metrics = row["quality_metrics"]
        gate = evaluate_thresholds(metrics["blur_laplacian_var"], metrics["exposure_mean"],
                                   metrics["uniformity_block_std"], str(bundle / "quality.yaml"), dataset="c2c12")
        if type(row["quality_passed"]) is not bool or row["quality_passed"] != gate.passed or row["quality_reasons"] != gate.reasons:
            raise ValueError("Quality output differs from frozen metrics/configuration")
        label = bin_label(bin_index(row["pct_cut0"], anomaly["bins"]["edges"]), anomaly["bins"]["edges"])
        if (label != row["anomaly_bin"] or type(row["anomaly_flag"]) is not bool
                or row["anomaly_flag"] != (row["anomaly_score"] > anomaly["calibration"]["bins"][label]["threshold"])):
            raise ValueError("Anomaly bin/flag differs from frozen reading/score/threshold")
    baseline = ModuleType("_cultureqc_c2c12_baseline")
    sys.modules[baseline.__name__] = baseline
    exec(compile((bundle / "baseline_rules.py").read_bytes(), str(bundle / "baseline_rules.py"), "exec"), baseline.__dict__)
    return manifest, rows, baseline


def replay_outputs(row, manifest, baseline, target, timing):
    config = {**manifest["line_config"], "target_confluency": target}
    inputs = {"confluency_pct": row["pct_cut0"], "confluency_confidence": row["confidence_cut0"], **timing}
    outputs = {}
    for variant in VARIANTS[:2]:
        flag, confidence = ((row["qc_flag"], row["qc_confidence"]) if variant == "baseline" else ("normal", 1.0))
        action, reason = baseline.decide(**inputs, qc_flag=flag, qc_confidence=confidence,
                                        line_config=baseline.LineConfig(**config))
        outputs[variant] = {"raw_action": action, "action": "continue" if action == "hold" else action,
                            "reason": reason, "reason_code": None}
    profile = Profile(**manifest["profile"])
    decision = evaluate_decision(
        **inputs, qc_flag=None, qc_confidence=None, line_config=LineConfig(**config),
        profile=profile, band_pp=profile.band_pp, quality_passed=row["quality_passed"],
        quality_reasons=row["quality_reasons"], anomaly_flag=row["anomaly_flag"],
        check_policy=CheckPolicy(**manifest["check_policy"]),
    )
    outputs["current_configured"] = {
        "raw_action": decision.action, "action": decision.action, "reason": decision.reason,
        "reason_code": decision.reason_code, "mode": "advisory", "host_actionable": False,
    }
    return outputs


def summarize(rows, target, variant):
    count = len(rows)
    counts = Counter(row["outputs"][variant]["action"] for row in rows)
    return {
        "n_frames": count, "n_sequences": len({row["sequence_id"] for row in rows}),
        "n_experiment_groups": len({row["experiment"] for row in rows}),
        "reading_at_or_above_target": sum(row["pct_cut0"] >= target for row in rows),
        "actions": {action: counts[action] for action in ("continue", "passage", "feed", "human_review", "reimage")},
        "review_fraction": counts["human_review"] / count if count else None,
        "reimage_fraction": counts["reimage"] / count if count else None,
        "explicit_review_or_reimage_fraction": (counts["human_review"] + counts["reimage"]) / count if count else None,
        "anomaly_flag_count": sum(row["anomaly_flag"] for row in rows),
        "quality_failed_count": sum(not row["quality_passed"] for row in rows),
        "confidence_interval": None,
        "decision_accuracy": None,
        "uncertainty_reason": "Descriptive grouped cache, correlated frames, no independent action truth",
    }


def replay(bundle):
    manifest, inputs, baseline = load_bundle(bundle)
    decisions, summaries, group_averages = [], [], []
    for target in manifest["targets_pct"]:
        for timing_name, timing in manifest["timing_scenarios"].items():
            group = []
            for row in inputs:
                outputs = replay_outputs(row, manifest, baseline, target, timing)
                group.append({**row, "outputs": outputs})
                decisions.append({"image_sha256": row["image_sha256"], "target_pct": target,
                                  "timing_scenario": timing_name, "outputs": outputs})
            for subset in ("all", "dense_reading_ge_40"):
                selected = group if subset == "all" else [row for row in group if row["pct_cut0"] >= manifest["dense_reading_min_pct"]]
                for variant in VARIANTS:
                    identity = {"target_pct": target, "timing_scenario": timing_name, "subset": subset, "variant": variant}
                    summaries.append({**identity, "group_kind": "pooled", "group_id": "all", **summarize(selected, target, variant)})
                    for kind, key in (("sequence", "sequence_id"), ("experiment", "experiment")):
                        grouped = [summarize([row for row in selected if row[key] == value], target, variant)
                                   for value in sorted({row[key] for row in group})]
                        for value, summary in zip(sorted({row[key] for row in group}), grouped):
                            summaries.append({**identity, "group_kind": kind, "group_id": value, **summary})
                        nonempty = [summary for summary in grouped if summary["n_frames"]]
                        group_averages.append({
                            **identity, "group_kind": kind, "nonempty_groups": len(nonempty),
                            "total_groups": len(grouped),
                            **{f"equal_group_mean_{metric}": sum(summary[metric] for summary in nonempty) / len(nonempty)
                               if nonempty else None for metric in ("review_fraction", "reimage_fraction")},
                        })
    report = {
        "comparison_kind": manifest["comparison_kind"], "manifest_sha256": common.digest(bundle / "manifest.json"),
        "n_unique_frames": len(inputs), "n_sequences": manifest["sequence_count"],
        "n_experiment_groups": manifest["experiment_group_count"], "paired_context_rows": len(decisions),
        "max_cached_reading_pct": max(row["pct_cut0"] for row in inputs),
        "summaries": summaries, "equal_group_averages": group_averages,
        "limitations": manifest["limitations"],
        "metric_boundary": "Explicit rule-action burden only, not measured human workload. Current continue/feed outputs still require host review/authorization. Anomaly flag rate is not human-review rate.",
    }
    return decisions, report


def markdown_report(report):
    lines = [
        "# C2C12 cached-policy workload comparison", "",
        "**No independent confluency/action truth. Not a detection or automation validation.**", "",
        f"{report['n_unique_frames']} unmodified held-out frames, {report['n_sequences']} sequence groups, "
        f"{report['n_experiment_groups']} experiment groups; {report['paired_context_rows']} repeated-context rows.",
        "The split holds out sequences, not experiments. All experiment groups also occur in tuning.",
        f"Maximum cached reading: {report['max_cached_reading_pct']:.2f}%. A reading is not ground truth.", "",
        report["metric_boundary"], "",
        "## Pooled action counts, with dense-reading burden", "",
        "| Target | Timing | Subset | Policy | Frames | Continue | Passage | Review | Reimage |",
        "|---|---|---|---|---:|---:|---:|---:|---:|",
    ]
    for row in report["summaries"]:
        if row["group_kind"] != "pooled":
            continue
        counts = row["actions"]
        lines.append(f"| {row['target_pct']:g} | {row['timing_scenario']} | {row['subset']} | {row['variant']} | "
                     f"{row['n_frames']} | {counts['continue']} | {counts['passage']} | {counts['human_review']} | {counts['reimage']} |")
    lines += [
        "", "Dense means cached reading ≥40%, not annotated density. 50% is a diagnostic target only.",
        "No cached reading reaches 80%; zero passage does not demonstrate passage safety.",
        "Review and reimage are separate; their sum is explicit deferred-output burden, not elapsed work.", "",
        "## Grouping and provenance", "",
        "`report.json` includes every sequence and experiment at both targets/timings and both subsets.",
        "It also supplies equal-sequence and equal-experiment mean rates alongside frame-weighted pooled counts.",
        "Empty dense subsets retain zero counts and null rates; group averages exclude them and disclose denominators.",
        "No confidence intervals or decision-accuracy estimates are inferred from correlated frames.",
        "The three policies isolate classifier neutralization, then current rules plus quality/anomaly policy.",
        "C2C12 remains uncalibrated (cutoff 0, no band); no calibration or model gain is claimed.",
        "Historical centre-tile anomaly flags are replayed, not new whole-frame detection signals.",
        "Bank array identity and NPZ file identity are distinct hashes. Score-to-bank binding is not authenticated per row.",
        "Bundle checksums establish reproducibility, not signed custody: the manifest itself has no independent trusted anchor.",
        "Quality is reevaluated from frozen metrics/config; anomaly flags are checked against serialized thresholds, not rescored.", "",
        "## Limits", "",
    ]
    lines += [f"- {value}" for value in report["limitations"]]
    return "\n".join(lines) + "\n"


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundle", type=Path, default=DEFAULT_BUNDLE)
    parser.add_argument("--freeze", action="store_true")
    parser.add_argument("--out", type=Path)
    args = parser.parse_args(argv)
    if args.out is None:
        if not args.freeze:
            parser.error("--out is required")
        args.out = args.bundle / "replay"
    if args.out.exists():
        parser.error("--out must not exist; historical results are never overwritten")
    if args.freeze:
        freeze(args.bundle)
    decisions, report = replay(args.bundle)
    args.out.mkdir(parents=True)
    common.write_json(args.out / "report.json", report)
    (args.out / "decisions.jsonl").write_text("".join(json.dumps(row, sort_keys=True, allow_nan=False) + "\n" for row in decisions))
    (args.out / "report.md").write_text(markdown_report(report))
    print(json.dumps({"output": str(args.out), "paired_context_rows": len(decisions), "inference_run": False}))


if __name__ == "__main__":
    main()
