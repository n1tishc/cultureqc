"""
cultureqc.rules — Deterministic action decisions.

The rules layer decides; the VLM/template recommends. Both are logged.
This separation is the GMP-friendly design: a human can read the rules,
predict the output, and audit the decision without understanding the model.

Order of precedence:
  1. QC flag != normal with confidence >= threshold -> human_review
     (skipped when qc_flag is None: the classifier is demoted, configs/qc.yaml)
  2. Confluency confidence < 0.3 -> human_review (uncertain measurement)
  3. Confluency >= target and hours since passage >= min_hours -> passage,
     unless the per-image anomaly check flagged the image: then human_review
     (a flagged flask is never passaged automatically; the flag does not
     change hold or feed, where nothing irreversible happens)
  4. Hours since feed >= feed_interval -> feed
  5. Else -> hold

Usage:
    from cultureqc.rules import decide, load_line_config, DEFAULT_CONFIG

    action, reason = decide(
        confluency_pct=78.2,
        confluency_confidence=0.91,
        qc_flag="normal",
        qc_confidence=0.97,
        line_config=DEFAULT_CONFIG,
        hours_since_passage=48,
        hours_since_feed=12,
    )
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field

# Written into every record's decided_by. v0.3 (2026-09-28): the anomaly flag
# holds a passage for human review (rule 3).
RULES_VERSION = "rules_v0.3"

# ---------------------------------------------------------------------------
# Per-line configuration
# ---------------------------------------------------------------------------

@dataclass
class LineConfig:
    """Per-cell-line decision thresholds. Load from YAML or use defaults."""
    cell_line: str = "unknown"
    target_confluency: float = 80.0
    min_hours_since_passage: float = 24.0
    feed_interval_h: float = 24.0
    qc_review_threshold: float = 0.7
    confluency_confidence_floor: float = 0.3


DEFAULT_CONFIG = LineConfig()

AMBIGUITY_TOOLTIP = ("Share of pixels near the cell/background cutoff, as min(1, 4 × share within ±1 logit); "
                     "rises with density; a review trigger, not a probability that the reading is right.")


def boundary_ambiguity(confluency_confidence: float) -> float:
    """What the console and the site show for the record's confluency
    `confidence`: 1 − confidence = min(1, 4 × share of pixels within ±1 logit
    of the cutoff), higher = more ambiguous. Shown under this name because the
    score tracks density, not the reading's error (results/confidence_vs_error.md).
    The record keeps the field `confidence`; the rules still compare it with
    the floor, so "confidence below 0.30" is "ambiguity above 0.70"."""
    return round(1.0 - float(confluency_confidence), 3)


def load_line_config(yaml_path: str) -> LineConfig:
    """Load a per-line YAML config. Falls back to defaults for missing fields."""
    try:
        import yaml
    except ImportError:
        raise ImportError("pip install pyyaml to use YAML configs")

    with open(yaml_path) as f:
        data = yaml.safe_load(f) or {}

    return LineConfig(
        cell_line=data.get("cell_line", "unknown"),
        target_confluency=data.get("target_confluency", 80.0),
        min_hours_since_passage=data.get("min_hours_since_passage", 24.0),
        feed_interval_h=data.get("feed_interval_h", 24.0),
        qc_review_threshold=data.get("qc_review_threshold", 0.7),
        confluency_confidence_floor=data.get("confluency_confidence_floor", 0.3),
    )


def load_all_configs(config_dir: str) -> dict[str, LineConfig]:
    """Load all YAML configs from a directory, keyed by cell_line name."""
    configs = {}
    if not os.path.isdir(config_dir):
        return configs
    for fname in os.listdir(config_dir):
        if fname.endswith((".yaml", ".yml")):
            cfg = load_line_config(os.path.join(config_dir, fname))
            configs[cfg.cell_line] = cfg
    return configs


# ---------------------------------------------------------------------------
# Decision logic
# ---------------------------------------------------------------------------

def decide(
    confluency_pct: float,
    confluency_confidence: float,
    qc_flag: str | None,
    qc_confidence: float | None,
    line_config: LineConfig | None = None,
    hours_since_passage: float | None = None,
    hours_since_feed: float | None = None,
    anomaly_flag: bool | None = None,
) -> tuple[str, str]:
    """
    Deterministic action decision.

    qc_flag=None leaves the classifier out of the decision (rule 1 is
    skipped); pass that when it is demoted rather than a made-up "normal".
    anomaly_flag=None (the check was unavailable) leaves rule 3 as a plain
    confluency check; pass the flag whenever the anomaly check ran.

    Returns:
        (action, reason) where action is one of:
        "human_review", "passage", "feed", "hold"
    """
    cfg = line_config or DEFAULT_CONFIG

    # 1. QC flag check (highest priority)
    if qc_flag is not None and qc_flag != "normal" and qc_confidence >= cfg.qc_review_threshold:
        return (
            "human_review",
            f"QC flag '{qc_flag}' at {qc_confidence:.0%} confidence "
            f"(threshold {cfg.qc_review_threshold:.0%}). "
            f"Automated decisions paused until human review."
        )

    # 2. Low confluency confidence -> uncertain measurement
    if confluency_confidence < cfg.confluency_confidence_floor:
        return (
            "human_review",
            f"Confluency confidence {confluency_confidence:.2f} is below "
            f"floor {cfg.confluency_confidence_floor:.2f}. "
            f"Image may be ambiguous; recommend manual inspection."
        )

    # 3. Passage check
    passage_ready = confluency_pct >= cfg.target_confluency
    hours_ok = (
        hours_since_passage is None
        or hours_since_passage >= cfg.min_hours_since_passage
    )
    if passage_ready and hours_ok and anomaly_flag:
        return (
            "human_review",
            f"Confluency {confluency_pct:.1f}% >= target {cfg.target_confluency:.0f}%, "
            f"but the anomaly check flagged this image; passage held for human review."
        )
    if passage_ready and hours_ok:
        return (
            "passage",
            f"Confluency {confluency_pct:.1f}% >= target {cfg.target_confluency:.0f}%"
            + (f", {hours_since_passage:.0f}h since last passage"
               if hours_since_passage is not None else "")
            + "."
        )

    # 4. Feed check
    if hours_since_feed is not None and hours_since_feed >= cfg.feed_interval_h:
        return (
            "feed",
            f"Feed interval {cfg.feed_interval_h:.0f}h elapsed "
            f"({hours_since_feed:.0f}h since last feed). "
            f"Confluency {confluency_pct:.1f}% (target {cfg.target_confluency:.0f}%)."
        )

    # 5. Default: hold
    return (
        "hold",
        f"Confluency {confluency_pct:.1f}% below target {cfg.target_confluency:.0f}%. "
        f"No action needed."
    )
