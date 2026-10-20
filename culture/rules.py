"""
cultureqc.rules — Deterministic action decisions.

The rules layer decides; the VLM/template recommends. Both are logged.
This separation is the GMP-friendly design: a human can read the rules,
predict the output, and audit the decision without understanding the model.

Order of precedence (rules_v0.7):
  1. QC flag != normal with confidence >= threshold -> human_review
     (skipped when qc_flag is None: the classifier is demoted, configs/qc.yaml)
  2. The image failed the quality gate -> reimage (no reading is acted on)
  3. Passage, read against the confluency profile's error band
     (culture/profiles.py; results/confluency_profiles.md), when enough
     hours have passed since the last passage:
       - reading − band >= target: passage only with approved matching
         decision scope; otherwise human_review. An anomaly flag also holds passage.
       - the band straddles the target: human_review (the reading can't say
         which side of the target the flask is on)
       - no band (an uncalibrated imaging setup) and reading >= target:
         human_review
  4. Hours since feed >= feed_interval -> feed
  5. Else -> advisory continue, never proof that no action is needed

Versions (decided_by in every record):
  rules_v0.7  explicit check requirements, missing timing, finite inputs and
              stable reason codes. All output is advisory, not host authorization.
  rules_v0.6  passage also requires explicit approved setup/model/cell-line
              scope covering the reading and target; a measured band alone
              never authorizes it. Historical measurement values are unchanged.
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
import math
from dataclasses import asdict, dataclass

from culture.profiles import Profile

RULES_VERSION = "rules_v0.7"
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
                     "rises with density; recorded for diagnosis, not a review trigger under rules_v0.5 or a probability that the reading is right.")


def boundary_ambiguity(confluency_confidence: float) -> float:
    """What the console and the site show for the record's confluency
    `confidence`: 1 − confidence = min(1, 4 × share of pixels within ±1 logit
    of the cutoff), higher = more ambiguous. Shown under this name because the
    score tracks density, not the reading's error (results/confidence_vs_error.md).
    The record keeps the field `confidence`; current rules do not compare it
    with a confidence floor."""
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

@dataclass(frozen=True)
class CheckPolicy:
    """Advisory check requirements; not an approval of a detector or setup.

    Image quality is always required for a passage candidate. The exploratory
    anomaly check is optional by default. A demoted classifier is explicitly
    not applicable in runtime callers. Required but unavailable checks block
    passage; optional checks still veto when their failure condition is met.
    """

    anomaly: str = "optional"
    qc: str = "optional"

    def requirements(self) -> dict[str, str]:
        requirements = {"quality": "required", **asdict(self)}
        if any(value not in ("required", "optional", "not_applicable") for value in requirements.values()):
            raise ValueError("Check requirements must be required, optional or not_applicable")
        return requirements


@dataclass(frozen=True)
class Decision:
    action: str
    reason: str
    reason_code: str
    checks: dict
    timing: dict
    warnings: list[str]

    def record_fields(self) -> dict:
        return {"reason_code": self.reason_code, "mode": "advisory", "host_actionable": False,
                "checks": self.checks, "timing": self.timing, "warnings": self.warnings}


def _finite_number(name, value, maximum=None):
    if (isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value)
            or value < 0 or (maximum is not None and value > maximum)):
        raise ValueError(f"{name} must be finite and nonnegative" +
                         (f" and at most {maximum}" if maximum is not None else ""))


def evaluate_decision(
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
    profile: Profile | None = None,
    setup_context: dict | None = None,
    check_policy: CheckPolicy | None = None,
) -> Decision:
    """Evaluate advisory rules and retain missing-check and timing provenance.

    None means unavailable, never a negative check. Passage candidates need
    known elapsed passage timing, matching approved scope and every required
    check. Confidence is validated for the record but does not gate confluency.
    Invalid inputs raise before any normal decision can be emitted.
    """
    cfg = line_config or DEFAULT_CONFIG
    target = cfg.target_confluency
    for name, value in (("confluency_pct", confluency_pct), ("target_confluency", target), ("band_pp", band_pp)):
        if name == "band_pp" and value is None:
            continue
        _finite_number(name, value, 100)
    for name, value in (("confluency_confidence", confluency_confidence),
                        ("qc_review_threshold", cfg.qc_review_threshold)):
        _finite_number(name, value, 1)
    if qc_confidence is not None:
        _finite_number("qc_confidence", qc_confidence, 1)
    for name, value in (("min_hours_since_passage", cfg.min_hours_since_passage),
                        ("feed_interval_h", cfg.feed_interval_h)):
        _finite_number(name, value)
    for name, value in (("hours_since_passage", hours_since_passage), ("hours_since_feed", hours_since_feed)):
        if value is not None:
            _finite_number(name, value)
    for name, value in (("quality_passed", quality_passed), ("anomaly_flag", anomaly_flag)):
        if value is not None and type(value) is not bool:
            raise ValueError(f"{name} must be a boolean or None")
    if qc_flag not in (None, "normal", "contamination_suspected", "detachment", "image_quality"):
        raise ValueError("Unknown QC flag")
    if quality_reasons is not None and (not isinstance(quality_reasons, list)
                                      or any(not isinstance(reason, str) for reason in quality_reasons)):
        raise ValueError("quality_reasons must be a list of strings")
    if profile is not None and profile.band_pp != band_pp:
        raise ValueError("Decision band must match the selected measurement profile")
    eligibility = (profile.passage_eligibility(confluency_pct, target, setup_context) if profile else
                   {"eligible": False, "reason": "No approved decision profile supplied"})
    requirements = (check_policy or CheckPolicy()).requirements()
    qc_available = qc_flag is not None and qc_confidence is not None
    qc_failed = qc_available and qc_flag != "normal" and qc_confidence >= cfg.qc_review_threshold
    observed = {"quality": quality_passed, "anomaly": None if anomaly_flag is None else not anomaly_flag,
                "qc": not qc_failed if qc_available else None}
    checks = {}
    for name, requirement in requirements.items():
        if requirement == "not_applicable":
            if observed[name] is not None or (name == "qc" and (qc_flag is not None or qc_confidence is not None)):
                raise ValueError(f"{name} is not applicable but a decision input was supplied")
            status = "not_applicable"
        else:
            status = "unavailable" if observed[name] is None else "passed" if observed[name] else "failed"
        checks[name] = {"requirement": requirement, "status": status}
    timing = {}
    for name, hours, interval in (("passage", hours_since_passage, cfg.min_hours_since_passage),
                                  ("feed", hours_since_feed, cfg.feed_interval_h)):
        timing[name] = {"hours": hours, "interval_h": interval,
                        "status": "unknown" if hours is None else "elapsed" if hours >= interval else "held"}
    warnings = [f"{check['requirement']}_{name}_unavailable" for name, check in checks.items()
                if check["status"] == "unavailable"]
    warnings += [f"{name}_time_unknown" for name, value in timing.items() if value["status"] == "unknown"]
    if not eligibility["eligible"]:
        warnings.append("unsupported_action_scope")

    def result(action, code, explanation):
        if action in ("feed", "continue"):
            if not eligibility["eligible"]:
                explanation += " No approved action scope; a low reading is not proof that no action is needed."
            if any(value["status"] == "unavailable" for value in checks.values()):
                explanation += " Some checks are unavailable; this is not a culture-health clearance."
            if timing["passage"]["status"] == "unknown":
                explanation += " Passage timing is unknown; passage eligibility cannot be established."
            if timing["feed"]["status"] == "unknown":
                explanation += " Feed timing is unknown; whether feeding is due cannot be established."
        explanation += " Advisory only; host review and authorization are required before acting."
        return Decision(action, explanation, code, checks, timing, warnings)

    if qc_failed:
        return result("human_review", "qc_flagged",
            f"QC flag '{qc_flag}' at {qc_confidence:.0%} confidence "
            f"(threshold {cfg.qc_review_threshold:.0%}). "
            f"Automated decisions paused until human review."
        )
    if quality_passed is False:
        why = ", ".join(r.replace("_", " ") for r in (quality_reasons or [])) or "quality gate failed"
        return result("reimage", "quality_failed", f"Image failed the quality gate ({why}); re-image before any decision.")
    if qc_flag not in (None, "normal") and qc_confidence is None:
        return result("human_review", "qc_incomplete", "QC raised a flag without its confidence; review the incomplete check.")

    hours_ok = timing["passage"]["status"] == "elapsed"
    potentially_ready = confluency_pct + (band_pp or 0) >= target
    if potentially_ready and timing["passage"]["status"] == "unknown":
        return result("human_review", "passage_time_unknown", "Passage timing is unknown; the minimum interval cannot be verified.")
    if hours_ok and band_pp is None and confluency_pct >= target:
        held = " The anomaly check also flagged this image." if anomaly_flag else ""
        return result("human_review", "measurement_uncalibrated",
            f"Confluency {confluency_pct:.1f}% >= target {target:.0f}%, but this imaging setup has no "
            f"calibration profile, so the reading has no measured error; passage needs a person.{held}"
        )
    if hours_ok and band_pp is not None:
        lower, upper = confluency_pct - band_pp, confluency_pct + band_pp
        if lower >= target and anomaly_flag:
            return result("human_review", "anomaly_flagged",
                f"Confluency {confluency_pct:.1f}% (±{band_pp:.1f} pp) >= target {target:.0f}%, "
                f"but the anomaly check flagged this image; passage held for human review."
            )
        if lower >= target:
            if not eligibility["eligible"]:
                return result("human_review", "passage_scope_unsupported", f"Calibrated reading retained, but passage eligibility is unsupported: "
                        f"{eligibility['reason']}; passage needs a person.")
            missing = [name for name, check in checks.items()
                       if check["requirement"] == "required" and check["status"] == "unavailable"]
            if missing:
                return result("human_review", "required_check_unavailable",
                              f"Required passage checks unavailable: {', '.join(missing)}; missing is not a passing result.")
            return result("passage", "passage_candidate",
                          f"Confluency {confluency_pct:.1f}% (±{band_pp:.1f} pp) >= target {target:.0f}%, "
                          f"{hours_since_passage:g}h since last passage.")
        if upper >= target:
            return result("human_review", "target_within_error_band",
                f"Confluency {confluency_pct:.1f}% is within its error band (±{band_pp:.1f} pp) of the "
                f"target {target:.0f}%: the reading can't tell which side of the target the flask is on; "
                f"recommend a person checks."
            )
    passage_hold = (f"Passage interval not elapsed ({hours_since_passage:g}h < {cfg.min_hours_since_passage:g}h). "
                    if timing["passage"]["status"] == "held" else "")
    if timing["feed"]["status"] == "elapsed":
        return result("feed", "feed_due", passage_hold + f"Feed interval {cfg.feed_interval_h:g}h elapsed "
                      f"({hours_since_feed:g}h since last feed). Confluency reading {confluency_pct:.1f}% (target {target:.0f}%).")
    if passage_hold:
        return result("continue", "passage_interval_hold", passage_hold +
                      f"Confluency reading {confluency_pct:.1f}% (target {target:.0f}%). Continue monitoring pending host review.")
    return result("continue", "monitor_advisory",
                  f"Confluency reading {confluency_pct:.1f}% (target {target:.0f}%); continue monitoring pending host review.")


def decide(*args, **kwargs) -> tuple[str, str]:
    """Compatibility tuple API; use evaluate_decision for structured provenance."""
    decision = evaluate_decision(*args, **kwargs)
    return decision.action, decision.reason
