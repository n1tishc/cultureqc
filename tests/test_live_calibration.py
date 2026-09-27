"""B3 (cultureQC_upgrade_specv4.md §2B.2): the A5 temperature in the live
classifier path, and the demoted classifier kept out of decisions. Stub
model, no download."""

import numpy as np
import pytest
import torch

from culture import qc
from culture.calibration import load_calibration, softmax
from culture.pipeline import config_hashes
from culture.rationale import generate_rationale
from culture.rules import decide

LOGITS = [2.0, 3.5, -1.0, 0.5]          # arg-max = contamination_suspected


class _Stub(torch.nn.Module):
    def __init__(self):
        super().__init__()
        self.w = torch.nn.Parameter(torch.zeros(1))

    def forward(self, x):
        return torch.tensor([LOGITS], dtype=torch.float32) + 0 * self.w


@pytest.fixture
def stub_model(monkeypatch):
    monkeypatch.setattr(qc, "_get_model", lambda: _Stub())


def test_live_probs_are_temperature_scaled(stub_model):
    cal = load_calibration()
    assert cal["model_version"] == qc.MODEL_VERSION
    r = qc.qc_classify(np.zeros((256, 256), np.uint8), run_gradcam=False)
    expected = softmax(np.array(LOGITS), cal["temperature"])
    assert r.calibrated is True
    assert r.flag == "contamination_suspected"
    assert r.confidence == pytest.approx(expected.max(), abs=1e-4)
    assert [r.per_class_probs[c] for c in qc.CLASS_NAMES] == pytest.approx(expected, abs=1e-4)
    assert r.confidence < softmax(np.array(LOGITS)).max()      # T > 1 softens


def test_other_model_version_is_not_calibrated(stub_model, monkeypatch):
    monkeypatch.setattr(qc, "_get_calibration", lambda: {"model_version": "other", "temperature": 2.0})
    r = qc.qc_classify(np.zeros((256, 256), np.uint8), run_gradcam=False)
    assert r.calibrated is False
    assert r.confidence == pytest.approx(softmax(np.array(LOGITS)).max(), abs=1e-4)


def test_demotion_switch_fails_safe(tmp_path):
    assert qc.classifier_demoted() is True                     # repo config: owner decision 2026-09-27
    assert "known not to transfer" in qc.demoted_label()
    assert qc.classifier_demoted(str(tmp_path / "missing.yaml")) is True
    (tmp_path / "no_key.yaml").write_text("rescale: {enabled: false}\n")
    assert qc.classifier_demoted(str(tmp_path / "no_key.yaml")) is True
    (tmp_path / "on.yaml").write_text("classifier: {demoted: false}\n")
    assert qc.classifier_demoted(str(tmp_path / "on.yaml")) is False


def test_decide_without_classifier_skips_the_qc_rule():
    kw = dict(confluency_pct=50.0, confluency_confidence=0.9, hours_since_passage=48, hours_since_feed=30)
    assert decide(qc_flag="contamination_suspected", qc_confidence=0.95, **kw)[0] == "human_review"
    action, reason = decide(qc_flag=None, qc_confidence=None, **kw)
    assert action == "feed" and "QC flag" not in reason
    assert decide(qc_flag="normal", qc_confidence=0.95, **kw)[0] == "feed"


def test_demoted_rationale_states_no_classifier_finding():
    r = generate_rationale(qc_flag=None, qc_confidence=None, evidence_bbox=None, confluency_pct=42.3,
                           target_confluency=80, action="feed", use_vlm=True, image_path="x.png")
    assert r["rationale"] == "Confluency 42.3% below target (80%); recommend perform media exchange."
    assert r["method"] == "template"


def test_records_hash_the_configs_they_used():
    h = config_hashes()
    assert set(h) == {"qc.yaml", "calibration.yaml", "detectability.yaml"}
    assert all(len(v) == 64 for v in h.values())
