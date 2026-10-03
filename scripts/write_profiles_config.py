"""
Write configs/confluency_profiles.yaml from results/confluency_profiles.json,
so no profile value is typed in by hand.

Status, decided mechanically from the pre-registered criteria
(results/confluency_profiles.md):
  validated        every measurable criterion A1-A5 passed, on held-out images
  failed           a measurable criterion failed
  in_domain_check  LIVECell: no held-out evidence, whatever the criteria say
Only a validated profile is live: its fitted cutoff and band are the ones
used. Any other keeps them as fitted_cutoff / fitted_band_pp and reads like an
uncalibrated setup (cutoff 0.0, no band). A setup with no scored profile
(UNSCORED) is written as uncalibrated, with its quality gate.

    .venv/bin/python scripts/write_profiles_config.py
"""

from __future__ import annotations

import hashlib
import json
import os

import yaml

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(REPO, "results", "confluency_profiles.json")
DST = os.path.join(REPO, "configs", "confluency_profiles.yaml")

LABELS = {
    "c2c12_ker2018": "C2C12 time-lapse microscope (Ker et al. 2018), 5× phase contrast",
    "evican_mixed": "EVICAN: mixed brightfield and phase-contrast microscopes",
    "msc_phase": "MSC phase contrast (Solopov et al. 2025)",
    "livecell_incucyte": "LIVECell instrument, 10× phase contrast",
}
# Imaging setups with no scored profile. They read like an uncalibrated setup (Cellpose's default cutoff, no
# band), but are named, so a reading says which setup took it, and they run the quality gate calibrated for
# the setup, which needs no labelled images (configs/quality.yaml).
UNSCORED = {
    "c2c12_ker2018": {
        "quality": "c2c12",
        "description": ("No labelled images from this setup, so no confluency calibration: the reading uses "
                        "Cellpose's default cutoff and has no error band, and a reading at or above the passage "
                        "target goes to a person. Its quality gate is calibrated on the tuning frames "
                        "(results/quality_gate_c2c12.md)."),
    },
}
HEADER = """# Confluency calibration profiles (culture/profiles.py).
#
# WRITTEN BY scripts/write_profiles_config.py from results/confluency_profiles.json;
# do not edit by hand (tests/test_profiles_config.py checks they match).
#
# One entry per imaging setup: the Cellpose-SAM logit cutoff and the 90% error
# band measured on held-out labelled images from that setup, by
# scripts/confluency_profiles.py (results/confluency_profiles.md, where the
# method and the acceptance criteria were committed before scoring). Every
# record carries the profile's id and SHA-256; replacing an entry is a change
# under change control, written as a `change` event in the record chain.
#
# status: validated (every measurable criterion passed on held-out images; the
#         only status whose fitted values are used), failed, in_domain_check,
#         uncalibrated. A profile that is not validated reads like an
#         uncalibrated setup: cutoff 0.0, band null.

"""


def status_of(res: dict) -> str:
    if res["status"].startswith("in-domain"):
        return "in_domain_check"
    verdicts = [v[0] for v in res["acceptance"].values()]
    return "failed" if "fail" in verdicts else "validated"


def build() -> dict:
    doc = json.load(open(SRC))
    src_hash = hashlib.sha256(open(SRC, "rb").read()).hexdigest()
    profiles = {"uncalibrated": {
        "label": "Other imaging setup (uncalibrated)",
        "description": ("No validated calibration profile for this imaging setup. The reading uses Cellpose's "
                        "default cutoff and has no error band, so a reading at or above the passage target goes to "
                        "a person."),
        "cutoff": 0.0, "band_pp": None, "status": "uncalibrated", "quality": None}}
    for pid, p in doc["profiles"].items():
        res = doc["results"][pid]
        st = status_of(res)
        live = st == "validated"
        profiles[pid] = {
            "label": LABELS.get(pid, pid),
            "description": (f"Fitted on {p['n_calib']} labelled images from this setup; tested on {res['n_test']} others."
                            if len(res.get("folds", [])) <= 1 else
                            f"{res['n_test']} labelled images from this setup in {len(res['folds'])} populations; each "
                            f"population tested with the cutoff and band fitted on the others."),
            "cutoff": p["cutoff"] if live else 0.0,
            "band_pp": round(p["band_pp"], 2) if (live and p["band_pp"] is not None) else None,
            "status": st,
            "fitted_cutoff": p["cutoff"],
            "fitted_band_pp": None if p["band_pp"] is None else round(p["band_pp"], 2),
            "acceptance": {k: v[0] for k, v in res["acceptance"].items()},
            "quality": "c2c12" if pid == "c2c12_ker2018" else None,
            "evidence": {"path": "results/confluency_profiles.json", "sha256": src_hash},
        }
    for pid, u in UNSCORED.items():
        if pid not in profiles:
            profiles[pid] = {"label": LABELS.get(pid, pid), "description": u["description"], "cutoff": 0.0,
                             "band_pp": None, "status": "uncalibrated", "quality": u["quality"]}
    return {"version": 1, "profiles": profiles}


def main():
    with open(DST, "w") as f:
        f.write(HEADER)
        yaml.safe_dump(build(), f, sort_keys=False, allow_unicode=True, width=110)
    print("wrote", os.path.relpath(DST, REPO))


if __name__ == "__main__":
    main()
