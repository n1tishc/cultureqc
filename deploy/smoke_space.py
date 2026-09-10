"""Real-model smoke test: .venv/bin/python deploy/smoke_space.py [--url URL].

Uses repository synthetic QC fixtures. This checks deployment and regression
behavior, not generalization to real contaminated cultures. CPU runs take minutes.
"""
import argparse
import hashlib
import json
from pathlib import Path
import time


def main():
    import httpx
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default="https://longgrainrice-cultureqc-api.hf.space")
    args = parser.parse_args()
    root = Path(__file__).resolve().parent.parent
    cases = [("normal_00005.png", "normal"), ("contam_00015.png", "contamination_suspected"),
             ("detach_00003.png", "detachment"), ("imgq_00012.png", "image_quality")]
    with httpx.Client(base_url=args.url, timeout=300) as client:
        deadline = time.monotonic() + 180
        while True:
            health = client.get("/health", timeout=15)
            health.raise_for_status()
            readiness = health.json()
            assert not readiness.get("error"), readiness
            if readiness["models_loaded"]:
                break
            assert time.monotonic() < deadline, "Models did not become ready within 180s"
            time.sleep(5)
        for name, expected in cases:
            body = (root / "test-data" / name).read_bytes()
            started = time.monotonic()
            response = client.post("/analyze", files={"image": (name, body, "image/png")})
            response.raise_for_status()
            result = response.json()
            record = dict(result["record"])
            digest = record.pop("record_hash")
            canonical = json.dumps(record, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
            assert hashlib.sha256(canonical.encode()).hexdigest() == digest, "Returned record hash mismatch"
            assert hashlib.sha256(result["record_canonical"].encode()).hexdigest() == digest
            assert record["image_hash"] == hashlib.sha256(body).hexdigest(), "Image hash mismatch"
            assert record["image_ref"] == name
            assert 0 <= result["confluency_pct"] <= 100
            assert result["confluency_method"] == "probmap"
            assert abs(sum(result["per_class_probs"].values()) - 1) < .002
            assert result["qc_flag"] == expected, (name, result["qc_flag"], expected)
            for x1, y1, x2, y2 in result["evidence_boxes"]:
                assert 0 <= x1 <= x2 <= 1 and 0 <= y1 <= y2 <= 1
            print(f"PASS {name}: {result['qc_flag']}, confluency={result['confluency_pct']}%, "
                  f"{time.monotonic()-started:.1f}s, image and record hashes verified", flush=True)


if __name__ == "__main__":
    main()
