"""
cultureqc.profiles — confluency calibration profiles, one per imaging setup.

A profile holds what turns Cellpose-SAM's cell-probability map into a reading
for one imaging setup: the logit cutoff, and the 90% error band measured on
held-out labelled images from that setup (results/confluency_profiles.md).
The cutoff that fits depends on the microscope, so it is configuration under
change control, not a code default: every record names the profile and its
SHA-256, and replacing a profile is a `change` event in the chain
(culture/records.py).

A setup with no labelled images gets the `uncalibrated` profile: Cellpose's
default cutoff and no band, so the rules never passage on its reading alone
(culture/rules.py).

    from culture.profiles import get_profile
    p = get_profile("c2c12_ker2018")
    p.cutoff, p.band_pp, p.interval(62.0), p.sha256
"""

from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass, field

import yaml

PROFILES_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "configs",
                             "confluency_profiles.yaml")
UNCALIBRATED = "uncalibrated"


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
                "band_pp": self.band_pp}


_cache: dict[str, dict[str, Profile]] = {}


def load_profiles(path: str = PROFILES_PATH) -> dict[str, Profile]:
    if path not in _cache:
        with open(path) as f:
            doc = yaml.safe_load(f) or {}
        out = {}
        for pid, e in (doc.get("profiles") or {}).items():
            out[pid] = Profile(id=pid, cutoff=float(e["cutoff"]),
                               band_pp=None if e.get("band_pp") is None else float(e["band_pp"]),
                               status=e["status"], description=e.get("description", ""),
                               quality=e.get("quality"), entry=e)
        if UNCALIBRATED not in out:
            raise ValueError(f"{path} has no `{UNCALIBRATED}` profile")
        _cache[path] = out
    return _cache[path]


def get_profile(profile_id: str | None = None, path: str = PROFILES_PATH) -> Profile:
    """The named profile; None or an unknown id gives `uncalibrated`, never a guess."""
    profiles = load_profiles(path)
    return profiles.get(profile_id or UNCALIBRATED, profiles[UNCALIBRATED])


def choices(path: str = PROFILES_PATH) -> list[tuple[str, str]]:
    """(label, id) pairs for a setup picker, uncalibrated last."""
    ps = load_profiles(path)
    order = [p for p in ps if p != UNCALIBRATED] + [UNCALIBRATED]
    return [(ps[p].entry.get("label", p), p) for p in order]
