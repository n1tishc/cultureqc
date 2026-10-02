"""
cultureqc.rules — Deterministic action decisions.

The rules layer decides; the VLM/template recommends. Both are logged.
This separation is the GMP-friendly design: a human can read the rules,
predict the output, and audit the decision without understanding the model.

Order of precedence (rules_v0.5):
  1. QC flag != normal with confidence >= threshold -> human_review
     (skipped when qc_flag is None: the classifier is demoted, configs/qc.yaml)
  2. The image failed the quality gate -> reimage (no reading is acted on)
  3. Passage, read against the confluency profile's error band
     (culture/profiles.py; results/confluency_profiles.md), when enough
     hours have passed since the last passage:
       - reading − band >= target: passage, unless the per-image anomaly
         check flagged the image, then human_review
       - the band straddles the target: human_review (the reading can't say
         which side of the target the flask is on)
       - no band (an uncalibrated imaging setup) and reading >= target:
         human_review
  4. Hours since feed >= feed_interval -> feed
  5. Else -> continue (keep culturing; no action now)

Versions (decided_by in every record):
  rules_v0.5  passage reads the profile's error band; the boundary-ambiguity
              floor no longer decides anything (it tracks density, not error:
              results/confidence_vs_error.md) and stays in the record; a
              failed quality gate gives `reimage`.
  rules_v0.4  label-only change: `hold` renamed `continue` (it read as "put
              the flask on hold"), and rule 2's reason names boundary
              ambiguity. Decisions identical to v0.3.
  rules_v0.3  an anomaly flag turns passage into human_review (owner
              decision, 2026-09-28).

Usage:
    from cultureqc.rules import decide, load_line_config, DEFAULT_CONFIG

    action, reason = decide(
        confluency_pct=78.2,
        confluency_confidence=0.91,
        qc_flag=None,
        qc_confidence=None,
        line_config=DEFAULT_CONFIG,
        hours_since_passage=48,
        hours_since_feed=12,
        band_pp=6.0,
        quality_passed=True,
    )
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field

# Written into every record's decided_by. v0.5: passage reads the confluency
# profile's error band; a failed quality gate gives reimage.
RULES_VERSION = "rules_v0.5"
ACTIONS = ("passage", "feed", "continue", "human_review", "reimage")

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
    confluency_confidence_floor: float = 0.3                # rules_v0.4 and earlier; not used from v0.5


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
    band_pp: float | None = None,
    quality_passed: bool | None = None,
    quality_reasons: list[str] | None = None,
) -> tuple[str, str]:
    """
    Deterministic action decision.

    qc_flag=None leaves the classifier out of the decision (rule 1 is
    skipped); pass that when it is demoted rather than a made-up "normal".
    anomaly_flag=None (the check was unavailable) leaves rule 3 as a plain
    confluency check. band_pp is the confluency profile's 90% error band;
    None means the imaging setup is uncalibrated. quality_passed=None means
    no quality gate is calibrated for the setup, so rule 2 is skipped.
    confluency_confidence (1 − boundary ambiguity) is accepted for the
    record and no longer decides anything.

    Returns:
        (action, reason) where action is one of ACTIONS.
    """
    cfg = line_config or DEFAULT_CONFIG
    T = cfg.target_confluency

    # 1. QC flag check (highest priority; skipped while the classifier is demoted)
    if qc_flag is not None and qc_flag != "normal" and qc_confidence >= cfg.qc_review_threshold:
        return (
            "human_review",
            f"QC flag '{qc_flag}' at {qc_confidence:.0%} confidence "
            f"(threshold {cfg.qc_review_threshold:.0%}). "
            f"Automated decisions paused until human review."
        )

    # 2. Quality gate: an image that failed it is not read for a decision
    if quality_passed is False:
        why = ", ".join(r.replace("_", " ") for r in (quality_reasons or [])) or "quality gate failed"
        return ("reimage", f"Image failed the quality gate ({why}); re-image before any decision.")

    # 3. Passage, against the error band
    hours_ok = hours_since_passage is None or hours_since_passage >= cfg.min_hours_since_passage
    since = f", {hours_since_passage:.0f}h since last passage" if hours_since_passage is not None else ""
    if hours_ok and band_pp is None and confluency_pct >= T:
        held = " The anomaly check also flagged this image." if anomaly_flag else ""
        return (
            "human_review",
            f"Confluency {confluency_pct:.1f}% >= target {T:.0f}%, but this imaging setup has no "
            f"calibration profile, so the reading has no measured error; passage needs a person.{held}"
        )
    if hours_ok and band_pp is not None:
        lo, hi = confluency_pct - band_pp, confluency_pct + band_pp
        if lo >= T and anomaly_flag:
            return (
                "human_review",
                f"Confluency {confluency_pct:.1f}% (±{band_pp:.1f} pp) >= target {T:.0f}%, "
                f"but the anomaly check flagged this image; passage held for human review."
            )
        if lo >= T:
            return ("passage", f"Confluency {confluency_pct:.1f}% (±{band_pp:.1f} pp) >= target {T:.0f}%{since}.")
        if hi >= T:
            return (
                "human_review",
                f"Confluency {confluency_pct:.1f}% is within its error band (±{band_pp:.1f} pp) of the "
                f"target {T:.0f}%: the reading can't tell which side of the target the flask is on; "
                f"recommend a person checks."
            )

    # 4. Feed check
    if hours_since_feed is not None and hours_since_feed >= cfg.feed_interval_h:
        return (
            "feed",
            f"Feed interval {cfg.feed_interval_h:.0f}h elapsed "
            f"({hours_since_feed:.0f}h since last feed). "
            f"Confluency {confluency_pct:.1f}% (target {T:.0f}%)."
        )

    # 5. Default: continue culturing
    return ("continue", f"Confluency {confluency_pct:.1f}% below target {T:.0f}%. No action needed.")
