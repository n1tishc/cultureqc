"""
demo/replay_3d.py — the Flask Timeline's 3D space x time view: one layer per
visit, stacked by hours since the start of the recording, each showing where
the frame's Cellpose-SAM map counts cell, with the 3 FOV crops the visit's
confluency came from.

Maps are the compute cache's own (scripts/export_replay_maps.py copies them
unchanged into demo/replay_maps/); each layer's SHA-256 is re-checked against
the index when drawn. Nothing is drawn between visits. The visit's reported
number is Cellpose-SAM run on each crop separately, so the boxes show where the
crops were, not their numbers; each layer's label gives the recorded 3-FOV mean
and the recorded full-frame confluency side by side.
"""

from __future__ import annotations

import functools
import html
import json
import os

import numpy as np
import plotly.graph_objects as go

from culture.cache import PROBMAP_DOWNSAMPLE, probmap_sha256
from demo import viz3d

MAPS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "replay_maps")
DRAW_STRIDE = 4                      # every 4th point of the 1/4-resolution map (1/16 of the frame)

CELL = "#22c55e"
FOV = "#3b82f6"
FRAME = "#64748b"
REIMAGE = "#ef4444"
FLAG = "#f59e0b"


@functools.lru_cache(maxsize=1)
def load_index() -> dict | None:
    path = os.path.join(MAPS_DIR, "maps.json")
    if not os.path.exists(path):
        return None
    with open(path) as f:
        return json.load(f)


@functools.lru_cache(maxsize=8)
def load_maps(scenario: str) -> np.ndarray:
    entry = load_index()["replays"][scenario]
    with np.load(os.path.join(MAPS_DIR, entry["file"])) as npz:
        return npz["prob_x1000"]


def available(scenario: str) -> bool:
    idx = load_index()
    return idx is not None and scenario in idx["replays"]


def verified_layers(scenario: str) -> tuple[int, int]:
    """(maps whose SHA-256 matches the index, layers)."""
    layers = load_index()["replays"][scenario]["layers"]
    maps = load_maps(scenario)
    return sum(probmap_sha256(m) == L["map_sha256"] for m, L in zip(maps, layers)), len(layers)


def _rect(y0, x0, h, w, z):
    return [x0, x0 + w, x0 + w, x0, x0, None], [y0, y0, y0 + h, y0 + h, y0, None], [z] * 5 + [None]


def figure(scenario: str, doc: dict) -> go.Figure:
    """One group of traces per visit (its cell points, frame outline, FOV boxes
    and hover marker), each tagged meta={"hours": ...}, so the page script
    (demo/viz3d.py) can build the stack up visit by visit. Complete as drawn:
    without the script every visit is visible."""
    idx = load_index()
    fh, fw = idx["frame_hw"]
    layers = idx["replays"][scenario]["layers"]
    maps = load_maps(scenario)
    flags = {v["visit"]: bool(v.get("anomaly_flag")) for v in doc["visits"]}
    d = PROBMAP_DOWNSAMPLE * DRAW_STRIDE
    styles = {"ok": (FRAME, "solid", "visit (quality gate pass)"), "flag": (FLAG, "solid", "anomaly flag"),
              "reimage": (REIMAGE, "dash", "REIMAGE (quality gate fail)")}
    legend_done: set[str] = set()

    def legend(group: str) -> bool:
        first = group not in legend_done
        legend_done.add(group)
        return first

    traces = []
    for m, L in zip(maps, layers):
        z = L["hours"]
        meta = {"hours": z}
        ys, xs = np.nonzero(m[::DRAW_STRIDE, ::DRAW_STRIDE] > 0)
        traces.append(go.Scatter3d(
            x=xs * d, y=ys * d, z=np.full(len(xs), z), mode="markers",
            marker=dict(size=1.6, color=CELL, opacity=0.55), hoverinfo="skip", name="counted as cell",
            legendgroup="cell", showlegend=legend("cell"), meta=meta))
        kind = "reimage" if not L["quality_pass"] else ("flag" if flags.get(L["visit"]) else "ok")
        color, dash, name = styles[kind]
        x, y, zz = _rect(0, 0, fh, fw, z)
        traces.append(go.Scatter3d(x=x, y=y, z=zz, mode="lines", line=dict(color=color, width=3, dash=dash),
                                   hoverinfo="skip", name=name, legendgroup=kind, showlegend=legend(kind), meta=meta))
        bx, by, bz = [], [], []
        for box in L["fov_boxes"]:
            for acc, part in zip((bx, by, bz), _rect(*box, z)):
                acc.extend(part)
        traces.append(go.Scatter3d(x=bx, y=by, z=bz, mode="lines", line=dict(color=FOV, width=4), hoverinfo="skip",
                                   name="3 FOV crops (the visit's number)", legendgroup="fov",
                                   showlegend=legend("fov"), meta=meta))
        gate = ("quality gate: pass" if L["quality_pass"]
                else "REIMAGE: " + ", ".join(L["quality_reasons"]) + " (not in the trend)")
        hover = (f"visit {L['visit']} · {z:.1f} h<br>3-FOV mean {L['fov_mean_recorded']:.1f}% "
                 f"(crops {', '.join(f'{p:.1f}' for p in L['fov_pct_recorded'])})<br>"
                 f"full frame {L['frame_pct_recorded']:.1f}%<br>{html.escape(gate)}"
                 f"{'<br>anomaly flag' if flags.get(L['visit']) else ''}"
                 f"<br>frame {L['image_sha256'][:12]}… map {L['map_sha256'][:12]}…")
        traces.append(go.Scatter3d(x=[fw], y=[0], z=[z], mode="markers+text",
                                   marker=dict(size=4, color="#e2e8f0"), text=[f"{z:.1f} h"],
                                   textfont=dict(size=10, color="#94a3b8"), textposition="middle right",
                                   hovertext=[hover], hoverinfo="text", name="visit details (hover)",
                                   legendgroup="hover", showlegend=legend("hover"), meta=meta))
    onset = (doc.get("fault") or {}).get("onset_hours")
    if onset is not None:
        x, y, z = _rect(0, 0, fh, fw, onset)
        traces.append(go.Scatter3d(x=x, y=y, z=z, mode="lines", line=dict(color="#a855f7", width=2, dash="dot"),
                                   hoverinfo="skip", name=f"simulated fault onset ({onset:g} h)",
                                   meta={"hours": onset}))

    axis = dict(showbackground=False, gridcolor="rgba(148,163,184,0.18)", color="#94a3b8",
                title_font=dict(size=11), tickfont=dict(size=10))
    fig = go.Figure(traces)
    fig.update_layout(
        scene=dict(xaxis=dict(axis, title="x (px)", range=[0, fw]),
                   yaxis=dict(axis, title="y (px)", range=[fh, 0]),
                   zaxis=dict(axis, title="hours since start", range=[0, max([L["hours"] for L in layers] + [onset or 0]) * 1.02]),
                   aspectmode="manual", aspectratio=dict(x=1.0, y=fh / fw, z=1.15),
                   camera=dict(eye=dict(x=1.45, y=-1.45, z=0.55))),
        paper_bgcolor="rgba(0,0,0,0)", font=dict(color="#cbd5e1"), height=620,
        margin=dict(l=0, r=0, t=0, b=0),
        legend=dict(orientation="h", y=1.0, x=0, font=dict(size=11), bgcolor="rgba(0,0,0,0)"),
        meta=viz3d.meta("timeline"),
    )
    return fig


def note(scenario: str) -> str:
    ok, n = verified_layers(scenario)
    check = (f'<span class="map-check ok">all {n} layer maps match their SHA-256 in the index</span>' if ok == n
             else f'<span class="map-check bad">{n - ok} of {n} layer maps do NOT match the index</span>')
    return (
        '<div class="map-note">'
        "<strong>3D space × time.</strong> One layer per visit, at its hour. "
        "<span class=\"c-cell\">Green</span>: points Cellpose-SAM counts as cell in the frame's cached map "
        f"(1/{PROBMAP_DOWNSAMPLE} resolution, drawn every {DRAW_STRIDE}th point). "
        "<span style=\"color:#3b82f6;font-weight:600\">Blue boxes</span>: the 3 FOV crops the visit's confluency "
        "came from; that number is Cellpose-SAM run on each crop, so it is not read off this picture. "
        "Hover the white markers for each visit's recorded numbers, quality gate and hashes. "
        "Nothing is drawn between visits."
        f'<div class="map-meta">Maps: the compute cache\'s own, copied by <code>scripts/export_replay_maps.py</code>; '
        f"{check}.</div></div>"
    )
