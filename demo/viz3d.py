"""
demo/viz3d.py — motion for the console's two 3D views, as one page script.

When a 3D figure appears (Analyze → 3D, Flask Timeline → 3D), the script
  - turns the camera once around the scene, slowly, and stops where it
    started (the figure's preset angle); any click, drag, wheel or touch on
    the plot stops it at once;
  - on the timeline, builds the stack up visit by visit (traces tagged
    meta={"hours": ...} by demo/replay_3d.py), in time order. A click on the
    plot or its legend finishes the build-up (everything shown) first.
Nothing moves when the viewer's system asks for reduced motion, and a figure
is always complete as drawn: without the script, or once it finishes, every
trace is visible. Only the camera and trace visibility change, never data.

Each figure carries layout.meta = meta(kind) with a fresh nonce, so reopening
the same view starts the motion again. Uses the page's global Plotly (the one
Gradio's plot component loads). HEAD (a <script> running JS) is passed to
launch(head=...) by console.py and demo/app.py: Gradio 6.26 did not run
launch(js=...) in a local check. window.__cqc3d is set once it runs.
"""

from __future__ import annotations

import uuid

ROTATE_S = {"landscape": 26, "timeline": 32}   # one full turn
BUILD_STEP_MS = 420                             # between visits in the timeline build-up


def meta(kind: str) -> dict:
    return {"cqc3d": kind, "nonce": uuid.uuid4().hex, "rotate_s": ROTATE_S[kind],
            "build_step_ms": BUILD_STEP_MS if kind == "timeline" else 0}


JS = r"""
() => {
  if (window.__cqc3d) return;
  window.__cqc3d = true;
  const reduced = () => window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  const runs = new WeakMap();

  // All relayout/restyle calls on one plot go through one queue.
  const enqueue = (run, fn) => (run.q = run.q.then(() => (run.dead ? null : fn())).catch(() => null));
  const visible = (gd) => gd.isConnected && gd.offsetParent !== null && !document.hidden;

  function finishBuild(gd, run) {
    if (!run.hidden || !run.hidden.length) return;
    const idx = run.hidden;
    run.hidden = [];
    run.buildDone = true;
    enqueue(run, () => Plotly.restyle(gd, { visible: true }, idx));
  }

  function stop(gd, run) {
    if (run.stopped) return;
    run.stopped = true;
    finishBuild(gd, run);
  }

  function rotate(gd, run, seconds) {
    const cam = (gd.layout.scene && gd.layout.scene.camera && gd.layout.scene.camera.eye) || { x: 1.25, y: -1.25, z: 0.6 };
    const r = Math.hypot(cam.x, cam.y), th0 = Math.atan2(cam.y, cam.x), z = cam.z;
    const eye = (f) => {
      const e = f < 0.5 ? 2 * f * f : 1 - Math.pow(-2 * f + 2, 2) / 2;      // ease in-out
      const th = th0 + 2 * Math.PI * e;
      return { "scene.camera.eye": { x: r * Math.cos(th), y: r * Math.sin(th), z } };
    };
    let t0 = null, busy = false;
    const step = (ts) => {
      if (run.stopped || run.dead) return;
      if (!visible(gd)) { run.stopped = true; return; }
      if (t0 === null) t0 = ts;
      const f = Math.min(1, (ts - t0) / (seconds * 1000));
      if (f >= 1) { enqueue(run, () => Plotly.relayout(gd, eye(1))); run.stopped = true; return; }
      if (!busy) { busy = true; enqueue(run, () => Plotly.relayout(gd, eye(f))).then(() => { busy = false; }); }
      requestAnimationFrame(step);
    };
    requestAnimationFrame(step);
  }

  function build(gd, run, stepMs) {
    const hours = [];
    gd.data.forEach((t, i) => { if (t.meta && typeof t.meta.hours === "number") hours.push([t.meta.hours, i]); });
    if (!hours.length) return;
    run.hidden = hours.map((h) => h[1]);
    enqueue(run, () => Plotly.restyle(gd, { visible: false }, run.hidden.slice()));
    const times = [...new Set(hours.map((h) => h[0]))].sort((a, b) => a - b);
    let k = 0;
    const next = () => {
      if (run.dead || run.buildDone) return;
      if (k >= times.length) { run.hidden = []; run.buildDone = true; return; }
      const t = times[k++];
      const idx = hours.filter((h) => h[0] === t).map((h) => h[1]);
      run.hidden = run.hidden.filter((i) => !idx.includes(i));
      enqueue(run, () => Plotly.restyle(gd, { visible: true }, idx));
      setTimeout(next, stepMs);
    };
    setTimeout(next, 300);
    // A handler from an earlier render of the same plot has no say (undefined).
    gd.on && gd.on("plotly_legendclick", () => {
      if (run.dead || run.buildDone) return undefined;
      finishBuild(gd, run);              // show everything first; the next legend click toggles
      return false;
    });
  }

  function begin(gd, meta) {
    const old = runs.get(gd);
    if (old) old.dead = true;
    const run = { nonce: meta.nonce, q: Promise.resolve(), stopped: false, dead: false, hidden: [], buildDone: false };
    runs.set(gd, run);
    window.__cqc3dRuns = (window.__cqc3dRuns || 0) + 1;
    if (reduced()) return;
    const halt = () => stop(gd, run);
    ["pointerdown", "wheel", "touchstart"].forEach((ev) => gd.addEventListener(ev, halt, { capture: true, once: true, passive: true }));
    if (meta.build_step_ms) build(gd, run, meta.build_step_ms);
    rotate(gd, run, meta.rotate_s);
  }

  setInterval(() => {
    if (typeof Plotly === "undefined") return;
    document.querySelectorAll(".js-plotly-plot").forEach((gd) => {
      const meta = gd.layout && gd.layout.meta;
      if (!meta || !meta.cqc3d || !gd._fullLayout || !visible(gd)) return;
      const run = runs.get(gd);
      if (run && run.nonce === meta.nonce) return;
      begin(gd, meta);
    });
  }, 120);
}
"""


HEAD = f"<script>({JS.strip()})();</script>"
