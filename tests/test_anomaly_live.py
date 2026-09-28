"""B2 (cultureQC_upgrade_specv4.md §2B.4): the live per-image anomaly score.

1. The live scoring code, fed the cached qctile embeddings of held-out frames,
   reproduces scripts/eval_anomaly.py's scores exactly (needs the cache).
2. Live DINOv2 on the real frames (data/c2c12_picks/, fetched by
   nb/04c_fetch_c2c12_frames.ipynb) matches the cached embeddings' scores
   (needs the frames; the cache was embedded on a GPU, so small differences).
3. The app caption's numbers are still in results/anomaly_summary.md.
"""

import os

import numpy as np
import pandas as pd
import pytest

from culture import anomaly

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE = os.path.join(REPO, "cache")
PICKS = os.path.join(REPO, "results", "c2c12_frame_picks.csv")
FRAMES = os.path.join(REPO, "data", "c2c12_picks")
HAS_CACHE = os.path.exists(os.path.join(CACHE, "anomaly", "banks.npz"))


def test_caption_numbers_come_from_the_report():
    with open(os.path.join(REPO, "results", "anomaly_summary.md")) as f:
        report = f.read()
    for fact in ["binned 10.0%", "target 5%", "F0016 69%", "+59.4 pp", "88% of these frames", "| 0.47 |"]:
        assert fact in report, fact
    text = " ".join(anomaly.LIVE_LIMITS)
    for n in ["10.0%", "5% target", "69%", "+59.4 pp", "88%", "0.47", "16.5×", "holds a passage for human review", "uncalibrated"]:
        assert n in text, n


def test_tile_box():
    assert anomaly.tile_box(1040, 1392) == (1392 // 2 - 128, 1040 // 2 - 128, 1.0, 1.0)
    assert anomaly.tile_box(200, 512) == (0, 0, 2.0, 200 / 256)


def test_unverified_banks_are_not_used(tmp_path):
    cfg = anomaly.load_anomaly_config()
    bad = tmp_path / "banks.npz"
    np.savez(bad, **{"bin_0-20": np.ones((4, 384), np.float32)})
    r = anomaly.score_frame(np.zeros((300, 300), np.uint8), 10.0, cfg, banks_path=str(bad))
    assert r.status == "unavailable" and "do not match" in r.reason and r.flag is None
    r = anomaly.score_frame(np.zeros((300, 300), np.uint8), 10.0, cfg, banks_path=str(tmp_path / "none.npz"))
    assert r.status == "unavailable" and r.record_fields()["anomaly_used_in_decision"] is False


def test_patch_count_is_checked():
    with pytest.raises(ValueError):
        anomaly.score_patches(np.zeros((10, 384)), 10.0, {}, {})


@pytest.mark.skipif(not HAS_CACHE, reason="needs the local compute cache")
def test_live_scoring_reproduces_cached_scores():
    cfg = anomaly.load_anomaly_config()
    banks, reason = anomaly.load_banks(cfg)
    assert banks is not None, reason
    sc = pd.read_parquet(os.path.join(CACHE, "anomaly", "scores.parquet"))
    held = sc[sc.split == "heldout"].drop_duplicates("image_sha256")
    sample = pd.concat([g.sample(min(len(g), 8), random_state=0) for _, g in held.groupby(["kind", "bin_label"])])
    for r in sample.itertuples():
        patches = np.load(os.path.join(CACHE, "embeddings", f"{r.image_sha256}_qctile.npy"))
        res = anomaly.score_patches(patches, r.pct, cfg, banks)
        assert res.bin_label == r.bin_label
        # eval_anomaly.py batched many frames per matmul: float32 order differs, ~1e-5
        assert res.score == pytest.approx(r.score_binned, abs=1e-4)
        assert res.flag == bool(r.flag_binned) or abs(r.score_binned - res.threshold) < 1e-4
        assert np.max(res.patch_distances) == pytest.approx(max(d for row in res.patch_distances for d in row))


@pytest.mark.skipif(not (HAS_CACHE and os.path.isdir(FRAMES)),
                    reason="needs data/c2c12_picks/ (nb/04c_fetch_c2c12_frames.ipynb)")
def test_live_embedding_parity_on_real_frames():
    import cv2

    from culture.cache import image_sha256

    cfg = anomaly.load_anomaly_config()
    picks = pd.read_csv(PICKS)
    rows = []
    for r in picks.itertuples():
        path = os.path.join(FRAMES, f"{r.image_sha256}.png")
        assert image_sha256(path) == r.image_sha256
        res = anomaly.score_frame(cv2.imread(path, cv2.IMREAD_GRAYSCALE), r.pct, cfg)
        rows.append((r.image_sha256[:12], r.kind, res.score, r.score_binned, res.threshold, res.flag, r.flag_binned))
    df = pd.DataFrame(rows, columns=["sha", "kind", "live", "cached", "thr", "flag_live", "flag_cached"])
    df["diff"] = (df.live - df.cached).abs()
    print("\n" + df.to_string(index=False))
    assert df["diff"].max() < 0.01, df
    tol = df["diff"].max()
    far = (df.cached - df.thr).abs() > tol          # a flag can only flip within the measured difference
    assert (df.flag_live[far] == df.flag_cached[far]).all(), df


def test_site_calibration_never_scores_against_its_own_bank(tmp_path, monkeypatch):
    """scripts/site_calibrate.py on stub embeddings: bank and calibration images
    are disjoint, thresholds are set, and the output loads in the live path."""
    import importlib.util

    spec = importlib.util.spec_from_file_location("site_calibrate", os.path.join(REPO, "scripts", "site_calibrate.py"))
    sc = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(sc)
    rng = np.random.default_rng(1)
    patches = [rng.standard_normal((anomaly.GRID ** 2, 16)).astype(np.float32) for _ in range(12)]
    patches = [p / np.linalg.norm(p, axis=1, keepdims=True) for p in patches]
    base = anomaly.load_anomaly_config()
    banks, cfg, warnings = sc.calibrate(patches, [5.0] * 6 + [30.0] * 6, base, fpr=0.05, seed=0, single_bin=False)
    assert set(cfg["calibration"]["bins"]) <= {"0-20", "20-40", "40-60", "60-80", "80-100", "0-40", "20-100",
                                               "0-100", "40-100"}
    for label, c in cfg["calibration"]["bins"].items():
        assert c["n_bank_images"] >= 1 and c["n_calibration_images"] >= 1
        assert c["threshold"] > 0                     # a self-scored bank would give ~0
    assert warnings                                   # tiny calibration sets are called out
    np.savez(tmp_path / "banks.npz", **banks)
    loaded, reason = anomaly.load_banks(cfg, str(tmp_path / "banks.npz"))
    assert loaded is not None, reason
    one, cfg1, _ = sc.calibrate(patches, [0.0] * 12, base, fpr=0.05, seed=0, single_bin=True)
    assert list(cfg1["calibration"]["bins"]) == ["0-100"]
