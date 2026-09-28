"""Rules v0.3: the per-image anomaly flag holds a passage for human review, and
changes nothing else (hold, feed, the confidence floor); None (check
unavailable) behaves like v0.2."""

from culture.rationale import generate_rationale
from culture.rules import RULES_VERSION, LineConfig, decide

CFG = LineConfig(target_confluency=80.0)
KW = dict(confluency_confidence=0.9, qc_flag=None, qc_confidence=None, line_config=CFG,
          hours_since_passage=48, hours_since_feed=12)


def test_flag_holds_a_passage():
    assert decide(confluency_pct=86.6, anomaly_flag=False, **KW)[0] == "passage"
    assert decide(confluency_pct=86.6, anomaly_flag=None, **KW)[0] == "passage"
    action, reason = decide(confluency_pct=86.6, anomaly_flag=True, **KW)
    assert action == "human_review" and "anomaly check flagged" in reason


def test_flag_changes_nothing_below_target():
    assert decide(confluency_pct=40.0, anomaly_flag=True, **KW)[0] == "hold"
    fed = dict(KW, hours_since_feed=30)
    assert decide(confluency_pct=40.0, anomaly_flag=True, **fed)[0] == "feed"


def test_flag_does_not_hold_a_passage_too_soon_anyway():
    soon = dict(KW, hours_since_passage=6)
    assert decide(confluency_pct=86.6, anomaly_flag=True, **soon)[0] == "hold"


def test_low_confidence_still_comes_first():
    low = dict(KW, confluency_confidence=0.1)
    _, reason = decide(confluency_pct=86.6, anomaly_flag=True, **low)
    assert "below floor" in reason


def test_rationale_says_why_the_passage_is_held():
    r = generate_rationale(qc_flag=None, qc_confidence=None, evidence_bbox=None, confluency_pct=86.6,
                           target_confluency=80, action="human_review", anomaly_flag=True)["rationale"]
    assert r.endswith("The anomaly check flagged this image, so it is not passaged automatically.")
    r = generate_rationale(qc_flag=None, qc_confidence=None, evidence_bbox=None, confluency_pct=5.1,
                           target_confluency=80, action="hold", anomaly_flag=True)["rationale"]
    assert r.endswith("The anomaly check flagged this image for review.")


def test_version():
    assert RULES_VERSION == "rules_v0.3"
