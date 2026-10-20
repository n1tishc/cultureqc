"""The console's results cards and the Analyze button's failure path (demo/app.py). No model runs: analyze_image
is replaced, and the stored examples (demo/examples/) supply real anomaly results."""

import dataclasses

import cv2
import numpy as np
import pytest
from conftest import requires

pytestmark = requires("gradio")

QUOTA = "You have exceeded your ZeroGPU runs limit. Sign in to get more quota."


@pytest.fixture
def app():
    from demo import app
    return app


def _image(path, value=90):
    cv2.imwrite(str(path), np.full((64, 64), value, np.uint8))
    return str(path)


def _raising(err):
    def fake(*a, **k):
        raise err
    return fake


@pytest.mark.parametrize("err, head", [
    (RuntimeError(QUOTA), "Live analysis is not available right now"),
    (ValueError("weights are not the approved ones"), "The analysis stopped with an error"),
])
def test_a_failed_run_is_a_card_and_writes_nothing(app, monkeypatch, tmp_path, err, head):
    monkeypatch.setattr(app, "analyze_image", _raising(err))
    before = app.writer.record_count
    out = app.analyze_or_explain(_image(tmp_path / "x.png"), "unknown", 80, "uncalibrated")
    assert len(out) == 7                                       # one value per Analyze output
    card = out[2]
    assert head in card and "no record was written" in card and str(err)[:20] in card
    assert out[3] is None and out[4] is None and out[5] is None  # no overlay, map or reading to review
    assert app.writer.record_count == before


def test_the_quota_message_is_told_apart(app):
    assert app.gpu_refusal(RuntimeError(QUOTA))
    assert app.gpu_refusal(RuntimeError("You have exceeded your GPU quota (60s requested vs. 12s left)."))
    assert not app.gpu_refusal(ValueError("could not broadcast input array"))


def test_the_button_comes_back_after_a_failure(app):
    """Gradio 6 runs only .failure listeners after an error, so the chain must end the loading state from one."""
    deps = app.demo.config["dependencies"]
    run = next(d for d in deps if d.get("api_name") == "run_analysis")
    after = [d for d in deps if d.get("trigger_after") == run["id"]]
    assert any(d.get("trigger_only_on_failure") for d in after)
    assert any(not d.get("trigger_only_on_failure") and not d.get("trigger_only_on_success") for d in after)


KW = dict(anomaly_html="", demoted=True, qc_calibrated=False, qc_flag="normal", qc_confidence=0.5, per_class_probs={},
          evidence_region_count=0, confluency_pct=52.9, confluency_confidence=0.5, confluency_method="probmap",
          target_confluency=80, action="human_review", chain_ok=True, record_count=1)
TEMPLATE = "Confluency 52.9% below target (80%); recommend pause automated decisions and flag for human review."
REASON = ("Confluency 52.9% is within its error band (±29.4 pp) of the target 80%: the reading can't tell which "
          "side of the target the flask is on; recommend a person checks.")


@pytest.mark.parametrize("demoted", [True, False])
def test_the_action_card_gives_the_rules_reason(app, demoted):
    out = app.render_results(**dict(KW, demoted=demoted), rationale=TEMPLATE, reason=REASON,
                             record={"decided_by": "rules_v0.5", "qc_rationale": TEMPLATE})
    card = out.split('class="rc-card action-card"')[1].split("</div>\n  </div>")[0]
    assert "within its error band" in card and "below target" not in card
    assert "a person decides before anything happens" in card and "rules_v0.5" in card
    assert TEMPLATE.replace("(", "").split(";")[0] not in out.split("audit-json")[0]   # only the record keeps it


def test_the_stored_examples_show_their_records_reason(app):
    from demo import precomputed
    ex = next(e for e in precomputed.load() if e["id"] == "evican_ht29")
    out = app.show_example(ex)
    assert "within its error band (±29.4 pp)" in out.split("audit-json")[0]
    assert "Historical policy replay" in out and "Not current authorization" in out
    assert "Not flagged" in out                                # EVICAN is not the anomaly check's setup
    c2c12 = app.show_example(next(e for e in precomputed.load() if e["id"] == "c2c12_normal_40_100"))
    assert "Within the normal range" in c2c12 and "anomaly-scope" not in c2c12


def test_measurement_card_separates_calibration_and_action_approval(app):
    from culture.profiles import get_profile

    profile = get_profile("msc_phase")
    record = {"confluency_profile": profile.record_fields(), "confluency_interval": profile.interval(90),
              "passage_eligibility": profile.passage_eligibility(90, 80)}
    card = app.confluency_card(record, 90, .9, "probmap", 80, 0)
    assert "measurement calibrated" in card
    assert "automatic passage is not supported" in card
    assert "90.0" in card and "7.1 pp" in card


def test_anomaly_card_off_its_reference_line(app):
    from demo import precomputed
    ex = next(e for e in precomputed.load() if e["id"] == "c2c12_normal_40_100")
    img = cv2.imread(precomputed.image_path(ex), cv2.IMREAD_GRAYSCALE)
    a = precomputed.anomaly_result(ex)
    assert not a.flag
    on = app.render_anomaly(img, a, ex["record"]["confluency_profile"]["id"])    # the C2C12 setup
    off = app.render_anomaly(img, a, "uncalibrated")
    assert "Within the normal range" in on and "anomaly-scope" not in on
    assert "Within the normal range" not in off and "Not flagged" in off and "C2C12 only" in off
    flagged = app.render_anomaly(img, dataclasses.replace(a, flag=True), "uncalibrated")
    assert "Flagged for review" in flagged
    assert "known limits" in on and "<details" in on                # the limits fold away


@pytest.mark.parametrize("grey", [120, 191, 230])               # 191: the HUVEC demo image's median
def test_comparison_view_draws_both_models_and_the_experts_outline(app, tmp_path, grey):
    img = np.full((40, 60), grey, np.uint8)
    mask = np.zeros((40, 60), np.uint16)
    mask[5:20, 5:25] = 1
    mask[22:35, 30:55] = 2
    cv2.imwrite(str(tmp_path / "m.tif"), mask)
    shipped = np.zeros((40, 60), bool)
    shipped[5:12, 5:25] = True
    finetuned = mask > 0
    out = app.compare_overlays(img, {"shipped": shipped, "finetuned": finetuned}, {"mask": str(tmp_path / "m.tif")})
    assert set(out) == {"Shipped", "Fine-tuned"}
    for view, fg in (("Shipped", shipped), ("Fine-tuned", finetuned)):
        rgb = cv2.cvtColor(cv2.imread(out[view]), cv2.COLOR_BGR2RGB)
        yellow = (rgb == app.EXPERTS_RGB).all(-1)
        assert yellow.any() and not yellow[0, 0]                 # outline drawn, background left alone
        inside = fg & ~yellow
        green_lead = rgb[inside][:, 1].astype(int) - rgb[inside][:, 0]
        assert (green_lead > 40).all()                           # counted pixels visibly green, even on a bright frame
    switched = app.switch_view("Fine-tuned", "orig.png", dict(out, Overlay="ov.png"), None)
    assert switched[0]["value"] == out["Fine-tuned"]
    assert app.switch_view("Overlay", "orig.png", "ov.png", None)[0]["value"] == "ov.png"


def test_the_outline_follows_cell_borders(tmp_path):
    from demo import lab_demo
    mask = np.zeros((64, 64), np.uint16)
    mask[10:30, 10:30] = 1
    mask[10:30, 30:50] = 2                                     # touching cells keep a border between them
    cv2.imwrite(str(tmp_path / "m.tif"), mask)
    edge = lab_demo.outline(str(tmp_path / "m.tif"), (64, 64))
    assert edge[20, 30] and edge[20, 10] and not edge[20, 20] and not edge[0, 0]
    assert lab_demo.outline(str(tmp_path / "m.tif"), (128, 128)).shape == (128, 128)
