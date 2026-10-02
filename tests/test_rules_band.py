"""rules_v0.5: passage is read against the confluency profile's 90% error band
(culture/profiles.py, results/confluency_profiles.md), a failed quality gate
gives reimage, and an uncalibrated imaging setup never passages on its own."""

import pytest

from culture.profiles import UNCALIBRATED, get_profile, load_profiles
from culture.rules import ACTIONS, LineConfig, decide

CFG = LineConfig(target_confluency=80.0)
KW = dict(confluency_confidence=0.9, qc_flag=None, qc_confidence=None, line_config=CFG,
          hours_since_passage=48, hours_since_feed=12, anomaly_flag=False)


def act(pct, **kw):
    return decide(confluency_pct=pct, **{**KW, **kw})


def test_band_clear_of_the_target_passages():
    assert act(90.0, band_pp=5.0)[0] == "passage"
    assert act(85.0, band_pp=5.0)[0] == "passage"          # lower end exactly at the target


@pytest.mark.parametrize("pct", [76.0, 79.9, 80.0, 84.9])
def test_band_straddling_the_target_goes_to_a_person(pct):
    action, reason = act(pct, band_pp=5.0)
    assert action == "human_review" and "error band" in reason


def test_band_clear_below_the_target_continues():
    assert act(74.0, band_pp=5.0)[0] == "continue"
    assert act(74.0, band_pp=5.0, hours_since_feed=30)[0] == "feed"


def test_uncalibrated_setup_never_passages_on_its_own():
    action, reason = act(95.0, band_pp=None)
    assert action == "human_review" and "no calibration profile" in reason
    assert act(40.0, band_pp=None)[0] == "continue"


def test_failed_quality_gate_gives_reimage_first():
    action, reason = act(95.0, band_pp=5.0, quality_passed=False, quality_reasons=["blur_below_threshold"])
    assert action == "reimage" and "blur below threshold" in reason
    assert act(95.0, band_pp=5.0, quality_passed=None)[0] == "passage"     # no gate for the setup
    assert "reimage" in ACTIONS


def test_too_soon_after_passage_is_not_held_by_the_band():
    assert act(82.0, band_pp=5.0, hours_since_passage=6)[0] == "continue"


def test_uncalibrated_profile_is_always_there():
    p = get_profile(None)
    assert p.id == UNCALIBRATED and p.band_pp is None and p.interval(50.0) is None
    assert get_profile("no-such-setup").id == UNCALIBRATED
    assert UNCALIBRATED in load_profiles()


def test_profile_hash_pins_the_entry():
    p = get_profile(None)
    assert len(p.sha256) == 64 and p.record_fields()["sha256"] == p.sha256
