"""
Cell-probability maps behind the Flask Timeline replays, for the timeline's 3D
space x time view (demo/replay_3d.py). No model runs: every map is the compute
cache's stored map (cache/probmaps/<sha>.npz, Cellpose-SAM on Colab GPU, nb/03)
for the frame each visit imaged, copied unchanged.

Per replay in demo/replays/, writes
    demo/replay_maps/<scenario>.npz   prob_x1000, one (260, 348) int16 map per visit
and one index, demo/replay_maps/maps.json, with per visit: the frame's sha,
the map's SHA-256 (culture.cache.probmap_sha256), and the 3 FOV crops the
visit's confluency came from, as boxes in full-frame pixels. The crops come
from the A2 fleet's visit records (cache/replay_fleet/visits_6h_fov3.jsonl,
the same streams scripts/export_demo_replays.py checks against), turned into
positions by culture.cache.fov_crop_specs, the function that made them; each
position is checked against the offsets the cache stored with that crop's
confluency row.

What the layers can and cannot show: a visit's reported confluency is the mean
of Cellpose-SAM run on each crop image separately (culture/cache.py), not read
off the full-frame map, so the boxes show where the crops were, not their
numbers. Each layer is labelled with the cache's full-frame confluency for
the frame (also recorded here, and checked against the map at 1/4 resolution).

    python scripts/export_replay_maps.py
"""

from __future__ import annotations

import json
import os
import re
import sys

import numpy as np
import pandas as pd

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)

from culture.cache import PROBMAP_DOWNSAMPLE, fov_crop_specs, probmap_sha256  # noqa: E402
from demo.replay_timeline import load_replays  # noqa: E402

CACHE = os.path.join(REPO, "cache")
OUT_DIR = os.path.join(REPO, "demo", "replay_maps")
FLEET = os.path.join(CACHE, "replay_fleet", "visits_6h_fov3.jsonl")
FRAME_HW = (1040, 1392)                  # C2C12 frames (cache maps are 260 x 348)
SPEC_RE = re.compile(r"crop_f([0-9.]+)_s(\d+)_k(\d+)$")


def crop_box(image_sha: str, spec: str) -> list[int]:
    """[y0, x0, h, w] in full-frame pixels, as culture.cache.crop_from_spec cuts it."""
    frac, seed, k = SPEC_RE.match(spec).groups()
    frac, k = float(frac), int(k)
    s = next(s for s in fov_crop_specs(image_sha, fracs=(frac,), k=k + 1) if s["crop_spec"] == spec)
    h, w = FRAME_HW
    ch, cw = max(int(h * frac), 1), max(int(w * frac), 1)
    return [int(s["offset_y"] * max(h - ch, 0)), int(s["offset_x"] * max(w - cw, 0)), ch, cw]


def main():
    fleet: dict[str, list[dict]] = {}
    with open(FLEET) as f:
        for line in f:
            v = json.loads(line)
            fleet.setdefault(v["flask_id"], []).append(v)
    conf = pd.read_parquet(os.path.join(CACHE, "confluency.parquet"))
    conf = conf[(conf.model_name == "seg") & (conf.model_version == "cpsam_v2")].set_index(
        ["image_sha256", "crop_spec"])
    os.makedirs(OUT_DIR, exist_ok=True)
    index = {"generated_by": "scripts/export_replay_maps.py",
             "source": "cache/probmaps (Cellpose-SAM cpsam_v2 on Colab GPU, nb/03), copied unchanged",
             "map_format": f"int16 logits x 1000, every {PROBMAP_DOWNSAMPLE}th pixel (culture.cache.downsample_probmap)",
             "frame_hw": list(FRAME_HW), "replays": {}}
    for name, doc in load_replays().items():
        by_time = {v["timestamp"]: v for v in fleet[doc["stream_id"]]}
        maps, layers = [], []
        for v in doc["visits"]:
            fv = by_time[v["timestamp"]]
            sha = v["image_sha256"]
            assert fv["image_sha256"] == [sha] * len(fv["crop_specs"])
            with np.load(os.path.join(CACHE, "probmaps", f"{sha}.npz")) as npz:
                m = npz["prob_x1000"]
            boxes = [crop_box(sha, s) for s in fv["crop_specs"]]
            for spec in fv["crop_specs"]:          # positions as the cache recorded them
                stored = json.loads(conf.loc[(sha, spec), "extra"])
                made = next(x for x in fov_crop_specs(sha, fracs=(stored["frac"],)) if x["crop_spec"] == spec)
                assert (made["offset_y"], made["offset_x"]) == (stored["offset_y"], stored["offset_x"]), spec
            frame_pct = float(conf.loc[(sha, "full"), "pct"])
            maps.append(m)
            layers.append({
                "visit": v["visit"], "hours": v["hours"], "image_sha256": sha, "map_sha256": probmap_sha256(m),
                "fov_boxes": boxes,
                "fov_pct_recorded": v["fov_confluency"], "fov_mean_recorded": v["confluency_mean"],
                "quality_pass": v["quality_pass"], "quality_reasons": v["quality_reasons"],
                "frame_pct_recorded": round(frame_pct, 2),
                "frame_pct_from_map": round(float((m > 0).mean() * 100), 2),
            })
        np.savez_compressed(os.path.join(OUT_DIR, f"{name}.npz"), prob_x1000=np.stack(maps))
        worst = max(abs(L["frame_pct_recorded"] - L["frame_pct_from_map"]) for L in layers)
        index["replays"][name] = {"file": f"{name}.npz", "stream_id": doc["stream_id"], "layers": layers}
        print(f"{name}: {len(layers)} visits, crop positions match the cache; full-frame confluency from the "
              f"1/4-resolution map vs recorded: max |diff| {worst:.2f} pp")
    with open(os.path.join(OUT_DIR, "maps.json"), "w") as f:
        json.dump(index, f, indent=1, sort_keys=True)
        f.write("\n")


if __name__ == "__main__":
    main()
