#!/usr/bin/env python3
"""
Fetch AutoQC-Bench's test/ and splits/ directories (~53 MB) from BioStudies.

Reviewed, minimal alternative to the mmv_AutoQC repo's own
`download_autoqc_data.py` (declined here — running an unreviewed downloaded
script was not something to do just because it existed; see docs/DATASETS.md).
This script does one thing: read the dataset's own published file manifest
and pull exactly the files it lists, verifying each download's byte size
against the manifest. No repo cloning, no third-party code execution.

    python scripts/fetch_autoqc_bench.py --out data/sources/autoqc_bench

By default this pulls only `test/` and `splits/` (~53 MB). `train/` is
~2.8 GB and is the AutoQC-Bench dataset almost in its entirety — see
docs/DATASETS.md for why it's deliberately deferred to whenever Slice 4
(anomaly scoring) actually starts. Pass --include-train to pull it anyway.
"""

import argparse
import json
import os
import time
import urllib.error
import urllib.request

ACCESSION = "S-BIAD2133"
MANIFEST_URL = f"https://www.ebi.ac.uk/biostudies/files/{ACCESSION}/file_list_v02.json"
FILE_BASE_URL = f"https://www.ebi.ac.uk/biostudies/files/{ACCESSION}"

# EBI's server 403s urllib's default "Python-urllib/x.y" User-Agent after a
# batch of requests (observed: 67 files in, then every request 403'd) — a
# bot-prevention default, not a real access restriction (the same URLs are
# reachable via curl/a browser with no auth). A descriptive UA identifying
# this script, its purpose, and a contact fixes it.
HEADERS = {
    "User-Agent": "cultureQC-fetch-autoqc-bench/1.0 "
    "(research reproducibility pull of public AutoQC-Bench data; "
    f"contact: {os.environ.get('CULTUREQC_CONTACT_EMAIL', 'repo owner')})"
}


def _get(url: str, timeout: int = 30):
    req = urllib.request.Request(url, headers=HEADERS)
    return urllib.request.urlopen(req, timeout=timeout)


def fetch_manifest() -> list[dict]:
    print(f"Fetching manifest: {MANIFEST_URL}")
    with _get(MANIFEST_URL) as resp:
        return json.load(resp)


def download_file(path: str, expected_size: int, out_dir: str, retries: int = 3) -> None:
    dest = os.path.join(out_dir, path)
    if os.path.exists(dest) and os.path.getsize(dest) == expected_size:
        return  # already fetched correctly; resumable across runs
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    url = f"{FILE_BASE_URL}/{path}"
    tmp = dest + ".tmp"

    last_err = None
    for attempt in range(retries):
        try:
            with _get(url, timeout=60) as resp, open(tmp, "wb") as f:
                f.write(resp.read())
            break
        except urllib.error.HTTPError as e:
            last_err = e
            time.sleep(1.5 * (attempt + 1))
    else:
        raise IOError(f"{path}: HTTP {last_err.code} after {retries} attempts") from last_err

    got = os.path.getsize(tmp)
    if got != expected_size:
        os.remove(tmp)
        raise IOError(f"{path}: downloaded {got} bytes, manifest says {expected_size}")
    os.replace(tmp, dest)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default="data/sources/autoqc_bench")
    parser.add_argument(
        "--include-train", action="store_true",
        help="also pull train/ (~2.8 GB, ~8233 files) — see module docstring",
    )
    args = parser.parse_args()
    os.makedirs(args.out, exist_ok=True)

    manifest = fetch_manifest()
    print(f"Manifest lists {len(manifest)} files")

    prefixes = ("test/", "splits/")
    if args.include_train:
        prefixes = prefixes + ("train/",)

    wanted = [f for f in manifest if f["path"].startswith(prefixes)]
    total_bytes = sum(f["size"] for f in wanted)
    print(f"Pulling {len(wanted)} files ({total_bytes / 1e6:.1f} MB) matching {prefixes}")

    for i, f in enumerate(wanted, 1):
        download_file(f["path"], f["size"], args.out)
        if i % 20 == 0 or i == len(wanted):
            print(f"  {i}/{len(wanted)}")

    print(f"Done. Files under {args.out}:")
    for prefix in prefixes:
        n = sum(1 for f in wanted if f["path"].startswith(prefix))
        print(f"  {prefix} — {n} files")


if __name__ == "__main__":
    main()
