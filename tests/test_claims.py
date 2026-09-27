"""Claims policy (spec v4 §12) over everything a viewer reads, plus the
detectability matrix's evidence rule (§2B.5)."""

import glob
import os
import re

import pytest

from culture import claims, detectability

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEXT_FILES = ["README.md", "configs/detectability.yaml", *sorted(
    os.path.relpath(p, REPO) for p in glob.glob(os.path.join(REPO, "demo", "replays", "*.json")))]
PY_UI_FILES = ["demo/app.py", "demo/flask_timeline.py", "demo/replay_timeline.py", "culture/rationale.py", "culture/detectability.py", "culture/anomaly.py"]


@pytest.mark.parametrize("text", [
    "Mycoplasma detected in flask 3.",
    "The flask is mycoplasma-free.",
    "cultureQC detects mycoplasma early.",
    "Mycoplasma risk: ELEVATED",
    "Real-time contamination detection on every visit.",
    "It replaces sterility testing.",
    "cultureQC is Part 11 compliant.",
    "Integrates with BioFlow out of the box.",
    "98% test accuracy.",
    "Contamination AUROC 1.00 on held-out sequences.",
    "SPC detects growth stalls within 3 visits.",
    "The app monitors anomaly scores over time.",
    "Predicts the passage crossing within 4.9 h.",
    "QUARANTINE_RECOMMENDED",
    "About a minute per image on 2 vCPU.",
    "Reports the cell doubling time.",
])
def test_checker_catches(text):
    assert claims.violations(text)


@pytest.mark.parametrize("text", [
    "Brightfield imaging cannot detect mycoplasma; confirm by PCR.",
    "cultureQC does not replace sterility testing or PCR.",
    "Designed to attach to an existing Part 11 audit trail; not Part 11 compliant on its own.",
    "98% test accuracy on synthetic tiles.",
    "AUROC 1.00 on simulated faults (n = 2).",
    "Growth stalls are not detectable at the tested setup.",
    "Passage forecast error 4.9 h (backtest: n = 5 sequences, 50% target).",
    "689 s per FOV at 2 threads (V9, results/live_latency.md).",
    "area doubling time, never cell doubling time",
    "Live demo",
])
def test_checker_allows(text):
    assert not claims.violations(text)


def test_viewer_facing_text_follows_claims_policy():
    found = []
    for rel in TEXT_FILES:
        with open(os.path.join(REPO, rel)) as f:
            found += claims.violations(f.read(), rel)
    for rel in PY_UI_FILES:
        found += claims.violations(claims.python_strings(os.path.join(REPO, rel)), rel + " (strings)")
    assert not found, "claims policy violations:\n" + "\n".join(found)


def test_detectability_rows_cite_evidence():
    m = detectability.load()
    assert m["rows"]
    for r in m["rows"]:
        assert set(r) >= {"issue", "detectable_here", "evidence", "confirm_with"}, r
        assert re.search(r"\bV\d|results/|tests/|not tested|not optically detectable", r["evidence"], re.I), r["issue"]
    assert re.fullmatch(r"[0-9a-f]{64}", detectability.config_hash())
    assert detectability.config_hash()[:16] in detectability.to_html()
