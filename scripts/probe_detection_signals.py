#!/usr/bin/env python3
"""Offline experimental signal probes; stdout JSON only, no active threshold changes."""

import argparse
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import sys

import numpy as np

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))


def image_probe(args):
    import cv2

    from culture.anomaly_coverage import coverage_plan, patch_scorer, score_coverage

    image_bytes = args.image.read_bytes()
    if not image_bytes:
        raise ValueError("image is empty")
    try:
        frame = cv2.imdecode(np.frombuffer(image_bytes, dtype=np.uint8), cv2.IMREAD_UNCHANGED)
    except cv2.error as error:
        raise ValueError("image cannot be decoded") from error
    if frame is None:
        raise ValueError("image cannot be decoded")
    if frame.ndim == 3 and frame.shape[2] == 3:
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    result = {"input_sha256": hashlib.sha256(image_bytes).hexdigest(),
              "status": "plan_only", "used_in_decision": False,
              **coverage_plan(frame, max_tiles=args.max_tiles)}
    if not args.score:
        return result
    if args.model_dir is None or args.banks is None or args.config is None or args.confluency is None:
        raise ValueError("--score requires --model-dir, --banks, --config and --confluency")
    if not np.isfinite(args.confluency) or not 0 <= args.confluency <= 100:
        raise ValueError("confluency must be finite and between 0 and 100")
    if not args.model_dir.is_dir():
        raise ValueError("--model-dir must be an existing local snapshot directory")
    import yaml

    from culture.anomaly import bank_hash, bin_index, bin_label
    from culture.records import hash_file

    config_bytes = args.config.read_bytes()
    try:
        config = yaml.safe_load(config_bytes)
    except yaml.YAMLError as error:
        raise ValueError("anomaly configuration is not valid YAML") from error
    if config["method"]["backbone"] != "facebook/dinov2-small":
        raise ValueError("only the DINOv2-small reference-bank contract is supported")
    with np.load(args.banks, allow_pickle=False) as stored:
        banks = {name: stored[name] for name in stored.files}
    if bank_hash([banks[name] for name in sorted(banks)]) != config["bank"]["sha256"]:
        raise ValueError("bank hash does not match supplied configuration")
    label = bin_label(bin_index(args.confluency, config["bins"]["edges"]), config["bins"]["edges"])
    artifacts = {str(path.relative_to(args.model_dir)): hash_file(str(path))
                 for path in sorted(args.model_dir.rglob("*")) if path.is_file()}
    from transformers import AutoImageProcessor, AutoModel

    processor = AutoImageProcessor.from_pretrained(str(args.model_dir), local_files_only=True)
    model = AutoModel.from_pretrained(str(args.model_dir), local_files_only=True).eval()
    if model.config.model_type != "dinov2" or model.config.hidden_size != 384 or model.config.patch_size != 14:
        raise ValueError("model architecture does not match DINOv2-small banks")
    scorer = patch_scorer(model, processor, banks[f"bin_{label}"], top_frac=config["method"]["top_frac"])
    scored = score_coverage(frame, scorer, max_tiles=args.max_tiles)
    if any(hash_file(str(args.model_dir / path)) != digest for path, digest in artifacts.items()):
        raise ValueError("model snapshot changed during scoring; discard output")
    return {**result, **scored, "reference_bank_sha256": config["bank"]["sha256"],
            "reference_bin": label, "confluency_pct": args.confluency,
            "configuration_sha256": hashlib.sha256(config_bytes).hexdigest(),
            "model_artifacts": artifacts, "inference_device": "cpu",
            "reference_warning": "Architecture/hash recording is not model approval or spatial calibration."}


def growth_probe(args):
    from culture.growth_signal import frozen_growth_series

    raw = args.input.read_bytes()
    packet = json.loads(raw)
    signals = frozen_growth_series(
        packet["visits"], baseline_end=packet["baseline_end"], baseline_reason=packet["baseline_reason"],
        horizon_hours=packet["horizon_hours"], max_gap_hours=packet["max_gap_hours"],
        min_expected_growth_pp=packet["min_expected_growth_pp"],
    )
    return {"status": "experimental_uncalibrated", "used_in_decision": False,
            "input_sha256": hashlib.sha256(raw).hexdigest(), "signals": [asdict(signal) for signal in signals]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    image = commands.add_parser("coverage", help="plan coverage; optionally score with local model files")
    image.add_argument("image", type=Path)
    image.add_argument("--max-tiles", type=int, default=64)
    image.add_argument("--score", action="store_true")
    image.add_argument("--model-dir", type=Path)
    image.add_argument("--banks", type=Path)
    image.add_argument("--config", type=Path)
    image.add_argument("--confluency", type=float)
    growth = commands.add_parser("growth", help="replay a predeclared frozen baseline from JSON visits")
    growth.add_argument("input", type=Path)
    args = parser.parse_args()
    try:
        result = image_probe(args) if args.command == "coverage" else growth_probe(args)
        output = json.dumps(result, indent=2, allow_nan=False)
    except (OSError, ValueError, KeyError, TypeError, ImportError) as error:
        print(json.dumps({"status": "error", "reason": str(error), "used_in_decision": False}))
        return 1
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
