"""Host-managed activation is explicit, traceable, and not a local approval claim."""

from copy import deepcopy
import os

import jsonschema
import numpy as np
import pytest

from culture.anomaly import bank_hash, load_banks
from culture.records import RecordWriter
from test_decision_provenance import runtime


@pytest.mark.parametrize("surface", ["library", "console"])
def test_host_managed_configuration_is_explicit(runtime, surface):
    record = getattr(runtime, surface)()
    activation = record["configuration_activation"]
    assert activation["mode"] == "host_managed"
    assert activation["local_enforcement"] is False
    assert activation["host_approval_ref"] is None
    assert len(activation["configuration_sha256"]) == 64
    assert record["decision"]["host_actionable"] is False


def test_console_and_library_identify_same_configuration(runtime):
    assert runtime.library()["configuration_activation"] == runtime.console()["configuration_activation"]


def test_profile_edit_is_traceable_but_never_claimed_locally_approved(runtime):
    before = runtime.library()
    runtime.profile_path.write_text(runtime.profile_path.read_text() + "\n# new host configuration revision\n")
    after = runtime.library()
    assert before["config_hashes"] != after["config_hashes"]
    assert before["configuration_activation"]["configuration_sha256"] != after["configuration_activation"]["configuration_sha256"]
    assert after["configuration_activation"]["local_enforcement"] is False
    assert after["passage_eligibility"]["eligible"] is False


@pytest.mark.parametrize("mutation", ["missing", "local", "identity"])
def test_activation_claims_are_validated_before_append(runtime, tmp_path, mutation):
    record = runtime.library()
    if mutation == "missing":
        record.pop("configuration_activation")
    elif mutation == "local":
        record["configuration_activation"]["local_enforcement"] = True
    else:
        record["configuration_activation"]["configuration_sha256"] = "0" * 64
    target = tmp_path / "rejected.jsonl"
    with pytest.raises((ValueError, jsonschema.ValidationError)):
        RecordWriter(str(target)).append(record)
    assert not target.exists() or target.stat().st_size == 0


def test_schema_06_does_not_gain_a_retroactive_activation_requirement(runtime, tmp_path):
    historical = deepcopy(runtime.library())
    historical["schema_version"] = "0.6"
    historical.pop("configuration_activation")
    out = RecordWriter(str(tmp_path / "historical.jsonl")).append(historical)
    assert "configuration_activation" not in out


def test_bank_replacement_requires_matching_configuration(tmp_path):
    path = tmp_path / "banks.npz"
    first = np.ones((2, 3), dtype=np.float32)
    second = first * 2
    cfg_first = {"bank": {"sha256": bank_hash([first])}}
    cfg_second = {"bank": {"sha256": bank_hash([second])}}
    np.savez(path, bin_0=first)
    banks, reason = load_banks(cfg_first, str(path))
    assert reason is None
    with pytest.raises(ValueError):
        banks["bin_0"][0, 0] = 42
    replacement = tmp_path / "replacement.npz"
    np.savez(replacement, bin_0=second)
    os.replace(replacement, path)
    assert load_banks(cfg_first, str(path))[0] is None
    updated, reason = load_banks(cfg_second, str(path))
    assert reason is None
    np.testing.assert_array_equal(updated["bin_0"], second)
    np.testing.assert_array_equal(banks["bin_0"], first)
    path.unlink()
    assert load_banks(cfg_second, str(path))[0] is None
    np.savez(path, bin_0=first)
    assert load_banks(cfg_first, str(path))[0] is not None


def test_missing_or_corrupt_bank_can_recover_without_restart(tmp_path):
    path = tmp_path / "banks.npz"
    bank = np.ones((2, 3), dtype=np.float32)
    cfg = {"bank": {"sha256": bank_hash([bank])}}
    assert load_banks(cfg, str(path))[0] is None
    path.write_bytes(b"not a numpy archive")
    assert load_banks(cfg, str(path))[0] is None
    with path.open("wb") as stream:
        np.save(stream, bank)
    assert load_banks(cfg, str(path))[0] is None
    np.savez(path, bin_0=bank)
    assert load_banks(cfg, str(path))[0] is not None


@pytest.mark.parametrize("value", ["2099-01-01", "2099-01-01T00:00:00", "invalid"])
def test_cli_requires_timezone_for_scheduled_activation(value):
    import argparse
    from scripts.approve_change import effective_time
    with pytest.raises(argparse.ArgumentTypeError):
        effective_time(value)


def test_cli_preserves_explicit_effective_time():
    from scripts.approve_change import effective_time
    assert effective_time("2099-01-01T00:00:00+03:00").isoformat() == "2099-01-01T00:00:00+03:00"
