"""
cultureqc.history — per-flask lineage/segment/visit history (cultureQC_upgrade.md §5.3).

Structure: lineage -> segments -> visits, plus events (SEEDED, FED, PASSAGED,
HARVESTED, NOTE). Append-only; each row hash-chained to the previous row of
the SAME lineage.

Storage design (a deliberate choice, not the only valid one): one JSONL file
per lineage (`<history_dir>/<lineage_id>.jsonl`), reusing culture.records'
RecordWriter/verify_chain exactly as-is rather than inventing a second
hash-chain implementation — RecordWriter already chains strictly to "the
previous line in this file," so giving each lineage its own file makes that
identical to "chained to the previous row of the same lineage," with no new
chaining logic needed. Visits and events for one lineage share a single
file/chain, distinguished by a "row_type" field ("visit" | "event"), in
strict chronological append order — one tamper-evident timeline per lineage
covering everything that happened to it, rather than two chains that would
need cross-referencing. Slice 7's tamper verifier reads this the same way it
reads culture/records.py's per-image logs.

get_segment(segment_id) scans every lineage file for matching rows, since
segment_id doesn't index directly to a lineage file — fine at the scale this
product operates at (per-lab flask counts, not a fleet); add an index file
if this becomes a real bottleneck, don't guess that it will be one now.

Visits are validated against schemas/visit_summary.v1.json before being
written — a malformed visit fails loudly at append time, not silently in
the chain. Quality-gate-failing visits ARE still written (the spec: "failing
visits are recorded with reason codes") but are excluded from
trend_windows() and get_lineage(..., trend_only=True) — "they do not enter
trend computations" is enforced here, not by the quality gate itself.

Usage:
    from culture.history import History
    h = History("history")
    h.append_visit(visit_summary_dict)
    h.append_event(lineage_id="L1", segment_id="S1", event_type="PASSAGED",
                    split_ratio=0.2, child_segment_ids=["S2"])
    h.get_lineage("L1")
    h.get_segment("S1")
"""

from __future__ import annotations

import glob
import json
import os

from culture.records import RecordWriter, verify_chain

EVENT_TYPES = {"SEEDED", "FED", "PASSAGED", "HARVESTED", "NOTE"}

_SCHEMA_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "schemas", "visit_summary.v1.json"
)


class ModelVersionChange(Exception):
    """Raised by trend functions when consecutive visits in a window don't
    share model_versions — per §5.3, trend computations must refuse to mix
    them, not silently average across a retrain."""


def _load_schema():
    with open(_SCHEMA_PATH) as f:
        return json.load(f)


class History:
    def __init__(self, history_dir: str):
        self.dir = history_dir
        os.makedirs(history_dir, exist_ok=True)
        self._writers: dict[str, RecordWriter] = {}
        self._schema = _load_schema()

    def _path(self, lineage_id: str) -> str:
        return os.path.join(self.dir, f"{lineage_id}.jsonl")

    def _writer(self, lineage_id: str) -> RecordWriter:
        if lineage_id not in self._writers:
            self._writers[lineage_id] = RecordWriter(self._path(lineage_id))
        return self._writers[lineage_id]

    # -- append -----------------------------------------------------------

    def append_visit(self, visit: dict) -> dict:
        """Validates against schemas/visit_summary.v1.json, then appends to
        its lineage's chain with row_type='visit'. Returns the finalized
        (hash-chained) row."""
        import jsonschema

        jsonschema.validate(visit, self._schema)
        lineage_id = visit["lineage_id"]
        row = dict(visit)
        row["row_type"] = "visit"
        return self._writer(lineage_id).append(row)

    def append_event(
        self, lineage_id: str, segment_id: str, event_type: str, **fields
    ) -> dict:
        """SEEDED (seeding_density=...), FED, PASSAGED (split_ratio=...,
        child_segment_ids=[...]), HARVESTED, NOTE (note=...). Extra fields
        are passed through as-is — no fixed schema per event type (the spec
        doesn't define one), but event_type itself is checked against the
        known set so a typo fails loudly rather than silently drifting the
        vocabulary."""
        if event_type not in EVENT_TYPES:
            raise ValueError(f"unknown event_type {event_type!r}, expected one of {sorted(EVENT_TYPES)}")
        row = {
            "row_type": "event",
            "lineage_id": lineage_id,
            "segment_id": segment_id,
            "event_type": event_type,
            **fields,
        }
        return self._writer(lineage_id).append(row)

    # -- read ---------------------------------------------------------------

    def get_lineage(self, lineage_id: str, trend_only: bool = False) -> list[dict]:
        """All rows (visits + events) for one lineage, in append order.
        trend_only=True drops quality-gate-failing visits (events are never
        filtered — they're not trend data)."""
        path = self._path(lineage_id)
        if not os.path.exists(path):
            return []
        rows = []
        with open(path) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                row = json.loads(line)
                if trend_only and row.get("row_type") == "visit" and not row.get("quality", {}).get("pass", True):
                    continue
                rows.append(row)
        return rows

    def get_segment(self, segment_id: str) -> list[dict]:
        """All rows for one segment, scanning every lineage file — see
        module docstring for why there's no direct index."""
        rows = []
        for path in sorted(glob.glob(os.path.join(self.dir, "*.jsonl"))):
            with open(path) as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    row = json.loads(line)
                    if row.get("segment_id") == segment_id:
                        rows.append(row)
        return rows

    # -- integrity ----------------------------------------------------------

    def verify_lineage(self, lineage_id: str) -> tuple[bool, int | None]:
        """(True, None) if the lineage's hash chain is intact, else
        (False, 1-indexed bad line number). Reuses records.verify_chain
        directly — same chain format, same verifier."""
        return verify_chain(self._path(lineage_id))

    # -- trend ----------------------------------------------------------------

    def trend_windows(self, segment_id: str) -> list[list[dict]]:
        """Partition a segment's trend-eligible visits (quality-passing,
        chronological) into windows of contiguous matching model_versions —
        §5.3: "must refuse to mix visits with different model_versions;
        return MODEL_VERSION_CHANGE and start a new trend window." Returns
        the windows themselves rather than raising, since a version change
        mid-segment is an expected, handleable event (start a new window),
        not necessarily an error — callers that want the strict "refuse and
        signal" behavior get it via require_single_window()."""
        visits = [
            r for r in self.get_segment(segment_id)
            if r.get("row_type") == "visit" and r.get("quality", {}).get("pass", True)
        ]
        visits.sort(key=lambda r: r["timestamp"])

        windows: list[list[dict]] = []
        for v in visits:
            if windows and windows[-1][-1]["model_versions"] == v["model_versions"]:
                windows[-1].append(v)
            else:
                windows.append([v])
        return windows

    def require_single_window(self, segment_id: str) -> list[dict]:
        """The strict form: return the segment's trend-eligible visits if
        they all share one model_versions, else raise ModelVersionChange."""
        windows = self.trend_windows(segment_id)
        if len(windows) > 1:
            raise ModelVersionChange(
                f"segment {segment_id!r} has {len(windows)} model_versions windows "
                f"({[len(w) for w in windows]} visits each) — trend computation refused"
            )
        return windows[0] if windows else []
