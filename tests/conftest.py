"""Shared test helpers.

CI (.github/workflows/tests.yml, job "Python tests") installs no model stack:
no torch, no cellpose, no gradio, and has no compute cache. A test that needs
one of those skips there with the reason below instead of failing; locally,
with requirements.txt installed, every test runs.
"""
import importlib.util

import pytest


def requires(*modules):
    """Skip unless every module in `modules` is importable."""
    missing = [m for m in modules if importlib.util.find_spec(m) is None]
    return pytest.mark.skipif(bool(missing), reason=f"needs {', '.join(missing)} (not installed in CI)")


def require_module(name):
    """Module-level skip for a test file that imports `name` at the top."""
    return pytest.importorskip(name, reason=f"needs {name} (not installed in CI)")


def synthetic_passage_profile(band_pp=5.0):
    """Rule-only fixture. These invented approvals are not scientific evidence."""
    from culture.profiles import Profile

    context = {"setup_id": "synthetic-setup-v1", "cell_line": "synthetic-line", "model_sha256": "a" * 64}
    entry = {"cutoff": 0.0, "band_pp": band_pp, "status": "validated",
             "acceptance": {name: "pass" for name in ("A1", "A2", "A3", "A4", "A5")},
             "validated_scope": {**context, "reading_range_pct": [0, 100], "target_range_pct": [80, 80]},
             "action_eligibility": {"status": "eligible", "reason": "Synthetic rule fixture only",
                                    "approval_ref": "synthetic-not-biological-validation"}}
    return Profile("synthetic", 0.0, band_pp, "validated", "Synthetic fixture", entry=entry), context
