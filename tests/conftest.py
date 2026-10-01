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
