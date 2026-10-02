"""configs/confluency_profiles.yaml is generated from results/confluency_profiles.json
(scripts/write_profiles_config.py): no profile value is typed in by hand, and only a
validated profile's fitted values are live."""

import os
import sys

import pytest
import yaml

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "scripts"))


@pytest.mark.skipif(not os.path.exists(os.path.join(REPO, "results", "confluency_profiles.json")),
                    reason="profiles not scored yet")
def test_config_matches_the_results():
    import write_profiles_config as w
    on_disk = yaml.safe_load(open(w.DST))
    assert on_disk == w.build(), "configs/confluency_profiles.yaml is stale: run scripts/write_profiles_config.py"


def test_only_validated_profiles_are_live():
    doc = yaml.safe_load(open(os.path.join(REPO, "configs", "confluency_profiles.yaml")))
    for pid, p in doc["profiles"].items():
        if p["status"] != "validated":
            assert p["cutoff"] == 0.0 and p["band_pp"] is None, pid
