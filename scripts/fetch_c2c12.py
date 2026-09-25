#!/usr/bin/env python3
"""
scripts/fetch_c2c12.py — C2C12 phase-contrast time-lapse sequences for Phase A
(cultureQC_upgrade.md §2A.2–2A.3), converted into cache-ready 8-bit PNGs.

Source: Ker et al., "Phase contrast time-lapse microscopy datasets with automated
and manual cell tracking annotations", Scientific Data 5:180237 (2018),
doi:10.1038/sdata.2018.237. Data: OSF project ysaq2 (doi:10.17605/OSF.IO/YSAQ2),
CC BY 4.0 — attribution required wherever these images or derived numbers appear.

Facts from the paper (used below, not guessed):
  - 48 sequences = 3 independent experiments x 16 fields of view
    (4 dishes x 4 conditions: control, FGF2, BMP2, FGF2+BMP2).
  - one frame every 5 minutes, ~1013-1062 frames (~3.5 days) per sequence.
  - TIFF, 1392 x 1040, 16-bit container holding 12-bit data (max 4095).
  - experiment folders are named like "090303-C2C12P15-FGF2,BMP2" (yymmdd first).
    NOTE: the experiment folder name lists BOTH growth factors, so condition must
    NOT be parsed from the full path — only from the sequence's own folder name.

What is NOT known from here (discovered at runtime, printed for the human to check):
  - how OSF packages the files (loose TIFFs per sequence folder vs. archives)
  - the per-sequence folder names and frame filename pattern
  - the folder-name -> condition mapping (paper Table 1)

Why convert to 8-bit PNG here, with ONE fixed normalization for the whole dataset:
  culture.cache.Cache.build() reads images with cv2.IMREAD_GRAYSCALE, which turns a
  16-bit TIFF into 8-bit by dropping the low byte — 12-bit data (max 4095) would
  come out nearly black. A per-frame auto-contrast would fix that but would also
  erase real brightness changes over time — exactly the lamp-dimming signal Phase A
  (V7) must be able to see. So: one global linear map (percentiles over a sample of
  frames), saved to JSON and reused on every rerun so PNG bytes (= cache keys) stay
  identical across runs.

Subcommands
  discover   walk OSF (all storage providers + child components), write inventory.json
  fetch      select sequences, download every Nth frame, write raw TIFFs + 8-bit PNGs,
             c2c12_sequences.csv, c2c12_frames.csv, c2c12_normalization.json
             (--local-src DIR instead of --inventory to use files you downloaded yourself)

Everything is resumable: files already on disk are skipped.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import sys
import time
from datetime import datetime, timedelta, timezone

import numpy as np

OSF_API = "https://api.osf.io/v2"
OSF_NODE = "ysaq2"
FRAME_INTERVAL_MIN = 5
TIFF_EXT = (".tif", ".tiff")
ARCHIVE_EXT = (".zip", ".tar", ".tar.gz", ".tgz", ".7z")
CONDITIONS = ("FGF2+BMP2", "FGF2", "BMP2", "control")


# ---------------------------------------------------------------------------
# HTTP helpers (OSF)
# ---------------------------------------------------------------------------

def _get_json(url: str, retries: int = 5) -> dict:
    import requests

    for attempt in range(retries):
        try:
            r = requests.get(url, timeout=60)
            if r.status_code == 429:
                time.sleep(10 * (attempt + 1))
                continue
            r.raise_for_status()
            return r.json()
        except Exception as e:  # noqa: BLE001 — network flakiness on Colab is normal
            if attempt == retries - 1:
                raise
            print(f"  retry {attempt + 1} after error: {e}")
            time.sleep(3 * (attempt + 1))
    raise RuntimeError("unreachable")


def _download(url: str, dest: str, retries: int = 5) -> None:
    import requests

    if os.path.exists(dest) and os.path.getsize(dest) > 0:
        return
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    tmp = dest + ".part"
    for attempt in range(retries):
        try:
            with requests.get(url, stream=True, timeout=120) as r:
                r.raise_for_status()
                with open(tmp, "wb") as f:
                    for chunk in r.iter_content(1 << 20):
                        f.write(chunk)
            os.replace(tmp, dest)
            return
        except Exception as e:  # noqa: BLE001
            if attempt == retries - 1:
                raise
            print(f"  retry {attempt + 1} for {os.path.basename(dest)}: {e}")
            time.sleep(3 * (attempt + 1))


def _pages(url: str):
    """Yield items across OSF's paginated listings."""
    sep = "&" if "?" in url else "?"
    url = f"{url}{sep}page[size]=100"
    while url:
        d = _get_json(url)
        for item in d.get("data", []):
            yield item
        url = (d.get("links") or {}).get("next")


# ---------------------------------------------------------------------------
# discover
# ---------------------------------------------------------------------------

def _file_entry(item: dict, node: str) -> dict:
    a = item["attributes"]
    return {
        "node": node,
        "kind": a["kind"],
        "name": a["name"],
        "path": a.get("materialized_path") or a.get("path") or a["name"],
        "size": a.get("size"),
        "download": (item.get("links") or {}).get("download"),
        "listing": ((item.get("relationships") or {}).get("files") or {}).get("links", {}).get("related", {}).get("href"),
    }


def _walk_folder(listing_url: str, node: str, out: dict, probe_files: int, depth: int = 0) -> None:
    """Walk one folder. Leaf folders full of TIFFs are only *probed* (first page)
    and recorded as sequence candidates — listing all ~50k frames up front would
    take hundreds of API calls; `fetch` lists only the sequences it selects."""
    n_tiff_seen, subfolders = 0, []
    sample_names = []
    for item in _pages(listing_url):
        e = _file_entry(item, node)
        if e["kind"] == "folder":
            subfolders.append(e)
            out["folders"].append(e)
        elif e["name"].lower().endswith(TIFF_EXT):
            n_tiff_seen += 1
            if len(sample_names) < 5:
                sample_names.append(e["name"])
            if n_tiff_seen >= probe_files and not subfolders:
                break  # it's a frame folder; stop paging
        else:
            out["files"].append(e)
    if n_tiff_seen:
        out["tiff_folders"].append({
            "node": node, "listing": listing_url, "path": out["_current_path"],
            "tiffs_seen_in_probe": n_tiff_seen, "complete_listing": False,
            "sample_names": sample_names,
        })
    for sf in subfolders:
        prev = out["_current_path"]
        out["_current_path"] = sf["path"]
        print(f"{'  ' * (depth + 1)}{sf['path']}")
        _walk_folder(sf["listing"], node, out, probe_files, depth + 1)
        out["_current_path"] = prev


def discover(inventory_path: str, node: str = OSF_NODE, probe_files: int = 20) -> dict:
    out = {"source": f"osf:{node}", "folders": [], "files": [], "tiff_folders": [], "_current_path": "/"}
    nodes = [node]
    try:
        for child in _pages(f"{OSF_API}/nodes/{node}/children/"):
            nodes.append(child["id"])
    except Exception as e:  # noqa: BLE001
        print("could not list child components (continuing with root only):", e)
    for n in nodes:
        for prov in _pages(f"{OSF_API}/nodes/{n}/files/"):
            name = prov["attributes"]["name"]
            href = prov["relationships"]["files"]["links"]["related"]["href"]
            print(f"[{n}] provider {name}")
            out["_current_path"] = f"/{name}"
            _walk_folder(href, n, out, probe_files)
    out.pop("_current_path")
    archives = [f for f in out["files"] if f["name"].lower().endswith(ARCHIVE_EXT)]
    out["archives"] = archives
    out["mode"] = "tiff_folders" if out["tiff_folders"] else ("archives" if archives else "unknown")
    os.makedirs(os.path.dirname(os.path.abspath(inventory_path)), exist_ok=True)
    with open(inventory_path, "w") as f:
        json.dump(out, f, indent=2)
    return out


def summarize_inventory(inv: dict) -> None:
    print(f"mode: {inv['mode']}")
    print(f"folders: {len(inv['folders'])}   loose non-TIFF files: {len(inv['files'])}   "
          f"TIFF sequence folders: {len(inv['tiff_folders'])}   archives: {len(inv.get('archives', []))}")
    for tf in inv["tiff_folders"][:60]:
        print(f"  [tiff] {tf['path']}   e.g. {tf['sample_names'][:2]}")
    for a in inv.get("archives", [])[:60]:
        size = f"{a['size'] / 1e9:.2f} GB" if a.get("size") else "? GB"
        print(f"  [archive] {a['path']}  {size}")


# ---------------------------------------------------------------------------
# sequence metadata
# ---------------------------------------------------------------------------

def parse_experiment(path: str) -> str:
    """yymmdd from the experiment folder (e.g. 090303-C2C12P15-FGF2,BMP2 -> 090303)."""
    m = re.search(r"(?<!\d)(\d{6})-C2C12", path, flags=re.IGNORECASE)
    if m:
        return m.group(1)
    m = re.search(r"(?<!\d)(0\d{5})(?!\d)", path)
    return m.group(1) if m else "unknown"


def parse_condition(leaf_name: str) -> str:
    """Condition from the sequence folder's OWN name only (see module docstring)."""
    s = leaf_name.upper().replace(" ", "")
    has_f, has_b = "FGF" in s, "BMP" in s
    if has_f and has_b:
        return "FGF2+BMP2"
    if has_f:
        return "FGF2"
    if has_b:
        return "BMP2"
    if any(t in s for t in ("CONTROL", "CTRL", "UNTREATED", "NOGF")):
        return "control"
    return "unknown"


def frame_index(name: str) -> int:
    nums = re.findall(r"\d+", os.path.splitext(os.path.basename(name))[0])
    if not nums:
        raise ValueError(f"no frame number in {name!r}")
    return int(nums[-1])


def slug(s: str) -> str:
    return re.sub(r"[^A-Za-z0-9]+", "_", s).strip("_")[:60]


def base_time(experiment: str) -> datetime:
    """Experiment date as the sequence's t0 (true date; time-of-day unknown -> 00:00 UTC)."""
    try:
        return datetime(2000 + int(experiment[:2]), int(experiment[2:4]), int(experiment[4:6]), tzinfo=timezone.utc)
    except Exception:  # noqa: BLE001
        return datetime(2009, 1, 1, tzinfo=timezone.utc)


def select_evenly(items: list, k: int) -> list:
    """k items spread evenly over a sorted list. Used per experiment: the 16
    fields are 4 dishes x 4 conditions, so an even spread over the sorted
    folder names is the best available proxy for stratifying by condition
    when folder names don't state the condition."""
    if k >= len(items):
        return list(items)
    idx = np.linspace(0, len(items) - 1, k).round().astype(int)
    return [items[i] for i in sorted(set(idx))]


# ---------------------------------------------------------------------------
# normalization + conversion
# ---------------------------------------------------------------------------

def read_raw(path: str) -> np.ndarray:
    import cv2

    img = cv2.imread(path, cv2.IMREAD_ANYDEPTH | cv2.IMREAD_GRAYSCALE)
    if img is None:
        try:
            import tifffile  # optional fallback
            img = tifffile.imread(path)
        except Exception as e:  # noqa: BLE001
            raise IOError(f"cannot read {path}: {e}")
    if img.ndim == 3:
        img = img[..., 0]
    return img


def fit_normalization(raw_paths: list[str], json_path: str, n_sample: int = 200, seed: int = 0,
                      hi_pct: float = 99.5) -> dict:
    """ONE global linear map for the whole dataset (see module docstring):
    raw 0 (camera zero) -> 0, raw p{hi_pct} over a frame sample -> 255.

    Anchored at physical zero rather than a low percentile on purpose: a dimmer
    lamp is a multiplicative change in raw counts, and a zero-anchored map keeps
    it a clean multiplicative change in 8-bit (a percentile-anchored map would
    clip dimmed shadows to black and distort the V7 instrument-drift test). It
    also yields the mid-grey background typical of 8-bit phase contrast.

    Reused from json_path if it already exists, so reruns produce
    byte-identical PNGs (= identical cache keys)."""
    if os.path.exists(json_path):
        with open(json_path) as f:
            return json.load(f)
    rng = np.random.default_rng(seed)
    pick = rng.choice(len(raw_paths), size=min(n_sample, len(raw_paths)), replace=False)
    vals = np.concatenate([read_raw(raw_paths[i])[::8, ::8].ravel() for i in pick]).astype(np.float64)
    norm = {
        "method": "global_linear_zero_to_percentile",
        "lo": 0.0,
        "hi": float(np.percentile(vals, hi_pct)),
        "hi_pct": hi_pct,
        "n_frames_sampled": int(len(pick)), "seed": seed,
        "note": "applied identically to every frame and to fault frames; never per-frame",
    }
    os.makedirs(os.path.dirname(os.path.abspath(json_path)), exist_ok=True)
    with open(json_path, "w") as f:
        json.dump(norm, f, indent=2)
    return norm


def to_uint8(raw: np.ndarray, norm: dict) -> np.ndarray:
    x = (raw.astype(np.float32) - norm["lo"]) / max(norm["hi"] - norm["lo"], 1e-6)
    return (np.clip(x, 0.0, 1.0) * 255.0 + 0.5).astype(np.uint8)


def write_png(path: str, img8: np.ndarray) -> None:
    import cv2

    os.makedirs(os.path.dirname(path), exist_ok=True)
    if not os.path.exists(path):
        tmp = path + ".tmp.png"
        cv2.imwrite(tmp, img8, [cv2.IMWRITE_PNG_COMPRESSION, 3])  # deterministic encoder settings
        os.replace(tmp, path)


# ---------------------------------------------------------------------------
# fetch
# ---------------------------------------------------------------------------

def _list_full(listing_url: str) -> list[dict]:
    return [_file_entry(it, "") for it in _pages(listing_url)]


def _collect_sequences_from_inventory(inv: dict) -> list[dict]:
    """-> [{seq_path, experiment, leaf, frames:[{name, frame_idx, download}]|None, listing}]"""
    seqs = []
    for tf in inv["tiff_folders"]:
        leaf = os.path.basename(tf["path"].rstrip("/"))
        seqs.append({"seq_path": tf["path"], "experiment": parse_experiment(tf["path"]),
                     "leaf": leaf, "listing": tf["listing"], "frames": None})
    return seqs


def _collect_sequences_from_local(src: str) -> list[dict]:
    by_dir: dict[str, list[str]] = {}
    for root, _dirs, files in os.walk(src):
        for fn in files:
            if fn.lower().endswith(TIFF_EXT):
                by_dir.setdefault(root, []).append(fn)
    seqs = []
    for d, files in sorted(by_dir.items()):
        rel = os.path.relpath(d, src)
        frames = []
        for fn in files:
            try:
                frames.append({"name": fn, "frame_idx": frame_index(fn), "local": os.path.join(d, fn)})
            except ValueError:
                pass
        seqs.append({"seq_path": rel, "experiment": parse_experiment(d), "leaf": os.path.basename(d),
                     "listing": None, "frames": sorted(frames, key=lambda x: x["frame_idx"])})
    return seqs


def fetch(out_dir: str, inventory: str | None = None, local_src: str | None = None,
          per_experiment: int = 8, stride: int = 12, max_sequences: int | None = None,
          condition_map_csv: str | None = None, seed: int = 0) -> dict:
    """Download (or read) every `stride`-th frame of the selected sequences.
    stride=12 at 5-min frames = hourly — plenty for replay cadences of 6-24 h,
    and ~1/12 the download of the full dataset."""
    import pandas as pd

    raw_dir = os.path.join(out_dir, "raw")
    png_dir = os.path.join(out_dir, "png")
    norm_path = os.path.join(out_dir, "c2c12_normalization.json")

    if local_src:
        seqs = _collect_sequences_from_local(local_src)
    else:
        with open(inventory) as f:
            inv = json.load(f)
        if inv["mode"] != "tiff_folders":
            raise SystemExit(
                f"OSF inventory mode is {inv['mode']!r}, not loose TIFF folders. This script only "
                "auto-downloads loose TIFFs. For archives: download the archives for a few sequences "
                "yourself (see the notebook's fallback cell), extract, and rerun with --local-src."
            )
        seqs = _collect_sequences_from_inventory(inv)

    cond_override = {}
    if condition_map_csv and os.path.exists(condition_map_csv):
        cm = pd.read_csv(condition_map_csv)  # columns: leaf, condition
        cond_override = dict(zip(cm["leaf"].astype(str), cm["condition"].astype(str)))

    # -- select: evenly spread within each experiment --
    by_exp: dict[str, list[dict]] = {}
    for s in seqs:
        by_exp.setdefault(s["experiment"], []).append(s)
    selected = []
    for exp in sorted(by_exp):
        items = sorted(by_exp[exp], key=lambda s: s["seq_path"])
        selected += select_evenly(items, per_experiment)
    if max_sequences:
        selected = selected[:max_sequences]
    print(f"selected {len(selected)} of {len(seqs)} sequences "
          f"({per_experiment}/experiment across {len(by_exp)} experiments)")

    # -- list + check every selected sequence first, so a naming problem stops
    # the run before anything is downloaded --
    for s in selected:
        if s["frames"] is None:
            entries = [e for e in _list_full(s["listing"]) if e["name"].lower().endswith(TIFF_EXT)]
            s["frames"] = sorted(
                [{"name": e["name"], "frame_idx": frame_index(e["name"]), "download": e["download"]} for e in entries],
                key=lambda x: x["frame_idx"],
            )
        idx = [fr["frame_idx"] for fr in s["frames"]]
        if len(set(idx)) != len(idx):
            # frame_index() takes the LAST number in the filename. If the frame
            # number sits elsewhere (e.g. "t0300_f01.tif"), every frame gets the
            # same index and the whole sequence collapses onto one raw path.
            raise SystemExit(
                f"{s['seq_path']}: {len(idx)} frames but only {len(set(idx))} distinct frame numbers "
                f"(e.g. {[fr['name'] for fr in s['frames'][:3]]}). Fix frame_index() for this naming "
                "before downloading."
            )
        s["n_frames_total"] = len(s["frames"])
        s["kept"] = s["frames"][::stride]
        s["sequence_id"] = f"c2c12_{s['experiment']}_{slug(s['leaf'])}"
        s["condition"] = cond_override.get(s["leaf"], parse_condition(s["leaf"]))

    # -- download selected frames (raw) --
    for s in selected:
        for fr in s["kept"]:
            raw_path = os.path.join(raw_dir, s["sequence_id"], f"{fr['frame_idx']:05d}.tif")
            if "local" in fr:
                if not os.path.exists(raw_path):
                    os.makedirs(os.path.dirname(raw_path), exist_ok=True)
                    shutil.copy2(fr["local"], raw_path)
            else:
                _download(fr["download"], raw_path)
            fr["raw_path"] = raw_path
        print(f"  {s['sequence_id']:<48} cond={s['condition']:<10} kept {len(s['kept'])}/{s['n_frames_total']}")

    # -- one global normalization, then convert --
    all_raw = [fr["raw_path"] for s in selected for fr in s["kept"]]
    norm = fit_normalization(all_raw, norm_path, seed=seed)
    print(f"normalization: lo={norm['lo']:.1f} hi={norm['hi']:.1f} ({norm['method']})")

    seq_rows, frame_rows = [], []
    for s in selected:
        t0 = base_time(s["experiment"])
        first_idx = s["frames"][0]["frame_idx"] if s["frames"] else 0
        for fr in s["kept"]:
            png_path = os.path.join(png_dir, s["sequence_id"], f"{fr['frame_idx']:05d}.png")
            if not os.path.exists(png_path):
                write_png(png_path, to_uint8(read_raw(fr["raw_path"]), norm))
            ts = t0 + timedelta(minutes=FRAME_INTERVAL_MIN * (fr["frame_idx"] - first_idx))
            frame_rows.append({
                "sequence_id": s["sequence_id"], "experiment": s["experiment"], "condition": s["condition"],
                "frame_idx": int(fr["frame_idx"]), "timestamp": ts.isoformat(),
                "hours_since_start": (ts - t0).total_seconds() / 3600.0,
                "png_path": png_path, "raw_path": fr["raw_path"],
            })
        kept_idx = [fr["frame_idx"] for fr in s["kept"]]
        seq_rows.append({
            "sequence_id": s["sequence_id"], "experiment": s["experiment"], "condition": s["condition"],
            "leaf": s["leaf"], "source_path": s["seq_path"], "n_frames_total": s["n_frames_total"],
            "n_frames_kept": len(s["kept"]), "stride": stride,
            "first_frame_idx": min(kept_idx) if kept_idx else -1, "last_frame_idx": max(kept_idx) if kept_idx else -1,
            "hours_span": (max(kept_idx) - min(kept_idx)) * FRAME_INTERVAL_MIN / 60 if kept_idx else 0.0,
        })

    seq_df, frames_df = pd.DataFrame(seq_rows), pd.DataFrame(frame_rows)
    seq_df.to_csv(os.path.join(out_dir, "c2c12_sequences.csv"), index=False)
    frames_df.to_csv(os.path.join(out_dir, "c2c12_frames.csv"), index=False)
    return {"sequences": seq_df, "frames": frames_df, "normalization": norm}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    d = sub.add_parser("discover")
    d.add_argument("--inventory", required=True)
    d.add_argument("--node", default=OSF_NODE)
    f = sub.add_parser("fetch")
    f.add_argument("--out", required=True)
    src = f.add_mutually_exclusive_group(required=True)
    src.add_argument("--inventory")
    src.add_argument("--local-src")
    f.add_argument("--per-experiment", type=int, default=8)
    f.add_argument("--stride", type=int, default=12)
    f.add_argument("--max-sequences", type=int, default=None)
    f.add_argument("--condition-map", default=None, help="CSV with columns leaf,condition (overrides parsing)")
    a = ap.parse_args()
    if a.cmd == "discover":
        summarize_inventory(discover(a.inventory, a.node))
    else:
        res = fetch(a.out, a.inventory, a.local_src, a.per_experiment, a.stride, a.max_sequences, a.condition_map)
        print(res["sequences"].to_string(index=False))


if __name__ == "__main__":
    sys.exit(main())
