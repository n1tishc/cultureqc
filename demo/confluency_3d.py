"""
demo/confluency_3d.py — the Analyze tab's 3D confluency view: the Cellpose-SAM
cell-probability map that the confluency number is counted from, drawn as a
surface over the image.

Height is the map's logit at each point, not cell thickness (phase contrast
does not measure height). Points above the cutoff plane (logit 0) are counted
as cell; points within ±band of it are the borderline pixels that lower the
confidence (culture/seg.py::cpsam_confluency). The map is the stored form
(culture.cache.downsample_probmap, 1/4 resolution), and its SHA-256 is the
record's confluency_map_hash, so the view can be checked against the audit
record. Every number in the note comes from the stored or live result.
"""

from __future__ import annotations

import html
import math

import numpy as np
import plotly.graph_objects as go

from culture.cache import PROBMAP_DOWNSAMPLE, probmap_sha256
from demo import viz3d

MAX_POINTS_PER_SIDE = 180          # drawn resolution cap; the hash covers the full stored map

# The opening camera per precomputed example (also used when the same image is
# analyzed live), chosen by eye so the first view reads without dragging; any
# other image gets DEFAULT_EYE. The page script turns the camera once around
# from here (demo/viz3d.py).
DEFAULT_EYE = dict(x=0.95, y=-1.05, z=0.7)
CAMERA_PRESETS: dict[str, dict] = {
    "c2c12_normal_0_20": dict(x=0.72, y=-0.82, z=0.52),      # close and low: separate cells stand out
    "c2c12_normal_20_40": dict(x=0.8, y=-0.9, z=0.55),
    "c2c12_normal_40_100": dict(x=0.82, y=-0.92, z=0.78),    # higher: the amber borderline shelf
    "c2c12_contamination_1": dict(x=0.85, y=-0.95, z=0.85),  # higher: the near-uniform carpet
    "c2c12_contamination_real_size": dict(x=0.72, y=-0.82, z=0.52),  # sparse, like the 0-20% frame
    "evican_pc3": dict(x=0.7, y=-0.8, z=0.5),                # few cells: come close
    "evican_ht29": dict(x=0.75, y=-0.85, z=0.58),
}

CELL = "#22c55e"                   # the overlay's cell green
BORDER = "#f59e0b"
BACKGROUND = "#334155"


def _classes(logit: np.ndarray, thr: float, band: float) -> np.ndarray:
    """0 background, 1 borderline, 2 cell (borderline wins near the cutoff)."""
    c = np.where(logit > thr, 2, 0)
    c[np.abs(logit - thr) < band] = 1
    return c


def landscape_figure(prob_x1000: np.ndarray, thr: float = 0.0, band: float = 1.0,
                     example_id: str | None = None) -> go.Figure:
    h, w = prob_x1000.shape
    stride = max(1, math.ceil(max(h, w) / MAX_POINTS_PER_SIDE))
    logit = prob_x1000[::stride, ::stride].astype(np.float32) / 1000.0
    ys = np.arange(0, h, stride)[: logit.shape[0]] * PROBMAP_DOWNSAMPLE
    xs = np.arange(0, w, stride)[: logit.shape[1]] * PROBMAP_DOWNSAMPLE
    cls = _classes(logit, thr, band)
    names = np.array(["background", "borderline", "cell"])[cls]

    surface = go.Surface(
        x=xs, y=ys, z=logit, surfacecolor=cls, cmin=0, cmax=2,
        colorscale=[[0, BACKGROUND], [0.33, BACKGROUND], [0.34, BORDER], [0.66, BORDER], [0.67, CELL], [1, CELL]],
        showscale=False, customdata=names,
        hovertemplate="x %{x} px, y %{y} px<br>logit %{z:.2f}<br>%{customdata}<extra></extra>",
        lighting=dict(ambient=0.55, diffuse=0.8, roughness=0.6, specular=0.15),
        name="cell-probability logit",
    )
    plane = go.Surface(
        x=[xs[0], xs[-1]], y=[ys[0], ys[-1]], z=[[thr, thr], [thr, thr]],
        colorscale=[[0, "#e2e8f0"], [1, "#e2e8f0"]], showscale=False, opacity=0.18,
        hoverinfo="skip", name="cutoff",
    )
    axis = dict(showbackground=False, gridcolor="rgba(148,163,184,0.18)", zerolinecolor="rgba(148,163,184,0.3)",
                color="#94a3b8", title_font=dict(size=11), tickfont=dict(size=10))
    fig = go.Figure([surface, plane])
    fig.update_layout(
        scene=dict(
            xaxis=dict(axis, title="x (px)"),
            yaxis=dict(axis, title="y (px)", autorange="reversed"),
            zaxis=dict(axis, title="logit (not height)"),
            aspectmode="manual", aspectratio=dict(x=1.0, y=h / w, z=0.4),
            camera=dict(eye=CAMERA_PRESETS.get(example_id, DEFAULT_EYE)),
        ),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#cbd5e1"), margin=dict(l=0, r=0, t=0, b=0), height=380, showlegend=False,
        meta=viz3d.meta("landscape"),
    )
    return fig


def landscape_note(prob_x1000: np.ndarray, confluency: dict, record_map_hash: str | None,
                   precomputed: bool) -> str:
    """The explanation under the surface. `confluency` is ConfluencyResult.to_dict()."""
    extra = confluency.get("extra") or {}
    thr, band = extra.get("cellprob_threshold", 0.0), extra.get("confidence_band", 1.0)
    bf = extra.get("borderline_fraction")
    h, w = prob_x1000.shape
    stride = max(1, math.ceil(max(h, w) / MAX_POINTS_PER_SIDE))
    digest = probmap_sha256(prob_x1000)
    if record_map_hash is None:
        check = '<span class="map-check bad">the record has no map hash</span>'
    elif digest == record_map_hash:
        check = '<span class="map-check ok">matches the record\'s <code>confluency_map_hash</code></span>'
    else:
        check = '<span class="map-check bad">does NOT match the record\'s <code>confluency_map_hash</code></span>'
    kept = ("stored with the example" if precomputed
            else "held in memory for this view only; the record keeps its hash")
    conf_line = ""
    if bf is not None:
        conf_line = (f" <span class=\"c-border\">Amber</span>: within ±{band:g} of the cutoff, "
                     f"{bf * 100:.2f}% of pixels, so confidence = 1 − 4 × {bf:.4f} = "
                     f"<strong>{confluency['confidence']:.3f}</strong>.")
    return (
        '<div class="map-note">'
        "<strong>3D confluency view.</strong> Height is Cellpose-SAM's cell-probability logit at each point, "
        "<em>not</em> cell thickness: phase contrast does not measure height. "
        f"<span class=\"c-cell\">Green</span>, above the cutoff plane (logit {thr:g}): counted as cell; "
        f"confluency <strong>{confluency['pct']:.2f}%</strong> is that share of the full-resolution map."
        f"{conf_line} <span class=\"c-bg\">Slate</span>: background."
        f'<div class="map-meta">Map: 1/{PROBMAP_DOWNSAMPLE} resolution, {h}×{w}, drawn every '
        f"{stride} point{'s' if stride > 1 else ''}; {html.escape(kept)}. SHA-256 "
        f"<code>{digest[:16]}…</code> {check}.</div>"
        "</div>"
    )
