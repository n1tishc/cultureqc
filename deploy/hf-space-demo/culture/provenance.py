"""Request-local config reads and immutable, inference-free decision replay."""

from contextvars import ContextVar
from copy import deepcopy
from dataclasses import asdict
from datetime import datetime
from functools import wraps
import hashlib
import json
import inspect
import os

import yaml

_configs = ContextVar("cultureqc_consumed_configs", default=None)


def capturing_configs():
    return _configs.get() is not None


def capture_configs(function):
    @wraps(function)
    def captured(*args, **kwargs):
        if capturing_configs():
            return function(*args, **kwargs)
        token = _configs.set({})
        try:
            return function(*args, **kwargs)
        finally:
            _configs.reset(token)
    return captured


def load_yaml(path, optional=False):
    """Read once per request and retain the exact bytes parsed, including absence."""
    source = os.path.abspath(os.fspath(path))
    ledger = _configs.get()
    if ledger is None or source not in ledger:
        try:
            with open(source, "rb") as stream:
                raw = stream.read()
            entry = {"source_path": source, "sha256": hashlib.sha256(raw).hexdigest(),
                     "text": raw.decode("utf-8"), "status": "read"}
        except FileNotFoundError:
            entry = {"source_path": source, "sha256": None, "text": None, "status": "missing"}
        if ledger is not None:
            ledger[source] = entry
    else:
        entry = ledger[source]
    if entry["status"] == "missing":
        if optional:
            return None
        raise FileNotFoundError(source)
    return yaml.safe_load(entry["text"])


def config_snapshot():
    return deepcopy(list((_configs.get() or {}).values()))


def snapshot_hashes(snapshot):
    return {entry["source_path"]: entry["sha256"] for entry in snapshot if entry["status"] == "read"}


def _digest(value):
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False)
    return hashlib.sha256(raw.encode()).hexdigest()


def configuration_activation(snapshot, decision_inputs):
    """Identify consumed configuration without claiming local activation approval."""
    values = decision_inputs["values"]
    configs = [{name: entry[name] for name in ("source_path", "status", "sha256")}
               for entry in sorted(snapshot, key=lambda entry: entry["source_path"])]
    identity = {"configs": configs, "policy": decision_inputs["policy"],
                **{name: values[name] for name in ("line_config", "check_policy", "profile")}}
    return {"mode": "host_managed", "local_enforcement": False, "host_approval_ref": None,
            "configuration_sha256": _digest(identity)}


def recorded_decision(**kwargs):
    from culture.rules import CheckPolicy, DEFAULT_CONFIG, RULES_VERSION, evaluate_decision

    bound = inspect.signature(evaluate_decision).bind(**kwargs)
    bound.apply_defaults()
    values = deepcopy(bound.arguments)
    values["line_config"] = asdict(values.get("line_config") or DEFAULT_CONFIG)
    values["check_policy"] = asdict(values.get("check_policy") or CheckPolicy())
    values["profile"] = asdict(values["profile"]) if values.get("profile") is not None else None
    for name in ("confluency_pct", "confluency_confidence", "qc_confidence", "hours_since_passage",
                 "hours_since_feed", "band_pp"):
        if type(values[name]) in (int, float):
            values[name] = float(values[name])
    for name, value in values["line_config"].items():
        if type(value) in (int, float):
            values["line_config"][name] = float(value)
    payload = {"policy": RULES_VERSION, "values": values}
    snapshot = {**payload, "sha256": _digest(payload)}
    return _evaluate(snapshot), snapshot


def _evaluate(snapshot):
    from culture.profiles import Profile
    from culture.rules import CheckPolicy, LineConfig, RULES_VERSION, evaluate_decision

    if set(snapshot) != {"policy", "values", "sha256"} or snapshot["policy"] != RULES_VERSION:
        raise ValueError("Unsupported decision snapshot/policy; no current-policy fallback")
    payload = {name: snapshot[name] for name in ("policy", "values")}
    if snapshot["sha256"] != _digest(payload):
        raise ValueError("Decision input snapshot hash mismatch")
    values = deepcopy(snapshot["values"])
    values["line_config"] = LineConfig(**values["line_config"])
    values["check_policy"] = CheckPolicy(**values["check_policy"])
    values["profile"] = Profile(**values["profile"]) if values["profile"] is not None else None
    return evaluate_decision(**values)


def replay_decision(record, policy_version):
    """Replay only a named supported policy; no files, models or configuration reads.

    Historical records lacking a snapshot are deliberately not reconstructible.
    Hashes detect inconsistency, not an attacker who can rewrite every hash.
    """
    snapshot = record.get("decision_inputs")
    if not isinstance(snapshot, dict):
        raise ValueError("Historical record has no immutable decision input snapshot")
    if policy_version != record.get("decided_by") or policy_version != snapshot.get("policy"):
        raise ValueError("Requested policy does not match the recorded policy")
    result = _evaluate(snapshot)
    values = snapshot["values"]
    for name in ("confluency_pct", "confluency_confidence"):
        if record.get(name) != values[name]:
            raise ValueError(f"Recorded {name} differs from decision inputs")
    from culture.profiles import Profile
    profile = Profile(**values["profile"]) if values["profile"] else None
    if profile is not None:
        if record.get("confluency_profile") != profile.record_fields():
            raise ValueError("Recorded profile differs from decision inputs")
        if record.get("confluency_interval") != profile.interval(values["confluency_pct"]):
            raise ValueError("Recorded interval differs from decision inputs")
        eligibility = profile.passage_eligibility(values["confluency_pct"],
                                                  values["line_config"]["target_confluency"], values["setup_context"])
        if record.get("passage_eligibility") != eligibility:
            raise ValueError("Recorded passage eligibility differs from decision inputs")
    expected_qc = (record.get("qc_flag"), record.get("qc_confidence")) if record.get("qc_used_in_decision") else (None, None)
    if expected_qc != (values["qc_flag"], values["qc_confidence"]):
        raise ValueError("Recorded QC differs from decision inputs")
    quality = record.get("quality_gate") or {}
    if (quality.get("passed"), quality.get("reasons")) != (values["quality_passed"], values["quality_reasons"]):
        raise ValueError("Recorded quality differs from decision inputs")
    if record.get("anomaly_flag") != values["anomaly_flag"]:
        raise ValueError("Recorded anomaly differs from decision inputs")
    context = values["setup_context"] or {}
    if (context.get("cell_line") != record.get("cell_line")
            or context.get("model_sha256") != (record.get("model_check") or {}).get("sha256")):
        raise ValueError("Recorded setup context differs from decision inputs")
    if (result.action != record.get("recommended_action") or result.reason != record.get("action_reason")
            or result.record_fields() != record.get("decision")):
        raise ValueError("Stored decision does not match its input snapshot")
    return result


def capture_time(value):
    if value is None:
        return {"captured_at": None, "capture_time_source": "unknown"}
    if not isinstance(value, str):
        raise ValueError("captured_at must be an ISO timestamp with a timezone")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as error:
        raise ValueError("captured_at must be an ISO timestamp with a timezone") from error
    if parsed.tzinfo is None:
        raise ValueError("captured_at must include a timezone")
    return {"captured_at": value, "capture_time_source": "host"}


def map_provenance(probmap):
    from culture.cache import probmap_sha256

    return {"confluency_map_hash": probmap_sha256(probmap) if probmap is not None else None,
            "map_provenance": {"status": "captured" if probmap is not None else "unavailable",
                               "representation": "culture.cache.downsample_probmap/x1000-int16-v1"}}
