"""Freeze and replay an internal, cached EVICAN policy comparison without inference."""

from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import asdict
import hashlib
import json
import math
from pathlib import Path
import subprocess
import sys
from types import ModuleType

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from culture.profiles import Profile, get_profile
from culture.rules import CheckPolicy, LineConfig, RULES_VERSION, evaluate_decision

BASELINE_REF = "e2274dd"
DEFAULT_BUNDLE = REPO / "results/policy_comparison_evican"
SOURCE_PATHS = (
    "scripts/compare_decision_policies.py",
    "culture/rules.py",
    "culture/profiles.py",
)
VARIANTS = (
    "baseline",
    "baseline_classifier_demoted",
    "current_uncalibrated",
    "current_configured",
)
CLASS_NAMES = ("normal", "contamination_suspected", "detachment", "image_quality")


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_json(path, value):
    Path(path).write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n")


def git_output(*args):
    return subprocess.check_output(["git", "-C", str(REPO), *args])


def qc_prediction(logits):
    if len(logits) != len(CLASS_NAMES) or not all(math.isfinite(value) for value in logits):
        raise ValueError("Expected four finite classifier logits")
    shifted = [math.exp(value - max(logits)) for value in logits]
    winner = max(range(len(shifted)), key=shifted.__getitem__)
    return CLASS_NAMES[winner], shifted[winner] / sum(shifted)


def freeze(bundle):
    if bundle.exists():
        raise ValueError("Freeze requires a new directory; historical artifacts are never overwritten")
    import pandas as pd

    source_paths = (
        "cache/images.parquet", "cache/logits.parquet", "cache/MANIFEST.json",
        "results/confluency_cutoff.csv", "results/confluency_real.csv",
        "results/confluency_profiles.json", "configs/confluency_profiles.yaml",
    )
    sources_before = {path: digest(REPO / path) for path in source_paths}
    cutoff = pd.read_csv(REPO / "results/confluency_cutoff.csv")
    cutoff = cutoff[cutoff["split"] == "eval33"].copy()
    originals = pd.read_csv(REPO / "results/confluency_real.csv")
    if len(cutoff) != 33 or set(cutoff.file_name) != set(originals.file_name):
        raise ValueError("The frozen cohort must be the original 33 evaluation images")
    truth = originals.set_index("file_name")["gt_pct"]
    if any(row.gt_pct != truth.loc[row.file_name] for row in cutoff.itertuples()):
        raise ValueError("Expert-mask truth differs between the original and cutoff studies")
    images = pd.read_parquet(REPO / "cache/images.parquet")
    images = images[images.dataset == "evican_eval2019"].copy()
    images["file_name"] = images.source_path.map(lambda path: Path(path).name)
    logits = pd.read_parquet(REPO / "cache/logits.parquet")
    logits = logits[(logits.model_name == "qc") & (logits.model_version == "qc_effnetb0_v1")
                    & (logits.crop_spec == "full")]
    joined = cutoff.merge(images[["file_name", "image_sha256"]], on="file_name",
                          how="left", validate="one_to_one")
    joined = joined.merge(logits[["image_sha256", "logits"]], on="image_sha256",
                          how="left", validate="one_to_one")
    if joined[["image_sha256", "logits"]].isna().any().any():
        raise ValueError("Every evaluation image needs one cached image identity and classifier output")
    rows = []
    for row in joined.sort_values("file_name").to_dict("records"):
        qc_flag, qc_confidence = qc_prediction(json.loads(row["logits"]))
        rows.append({
            "file_name": row["file_name"], "image_sha256": row["image_sha256"],
            "split": "eval33", "truth_kind": "independent_expert_mask_union",
            "gt_pct": row["gt_pct"], "pct_cut0": row["pct_cut0"],
            "confidence_cut0": row["conf_cut0"], "pct_configured": row["pct_cut-3.5"],
            "confidence_configured": row["conf_cut-3.5"],
            "qc_logits": json.loads(row["logits"]), "qc_flag": qc_flag,
            "qc_confidence": qc_confidence, "quality_passed": None, "anomaly_flag": None,
            "biological_unit_id": None,
        })
    profile = get_profile("evican_mixed")
    if profile.cutoff != -3.5 or profile.band_pp != 29.4 or profile.quality is not None:
        raise ValueError("This freeze supports only the documented EVICAN profile")
    if profile.entry["action_eligibility"]["status"] != "unsupported":
        raise ValueError("This protocol must not imply passage approval")
    baseline_commit = git_output("rev-parse", BASELINE_REF).decode().strip()
    baseline_source = git_output("show", f"{baseline_commit}:culture/rules.py")
    sources_after = {path: digest(REPO / path) for path in source_paths}
    if sources_before != sources_after:
        raise ValueError("An input changed while freezing")
    bundle.mkdir(parents=True)
    write_json(bundle / "inputs.json", rows)
    (bundle / "baseline_rules.py").write_bytes(baseline_source)
    manifest = {
        "protocol_version": 1, "comparison_kind": "cached_policy_replay",
        "freeze_python_version": sys.version.split()[0], "inference_run": False,
        "cohort": "EVICAN eval2019, original eval33; reused, not fully blind",
        "sample_count": len(rows), "independent_biological_unit_count": None,
        "baseline_commit": baseline_commit,
        "current_parent_commit": git_output("rev-parse", "HEAD").decode().strip(),
        "current_identity": "Local source hashes identify the implementation, not the parent commit",
        "current_rules": RULES_VERSION,
        "source_sha256": {path: digest(REPO / path) for path in SOURCE_PATHS},
        "input_source_sha256": sources_before,
        "artifact_sha256": {
            "inputs.json": digest(bundle / "inputs.json"),
            "baseline_rules.py": digest(bundle / "baseline_rules.py"),
        },
        "profile": asdict(profile),
        "line_config": asdict(LineConfig()),
        "check_policy": asdict(CheckPolicy(qc="not_applicable")),
        "targets_pct": [80.0, 50.0],
        "timing_scenarios": {
            "unknown": {"hours_since_passage": None, "hours_since_feed": None},
            "assumed_elapsed": {"hours_since_passage": 48.0, "hours_since_feed": 12.0},
        },
        "timing_provenance": "No capture/passage/feed timing is available; 48h/12h is a scenario, not an observation",
        "setup": "EVICAN mixed brightfield/phase contrast; no instrument-specific decision approval",
        "weights": {
            "seg": {"cache_version": "cpsam_v2", "sha256": None},
            "qc": {"cache_version": "qc_effnetb0_v1", "sha256": None},
            "limitation": "Cached outputs do not authenticate exact weights; no new inference or fine-tuned model",
        },
        "measurement_source": "Rounded full-resolution rerun CSV at cutoffs 0 and -3.5; same maps, not two model versions",
        "image_identity": "SHA-256 recorded by historical cache; raw image bytes are not reverified by replay",
        "truth_source": "Expert EVICAN Cell polygon union; not model-derived C2C12 proxy truth",
        "subset_rules": {"dense_gt_min_pct": 40.0, "near_target_half_width_pp": 10.0},
        "uncertainty": {
            "confidence_interval": None,
            "reason": "Biological independent-unit IDs unavailable; reused selected images do not support population inference",
            "rounding": "CSV readings rounded to 0.01 pp, truth to 0.001 pp; equality uses these stored values",
        },
        "limitations": [
            "Not an end-to-end v2/v4 benchmark or a fine-tuning comparison.",
            "Classifier demotion and policy/calibration changes are sequential ablations, not causal attribution.",
            "Quality and anomaly checks are unavailable on these images, not assumed to pass.",
            "No target-reaching ground truth at 80%; zero early passage cannot establish passage safety.",
            "50% is a diagnostic scenario, not a recommended culture passage threshold.",
            "No review-time measurement, workload saving, pilot approval or host action is established.",
            "v2's missing synthetic headline artifacts are not reconstructed.",
            "C2C12 cached readings are not independent truth and are outside this first bundle.",
        ],
    }
    write_json(bundle / "manifest.json", manifest)


def load_bundle(bundle):
    manifest = json.loads((bundle / "manifest.json").read_text())
    if manifest["protocol_version"] != 1 or manifest["current_rules"] != RULES_VERSION:
        raise ValueError("Unsupported comparison protocol or current rules version")
    for path in SOURCE_PATHS:
        if digest(REPO / path) != manifest["source_sha256"][path]:
            raise ValueError(f"Frozen source mismatch: {path}; make a new bundle rather than relabelling this result")
    for name in ("inputs.json", "baseline_rules.py"):
        if digest(bundle / name) != manifest["artifact_sha256"][name]:
            raise ValueError(f"Frozen artifact mismatch: {name}")
    rows = json.loads((bundle / "inputs.json").read_text())
    if len(rows) != manifest["sample_count"] or len({row["image_sha256"] for row in rows}) != len(rows):
        raise ValueError("Comparison input count or unique identities do not match")
    for row in rows:
        for field in ("gt_pct", "pct_cut0", "pct_configured", "confidence_cut0",
                      "confidence_configured", "qc_confidence"):
            value = row[field]
            maximum = 1 if field.startswith("confidence") or field == "qc_confidence" else 100
            if type(value) not in (int, float) or not math.isfinite(value) or not 0 <= value <= maximum:
                raise ValueError(f"Invalid input {field}")
        if row["truth_kind"] != "independent_expert_mask_union" or row["split"] != "eval33":
            raise ValueError("Unsupported truth source or split")
        predicted_flag, predicted_confidence = qc_prediction(row["qc_logits"])
        if row["qc_flag"] != predicted_flag or not math.isclose(
                row["qc_confidence"], predicted_confidence, rel_tol=0, abs_tol=1e-14):
            raise ValueError("Classifier prediction does not match frozen logits")
        if row["quality_passed"] is not None or row["anomaly_flag"] is not None:
            raise ValueError("EVICAN unavailable checks must remain unknown")
    module_name = "_cultureqc_frozen_baseline_rules"
    baseline = ModuleType(module_name)
    sys.modules[module_name] = baseline
    exec(compile((bundle / "baseline_rules.py").read_bytes(), str(bundle / "baseline_rules.py"), "exec"),
         baseline.__dict__)
    return manifest, rows, baseline


def replay_row(row, manifest, baseline, target, timing):
    config = {**manifest["line_config"], "target_confluency": target}
    common = {"confluency_pct": row["pct_cut0"],
              "confluency_confidence": row["confidence_cut0"], **timing}
    outputs = {}
    for variant in VARIANTS[:2]:
        flag, confidence = ((row["qc_flag"], row["qc_confidence"]) if variant == "baseline"
                            else ("normal", 1.0))
        action, reason = baseline.decide(**common, qc_flag=flag, qc_confidence=confidence,
                                        line_config=baseline.LineConfig(**config))
        outputs[variant] = {
            "raw_action": action, "action": "continue" if action == "hold" else action,
            "reason": reason, "reason_code": None,
        }
    profile = Profile(**manifest["profile"])
    for variant in VARIANTS[2:]:
        configured = variant == "current_configured"
        inputs = dict(common)
        if configured:
            inputs.update(confluency_pct=row["pct_configured"],
                          confluency_confidence=row["confidence_configured"])
        decision = evaluate_decision(
            **inputs, qc_flag=None, qc_confidence=None, line_config=LineConfig(**config),
            band_pp=profile.band_pp if configured else None, profile=profile if configured else None,
            quality_passed=row["quality_passed"], anomaly_flag=row["anomaly_flag"],
            check_policy=CheckPolicy(**manifest["check_policy"]),
        )
        outputs[variant] = {"raw_action": decision.action, "action": decision.action,
                            "reason": decision.reason, **decision.record_fields()}
    return outputs


def summarize(rows, target, variant):
    count = len(rows)
    actions = Counter(row["outputs"][variant]["action"] for row in rows)
    confusion = {truth: dict(Counter(
        row["outputs"][variant]["action"] for row in rows
        if (row["gt_pct"] >= target) == (truth == "at_or_above_target")
    )) for truth in ("below_target", "at_or_above_target")}
    correct = sum((row["outputs"][variant]["action"] == "passage" and row["gt_pct"] >= target)
                  or (row["outputs"][variant]["action"] == "continue" and row["gt_pct"] < target)
                  for row in rows)
    decided = sum(row["outputs"][variant]["action"] in ("continue", "passage") for row in rows)
    return {
        "n_images": count, "independent_biological_units": None,
        "n_at_or_above_target": sum(row["gt_pct"] >= target for row in rows),
        "actions": {action: actions[action] for action in ("continue", "passage", "feed", "human_review", "reimage")},
        "threshold_action_confusion": confusion,
        "early_passage": confusion["below_target"].get("passage", 0),
        "ready_called_continue": confusion["at_or_above_target"].get("continue", 0),
        "threshold_correct_decided_n": correct, "threshold_decided_n": decided,
        "threshold_correct_decided_coverage": correct / count if count else None,
        "threshold_accuracy_among_decided": correct / decided if decided else None,
        "review_fraction": actions["human_review"] / count if count else None,
        "reimage_fraction": actions["reimage"] / count if count else None,
        "passage_evidence": ("insufficient_no_target_reaching_cases" if not any(
            row["gt_pct"] >= target for row in rows) else "descriptive_only_not_action_validation"),
        "uncertainty_interval": None,
    }


def replay(bundle):
    manifest, inputs, baseline = load_bundle(bundle)
    decisions = []
    summaries = []
    transitions = []
    for target in manifest["targets_pct"]:
        for timing_name, timing in manifest["timing_scenarios"].items():
            group = [{
                **row, "target_pct": target, "timing_scenario": timing_name,
                "outputs": replay_row(row, manifest, baseline, target, timing),
            } for row in inputs]
            decisions.extend(group)
            subsets = {
                "all": group,
                "dense_gt_ge_40": [row for row in group if row["gt_pct"] >= manifest["subset_rules"]["dense_gt_min_pct"]],
                "near_target_plus_minus_10": [row for row in group if abs(row["gt_pct"] - target)
                                             <= manifest["subset_rules"]["near_target_half_width_pp"]],
            }
            for subset_name, subset in subsets.items():
                for variant in VARIANTS:
                    summaries.append({
                        "target_pct": target, "timing_scenario": timing_name,
                        "subset": subset_name, "variant": variant, **summarize(subset, target, variant),
                    })
            for before, after in zip(VARIANTS, VARIANTS[1:]):
                counts = Counter(f"{row['outputs'][before]['action']} -> {row['outputs'][after]['action']}"
                                 for row in group)
                transitions.append({"target_pct": target, "timing_scenario": timing_name,
                                    "before": before, "after": after, "actions": dict(sorted(counts.items()))})
    measurement = {}
    for key in ("pct_cut0", "pct_configured"):
        errors = [row[key] - row["gt_pct"] for row in inputs]
        measurement[key] = {"n": len(errors), "mae_pp": sum(abs(value) for value in errors) / len(errors),
                            "bias_pp": sum(errors) / len(errors)}
    report = {
        "comparison_kind": manifest["comparison_kind"], "manifest_sha256": digest(bundle / "manifest.json"),
        "measurement": measurement, "summaries": summaries, "sequential_transitions": transitions,
        "metric_boundary": "Threshold agreement only. A mask is not an independent adjudication of feeding, health, passage timing or action eligibility. Correct continue coverage is not automation coverage.",
        "limitations": manifest["limitations"], "uncertainty": manifest["uncertainty"],
    }
    return decisions, report


def markdown_report(report):
    lines = [
        "# Internal EVICAN cached-policy replay", "",
        "**Not an end-to-end v2/v4 benchmark. Not fine-tuning evidence. No host action authorized.**", "",
        "33 previously reused evaluation images with expert-mask confluency; biological independent units unknown.",
        "Same cached maps read at two cutoffs, with original unscaled classifier logits. Timing is unknown or explicitly assumed.",
        "Quality/anomaly checks are missing, not passed. Current outputs remain advisory. `hold` is normalized to `continue` only for counting.", "",
        "## Measurement, not a model upgrade", "",
    ]
    for key, value in report["measurement"].items():
        lines.append(f"- {key}: MAE {value['mae_pp']:.2f} pp; bias {value['bias_pp']:+.2f} pp (n={value['n']}).")
    lines += [
        "", "The configured cutoff is −3.5 with a 29.4 pp band. Selection was not fully blind; no new tuning occurred.",
        "The fine-tuned experimental model is not used. The original v2 synthetic headline cannot be regenerated.", "",
        "## Full cohort and dense-subset burden", "",
        "| Target | Timing | Subset | Variant | n | GT ready | Continue | Passage | Review | Reimage | Early passage | Ready → continue | Correct decided / all |",
        "|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in report["summaries"]:
        counts = row["actions"]
        lines.append(f"| {row['target_pct']:g} | {row['timing_scenario']} | {row['subset']} | {row['variant']} | "
                     f"{row['n_images']} | {row['n_at_or_above_target']} | {counts['continue']} | "
                     f"{counts['passage']} | {counts['human_review']} | {counts['reimage']} | "
                     f"{row['early_passage']} | {row['ready_called_continue']} | "
                     f"{row['threshold_correct_decided_n']}/{row['n_images']} |")
    lines += ["", report["metric_boundary"], "",
              "Empty subsets have null rates, not a zero-error success. At 80% there are no target-reaching cases.",
              "Dense means expert GT ≥40%; near-target means within ±10 pp. These are descriptive slices, not new acceptance thresholds.",
              "Uncertainty intervals are withheld: biological unit IDs and an independent prospective sample are absent.",
              "Review and reimage counts are separate; unavailable quality checks cannot establish a good reimage rate.", "",
              "## Sequential ablations", "",
              "1. baseline → baseline_classifier_demoted: only the classifier trigger is neutralized with normal/1.0.",
              "2. baseline_classifier_demoted → current_uncalibrated: current policy at the same zero-cutoff reading, with unavailable checks explicit.",
              "3. current_uncalibrated → current_configured: configured reading and band together; not a new model or isolated band effect.",
              "", "Full action transitions, confusion counts and denominators are in `report.json`; every paired output/reason is in `decisions.jsonl`.", "",
              "## Limits and remaining evidence", ""]
    lines += [f"- {limitation}" for limitation in report["limitations"]]
    return "\n".join(lines) + "\n"


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundle", type=Path, default=DEFAULT_BUNDLE)
    parser.add_argument("--freeze", action="store_true", help="Create a new bundle from local caches; never overwrite one")
    parser.add_argument("--out", type=Path, help="New output directory (required unless --freeze)")
    args = parser.parse_args(argv)
    if args.out is None:
        if not args.freeze:
            parser.error("--out is required; use a new directory to preserve historical results")
        args.out = args.bundle / "replay"
    if args.out.exists():
        parser.error("--out must not already exist")
    if args.freeze:
        freeze(args.bundle)
    decisions, report = replay(args.bundle)
    args.out.mkdir(parents=True)
    write_json(args.out / "report.json", report)
    (args.out / "decisions.jsonl").write_text("".join(
        json.dumps(row, sort_keys=True, allow_nan=False) + "\n" for row in decisions))
    (args.out / "report.md").write_text(markdown_report(report))
    print(json.dumps({"comparison_kind": report["comparison_kind"], "paired_rows": len(decisions),
                      "output": str(args.out), "inference_run": False}))


if __name__ == "__main__":
    main()
