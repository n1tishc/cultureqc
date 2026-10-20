"""
cultureqc.profiles — confluency calibration profiles, one per imaging setup.

A profile holds what turns Cellpose-SAM's cell-probability map into a reading
for one imaging setup: the logit cutoff, and the 90% error band measured on
held-out labelled images from that setup (results/confluency_profiles.md).
The cutoff that fits depends on the microscope, so it is configuration under
change control, not a code default: every record names the profile and its
SHA-256, and replacing a profile is a `change` event in the chain
(culture/records.py).

A setup with no labelled images gets the `uncalibrated` profile, or a named
entry with status `uncalibrated` that also names its quality gate: Cellpose's
default cutoff and no band, so the rules never passage on its reading alone
(culture/rules.py). A profile that did not pass its pre-registered criteria
on held-out images (status `failed` or `in_domain_check`) keeps its fitted
values for the record (`fitted_cutoff`, `fitted_band_pp`) but reads like an
uncalibrated setup: `cutoff` 0.0 and `band_pp` null. The entries are written
from results/confluency_profiles.json by scripts/write_profiles_config.py,
and tests/test_profiles_config.py checks that they still match.

Since rules_v0.6, these are measurement statuses only. Passage additionally
requires explicit action approval and matching validated decision scope;
the generated historical profiles have neither. Unknown explicit IDs raise.

    from culture.profiles import get_profile
    p = get_profile("msc_phase")
    p.cutoff, p.band_pp, p.interval(62.0), p.sha256
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import re
from copy import deepcopy
from dataclasses import dataclass, field

import yaml

PROFILES_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "configs",
                             "confluency_profiles.yaml")
UNCALIBRATED = "uncalibrated"


def _number(value, name, minimum=None, maximum=None):
    if (isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value)
            or (minimum is not None and value < minimum) or (maximum is not None and value > maximum)):
        raise ValueError(f"Invalid profile {name}: {value!r}")


def _validate_entry(entry):
    if not isinstance(entry, dict):
        raise ValueError("Profile entry must be a mapping")
    status = entry.get("status")
    if not isinstance(status, str) or status not in {"validated", "failed", "in_domain_check", "uncalibrated"}:
        raise ValueError("Invalid profile status")
    _number(entry.get("cutoff"), "cutoff")
    band = entry.get("band_pp")
    if status == "validated":
        _number(band, "band_pp", 0, 100)
    elif band is not None or entry["cutoff"] != 0:
        raise ValueError("Nonvalidated measurement profiles require cutoff 0 and no active band")
    if entry.get("fitted_cutoff") is not None:
        _number(entry["fitted_cutoff"], "fitted_cutoff")
    if entry.get("fitted_band_pp") is not None:
        _number(entry["fitted_band_pp"], "fitted_band_pp", 0, 100)
    acceptance = entry.get("acceptance", {})
    if (not isinstance(acceptance, dict)
            or any(not isinstance(value, str) or value not in {"pass", "fail", "not measurable"} for value in acceptance.values())
            or (status == "validated" and "fail" in acceptance.values())):
        raise ValueError("Invalid measurement acceptance/status combination")
    eligibility = entry.get("action_eligibility", {"status": "unsupported", "reason": "Legacy profile has no action approval"})
    if (not isinstance(eligibility, dict) or not isinstance(eligibility.get("status"), str)
            or eligibility["status"] not in {"eligible", "unsupported"}
            or not isinstance(eligibility.get("reason"), str) or not eligibility["reason"].strip()):
        raise ValueError("Invalid profile action_eligibility")
    scope = entry.get("validated_scope")
    if eligibility["status"] == "unsupported":
        if scope is not None:
            raise ValueError("Unsupported action profile must not claim a validated decision scope")
        return
    if status != "validated" or not isinstance(scope, dict):
        raise ValueError("Eligible action profile requires calibrated measurement and validated_scope")
    if set(scope) != {"setup_id", "cell_line", "model_sha256", "reading_range_pct", "target_range_pct"}:
        raise ValueError("Invalid validated_scope fields")
    if any(entry.get("acceptance", {}).get(criterion) != "pass" for criterion in ("A1", "A2", "A3", "A4", "A5")):
        raise ValueError("Eligible action profile requires all A1-A5 criteria to pass")
    if not isinstance(eligibility.get("approval_ref"), str) or not eligibility["approval_ref"].strip():
        raise ValueError("Eligible action profile requires approval_ref")
    for name in ("setup_id", "cell_line"):
        if not isinstance(scope.get(name), str) or not scope[name].strip() or scope[name] in {"unknown", "*"}:
            raise ValueError(f"Invalid validated_scope {name}")
    if not isinstance(scope.get("model_sha256"), str) or not re.fullmatch(r"[0-9a-f]{64}", scope["model_sha256"]):
        raise ValueError("Invalid validated_scope model_sha256")
    for name in ("reading_range_pct", "target_range_pct"):
        bounds = scope.get(name)
        if not isinstance(bounds, list) or len(bounds) != 2:
            raise ValueError(f"Invalid validated_scope {name}")
        for value in bounds:
            _number(value, name, 0, 100)
        if bounds[0] > bounds[1]:
            raise ValueError(f"Reversed validated_scope {name}")


@dataclass(frozen=True)
class Profile:
    id: str
    cutoff: float
    band_pp: float | None
    status: str                      # "validated" | "failed" | "in_domain_check" | "uncalibrated"
    description: str
    quality: str | None = None       # configs/quality.yaml entry calibrated on this setup, if any
    entry: dict = field(default_factory=dict, compare=False, hash=False)

    @property
    def sha256(self) -> str:
        """SHA-256 of the profile's canonical JSON, id included: what the record pins."""
        blob = json.dumps({"id": self.id, **self.entry}, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
        return hashlib.sha256(blob.encode()).hexdigest()

    @property
    def calibrated(self) -> bool:
        return self.band_pp is not None

    def interval(self, pct: float) -> list[float] | None:
        if self.band_pp is None:
            return None
        return [round(max(0.0, pct - self.band_pp), 2), round(min(100.0, pct + self.band_pp), 2)]

    def record_fields(self) -> dict:
        return {"id": self.id, "sha256": self.sha256, "status": self.status, "cutoff": self.cutoff,
                "band_pp": self.band_pp, "measurement_calibrated": self.calibrated,
                "validated_scope": deepcopy(self.entry.get("validated_scope")),
                "action_eligibility": deepcopy(self.entry.get("action_eligibility", {
                    "status": "unsupported", "reason": "Legacy profile has no action approval"}))}

    def passage_eligibility(self, reading_pct: float, target_pct: float, context: dict | None = None) -> dict:
        """Evaluate approved decision scope, never infer it from a fitted band."""
        _validate_entry(self.entry)
        if (self.cutoff, self.band_pp, self.status) != (self.entry["cutoff"], self.entry["band_pp"], self.entry["status"]):
            raise ValueError("Profile measurement fields differ from its pinned entry")
        _number(reading_pct, "reading_pct", 0, 100)
        _number(target_pct, "target_pct", 0, 100)
        context = context or {}
        result = {"eligible": False, "reason": "Profile has no approved passage eligibility",
                  "reading_pct": reading_pct, "target_pct": target_pct,
                  **{name: context.get(name) for name in ("setup_id", "cell_line", "model_sha256")}}
        policy = self.entry.get("action_eligibility", {})
        if policy.get("status") != "eligible":
            result["reason"] = policy.get("reason", result["reason"])
            return result
        scope = self.entry["validated_scope"]
        for name in ("setup_id", "cell_line", "model_sha256"):
            if context.get(name) != scope[name]:
                result["reason"] = f"Missing or mismatched {name} for validated decision scope"
                return result
        for name, value in (("reading_range_pct", reading_pct), ("target_range_pct", target_pct)):
            if not scope[name][0] <= value <= scope[name][1]:
                result["reason"] = f"Outside validated decision scope: {name}"
                return result
        result.update(eligible=True, reason="Matches approved passage decision scope")
        return result


_cache: dict[str, dict[str, Profile]] = {}


def load_profiles(path: str = PROFILES_PATH) -> dict[str, Profile]:
    from culture.provenance import capturing_configs, load_yaml
    cache = {} if capturing_configs() else _cache
    if path not in cache:
        doc = load_yaml(path) or {}
        if (not isinstance(doc, dict) or type(doc.get("version")) is not int
                or doc["version"] not in (1, 2) or not isinstance(doc.get("profiles"), dict)):
            raise ValueError("Invalid calibration profile document")
        out = {}
        for pid, e in (doc.get("profiles") or {}).items():
            if not isinstance(pid, str) or not pid.strip():
                raise ValueError("Invalid profile id")
            _validate_entry(e)
            out[pid] = Profile(id=pid, cutoff=float(e["cutoff"]),
                               band_pp=None if e.get("band_pp") is None else float(e["band_pp"]),
                               status=e["status"], description=e.get("description", ""),
                               quality=e.get("quality"), entry=e)
        if UNCALIBRATED not in out:
            raise ValueError(f"{path} has no `{UNCALIBRATED}` profile")
        cache[path] = out
    return cache[path]


def get_profile(profile_id: str | None = None, path: str = PROFILES_PATH) -> Profile:
    """None selects uncalibrated; an unknown explicit id is a configuration error."""
    profiles = load_profiles(path)
    requested = UNCALIBRATED if profile_id is None else profile_id
    if requested not in profiles:
        raise ValueError(f"Unknown confluency profile: {requested!r}")
    return profiles[requested]


def choices(path: str = PROFILES_PATH) -> list[tuple[str, str]]:
    """(label, id) pairs for a setup picker: the validated profiles, the named setups without a
    calibration (they still run their quality gate), then the generic uncalibrated entry."""
    ps = load_profiles(path)
    order = ([p for p in ps if ps[p].status == "validated"] +
             [p for p in ps if ps[p].status == "uncalibrated" and p != UNCALIBRATED] + [UNCALIBRATED])
    return [(ps[p].entry.get("label", p), p) for p in order]
