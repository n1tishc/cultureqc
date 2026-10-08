"""The fine-tuned model's demo set in the console (demo/lab_demo.py): off unless CULTUREQC_FINETUNED is set, and
when on, the fine-tuned model reads only the listed images, matched by the exact file; its weights are downloaded
to the configured path, never checked or trusted here. No model is loaded and nothing is downloaded."""

import json
import os

import numpy as np
import pytest
from conftest import requires

from demo import lab_demo

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class Stop(Exception):
    pass


def _capture(monkeypatch, app):
    seen = []

    def fake(img, path, line, target, profile_id=None, finetuned_id=None):
        seen.append(finetuned_id)
        raise Stop

    monkeypatch.setattr(app, "analyze_image", fake)
    return seen


def _image(path, value):
    import cv2
    cv2.imwrite(str(path), np.full((32, 32), value, np.uint8))
    return str(path)


def test_the_demo_set_is_the_agreed_test_images():
    names = [n for n, *_ in lab_demo.IMAGES]
    assert len(names) == 4 and len(set(n for _, n, *_ in lab_demo.IMAGES)) == 4
    split = {r["name"]: r["split"] for r in json.load(open(os.path.join(REPO, "results", "confluency_mcellseg_split.json")))["images"]}
    assert all(split[n] == "test" for n in names)                    # never trained on by the fine-tuned model
    product = {json.loads(x)["flask_id"] for x in open(os.path.join(REPO, "results", "finetuned_product_readings.jsonl")) if x.strip()}
    assert set(names) <= product
    assert not {"HUVEC_CellsOnly_CD7_12_84-0005.tif", "P2_siRNA_1_40xoir-C_3.tif"} & set(names)


def test_off_without_the_variable(monkeypatch, tmp_path):
    monkeypatch.delenv(lab_demo.MODEL_ENV, raising=False)
    assert lab_demo.available() == []
    p = _image(tmp_path / "x.png", 1)
    assert lab_demo.match(p, [{"sha256": lab_demo.hash_file(p)}]) is None


@pytest.fixture
def lab(monkeypatch, tmp_path):
    data = tmp_path / "labeled"
    (data / "images").mkdir(parents=True)
    (data / "masks").mkdir()
    img = _image(data / "images" / "demo.tif", 100)
    mask = np.zeros((32, 32), np.uint8)
    mask[:8] = 1                                              # 25% outlined
    import cv2
    cv2.imwrite(str(data / "masks" / "demo_mask.tif"), mask)
    monkeypatch.setattr(lab_demo, "IMAGES", [("demo.tif", lab_demo.hash_file(img), "HEK293T", "HEK · demo")])
    monkeypatch.setenv(lab_demo.MODEL_ENV, "mcellseg_ftF_r2")
    images = lab_demo.available(str(data))
    assert len(images) == 1 and images[0]["experts_pct"] == pytest.approx(25.0)
    return images, img, tmp_path


@requires("gradio")
def test_console_without_the_variable_never_reads_the_finetuned_model(monkeypatch, tmp_path):
    monkeypatch.delenv(lab_demo.MODEL_ENV, raising=False)
    import importlib
    from demo import app
    app = importlib.reload(app)                               # built as demo/app.py builds it on its own
    assert app.LAB_IMAGES == [] and "HEK293T" not in app.CELL_LINES
    seen = _capture(monkeypatch, app)
    with pytest.raises(Stop):
        app.run_analysis(_image(tmp_path / "up.png", 7), "A172", 80, "uncalibrated")
    assert seen == [None]


@requires("gradio")
def test_finetuned_reads_only_the_exact_demo_files(monkeypatch, lab):
    images, img, tmp = lab
    from demo import app
    monkeypatch.setattr(app, "LAB_IMAGES", images)
    seen = _capture(monkeypatch, app)
    other = _image(tmp / "upload.png", 101)                   # any upload
    changed = tmp / "changed.tif"
    b = bytearray(open(img, "rb").read())
    b[-1] ^= 1
    changed.write_bytes(bytes(b))                             # the demo file with one byte changed
    for p in (img, other, str(changed)):
        with pytest.raises(Stop):
            app.run_analysis(p, "HEK293T", 80, "uncalibrated")
    assert seen == ["mcellseg_ftF_r2", None, None]
    out = app.on_lab_image("demo.tif")
    assert out[2] == img and out[5] == app.DEFAULT_PROFILE and out[6] == "HEK293T"


@requires("gradio")
def test_cards_show_the_check_and_never_an_action(lab):
    images, img, tmp = lab
    from demo import app
    fr = {"id": "mcellseg_ftF_r2", "status": "not_validated", "cutoff": 0.0, "confluency_pct": 78.7,
          "check": {"status": "match", "sha256": "2d1549682c1d" + "0" * 52, "approvals_head": "e326493673ef" + "0" * 52},
          "used_in_decision": False}
    kw = dict(anomaly_html="", demoted=True, qc_calibrated=False, qc_flag="normal", qc_confidence=0.5,
              per_class_probs={}, evidence_region_count=0, confluency_pct=43.4, confluency_confidence=0.5,
              confluency_method="probmap", target_confluency=80, action="continue", rationale="r", record={},
              chain_ok=True, record_count=1)
    plain = app.render_results(**kw)
    assert "ft-card" not in plain and "lab-card" not in plain
    shown = app.render_results(**kw, finetuned=fr, lab=images[0])
    assert "78.7" in shown and "decides nothing" in shown and "match" in shown and "2d1549682c1d" in shown
    assert "25.0%" in shown and "experts" in shown
    refused = app.render_results(**kw, finetuned=dict(fr, confluency_pct=None, reason="weights are not the approved ones",
                                                      check=dict(fr["check"], status="mismatch")), lab=images[0])
    assert "No reading" in refused and "mismatch" in refused


def test_the_listed_files_are_the_dataset_bytes():
    """Where mCellSeg is on disk (it is gitignored), every listed hash is the file's."""
    present = [(n, s) for n, s, *_ in lab_demo.IMAGES if os.path.exists(os.path.join(lab_demo.DATA, "images", n))]
    if not present:
        pytest.skip("mCellSeg not on disk")
    for n, s in present:
        assert lab_demo.hash_file(os.path.join(lab_demo.DATA, "images", n)) == s, n


def test_files_are_the_images_and_their_masks():
    f = lab_demo.files()
    assert len(f) == 2 * len(lab_demo.IMAGES) and all(p.startswith("data/sources/mcellseg/") for p in f)
    assert sum(p.endswith("_mask.tif") for p in f) == len(lab_demo.IMAGES)


def _weights_config(monkeypatch, tmp_path):
    import culture.finetuned as ft
    target = tmp_path / "w" / "mcellseg_ftF_r2"
    monkeypatch.setattr(ft, "load_config", lambda *a, **k: {"mcellseg_ftF_r2": {"path": str(target)}})
    monkeypatch.setattr(ft, "weights_file", lambda entry: entry["path"])
    return target


def _hub(monkeypatch, download):
    """A stand-in huggingface_hub (CI does not install it); fetch_weights imports it at call time."""
    import sys
    import types
    hub = types.ModuleType("huggingface_hub")
    hub.hf_hub_download = download
    monkeypatch.setitem(sys.modules, "huggingface_hub", hub)


def test_fetch_weights_downloads_to_the_configured_path(monkeypatch, tmp_path):
    target = _weights_config(monkeypatch, tmp_path)
    seen = []

    def fake(repo_id, filename, local_dir=None, token=None):
        seen.append((repo_id, filename, local_dir, token))
        os.makedirs(local_dir, exist_ok=True)
        open(os.path.join(local_dir, filename), "wb").write(b"w")
        return os.path.join(local_dir, filename)

    _hub(monkeypatch, fake)
    path, how = lab_demo.fetch_weights("mcellseg_ftF_r2", "owner/private", token="t")
    assert path == str(target) and target.exists() and "owner/private" in how
    assert seen == [("owner/private", "mcellseg_ftF_r2", str(target.parent), "t")]
    assert lab_demo.fetch_weights("mcellseg_ftF_r2", "owner/private") == (str(target), "already on disk")
    assert len(seen) == 1                                     # no second download


def test_fetch_weights_failure_turns_nothing_on(monkeypatch, tmp_path):
    _weights_config(monkeypatch, tmp_path)

    def fail(*a, **k):
        raise OSError("401 Client Error\nsecret details")

    _hub(monkeypatch, fail)
    path, why = lab_demo.fetch_weights("mcellseg_ftF_r2", "owner/private", token="hf_secret")
    assert path is None and "owner/private" in why and "401" in why
    assert "secret details" not in why and "hf_secret" not in why
    assert lab_demo.fetch_weights("other", "owner/private")[0] is None
