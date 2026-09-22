#!/usr/bin/env python3
"""
Fetch EVICAN's eval2019 held-out split (images + COCO masks) from its
Dataverse (Edmond/Max Planck Society) record.

    python scripts/fetch_evican.py --out data/sources/evican

CC BY 4.0 (Parekh et al. 2020, Bioinformatics 36(12):3863-3870). See
docs/DATASETS.md for the full license/provenance verification and why this
uses the Dataverse REST API rather than the paper-cited URL (dead, redirects
to a human-facing page behind an anti-scraping wall) or a full-dataset clone
(only eval2019 + its 2-category masks are needed here; train/val and the
60-category variant are not).

Queries the dataset's own file listing at runtime (rather than hardcoding
file IDs, which Dataverse assigns per-upload and could change on a new
version) and verifies each download's MD5 against the record's own manifest.
"""

import argparse
import hashlib
import json
import os
import urllib.request

PERSISTENT_ID = "doi:10.17617/3.AJBV1S"
API_BASE = "https://edmond.mpg.de/api"

# Only the eval2019 held-out split, 2-category (Cell/Nucleus) masks — not
# train2019/val2019 (2.2 GB / 540 MB, unneeded), not the 60-category variant
# (EVICAN60 — the per-cell-line breakdown, not needed for confluency GT).
WANTED_SUFFIXES = (
    "EVICAN_eval2019.zip",
    "instances_eval2019_easy_EVICAN2.json",
    "instances_eval2019_medium_EVICAN2.json",
    "instances_eval2019_difficult_EVICAN2.json",
)


def fetch_file_list() -> list[dict]:
    url = f"{API_BASE}/datasets/:persistentId/?persistentId={PERSISTENT_ID}"
    print(f"Fetching dataset metadata: {url}")
    with urllib.request.urlopen(url, timeout=30) as resp:
        meta = json.load(resp)
    return meta["data"]["latestVersion"]["files"]


def md5sum(path: str) -> str:
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()


def download_one(file_id: int, label: str, expected_md5: str, out_dir: str) -> None:
    dest = os.path.join(out_dir, label)
    if os.path.exists(dest) and md5sum(dest) == expected_md5:
        print(f"  already have {label} (md5 verified)")
        return
    url = f"{API_BASE}/access/datafile/{file_id}"
    print(f"  downloading {label} ...")
    tmp = dest + ".tmp"
    urllib.request.urlretrieve(url, tmp)
    got_md5 = md5sum(tmp)
    if got_md5 != expected_md5:
        os.remove(tmp)
        raise IOError(f"{label}: md5 {got_md5} != expected {expected_md5}")
    os.replace(tmp, dest)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default="data/sources/evican")
    args = parser.parse_args()
    os.makedirs(args.out, exist_ok=True)

    files = fetch_file_list()
    wanted = [f for f in files if f.get("label", "") in WANTED_SUFFIXES]
    if len(wanted) != len(WANTED_SUFFIXES):
        found = {f.get("label") for f in wanted}
        missing = set(WANTED_SUFFIXES) - found
        raise SystemExit(f"Dataverse record is missing expected files: {missing}")

    for f in wanted:
        df = f["dataFile"]
        download_one(df["id"], f["label"], df["md5"], args.out)

    zip_path = os.path.join(args.out, "EVICAN_eval2019.zip")
    images_dir = os.path.join(args.out, "eval2019_images")
    n_jpgs_now = len([f for f in os.listdir(images_dir) if f.lower().endswith(".jpg")]) if os.path.isdir(images_dir) else 0
    if n_jpgs_now < 98:
        # The zip has NO top-level folder — its 98 .jpg files sit flat at the
        # zip root (verified by listing it directly) — so extract straight
        # into images_dir rather than into args.out and hunting for a
        # subfolder to rename (there isn't one).
        print("Extracting EVICAN_eval2019.zip ...")
        import zipfile
        os.makedirs(images_dir, exist_ok=True)
        with zipfile.ZipFile(zip_path) as zf:
            zf.extractall(images_dir)

    n_images = len([f for f in os.listdir(images_dir) if f.lower().endswith(".jpg")]) if os.path.isdir(images_dir) else 0
    if n_images != 98:
        raise SystemExit(f"expected 98 EVICAN eval2019 images, found {n_images} in {images_dir}")
    print(f"Done. {n_images} images in {images_dir}")


if __name__ == "__main__":
    main()
