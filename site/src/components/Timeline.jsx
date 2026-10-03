import { useEffect, useMemo, useRef, useState } from "react";
import { Icon } from "./ui";
import { ScaleBar } from "./Stage";

/* Five held-out C2C12 flasks replayed as visits. Left: the Cellpose-SAM map
   at the selected visit and the three fields of view its number came from.
   Right: the per-visit mean with its noise band, the quality gate, the
   anomaly flag and the passage forecast. The visits play through once when
   the figure first comes into view; after that the row is yours. */

const TITLES = {
  normal_1: ["Normal flask A", ""],
  normal_2: ["Normal flask B", ""],
  contamination: ["Contamination", "simulated"],
  stall: ["Growth stall", "simulated"],
  dimming: ["Lamp dimming", "simulated"],
};

const W = 640;
const H = 300;
const M = { l: 40, r: 14, t: 16, b: 30 };

function Chart({ r, sel, setSel }) {
  const passes = r.visits.filter((v) => v.quality_pass);
  const f = r.forecast;
  const xmax = Math.ceil(Math.max(r.visits.at(-1).hours, f.interval ? f.interval[1] : 0, f.t_star || 0) / 12) * 12 + 2;
  const ymaxRaw = Math.max(...r.visits.flatMap((v) => [...v.fov, v.mean + v.se]), f.target || 0);
  const ymax = Math.min(100, Math.ceil((ymaxRaw + 8) / 20) * 20);
  const x = (h) => M.l + (h / xmax) * (W - M.l - M.r);
  const y = (p) => H - M.b - (p / ymax) * (H - M.t - M.b);
  const band =
    passes.map((v) => `${x(v.hours)},${y(v.mean + v.se)}`).join(" ") +
    " " +
    [...passes].reverse().map((v) => `${x(v.hours)},${y(Math.max(0, v.mean - v.se))}`).join(" ");
  const line = passes.map((v) => `${x(v.hours)},${y(v.mean)}`).join(" ");
  const curve = f.curve.length ? f.curve.map(([h, m]) => `${x(h)},${y(m)}`).join(" ") : "";
  const yTicks = [];
  for (let t = 0; t <= ymax; t += ymax > 60 ? 20 : 10) yTicks.push(t);
  const xTicks = [];
  for (let t = 0; t <= xmax; t += 12) xTicks.push(t);
  const cur = r.visits[sel];

  return (
    <svg viewBox={`0 0 ${W} ${H}`} role="img" aria-label={`Confluency per visit for ${TITLES[r.scenario][0]}, 0 to ${xmax} hours`}>
      <g className="grid">
        {yTicks.map((t) => (
          <line key={t} x1={M.l} x2={W - M.r} y1={y(t)} y2={y(t)} />
        ))}
      </g>
      <g className="axis">
        {yTicks.map((t) => (
          <text key={t} x={M.l - 8} y={y(t) + 3.5} textAnchor="end">
            {t}%
          </text>
        ))}
        {xTicks.map((t) => (
          <text key={t} x={x(t)} y={H - 10} textAnchor="middle">
            {t} h
          </text>
        ))}
        <line x1={M.l} x2={W - M.r} y1={H - M.b} y2={H - M.b} />
      </g>

      {f.interval ? (
        <rect x={x(f.interval[0])} y={M.t} width={x(f.interval[1]) - x(f.interval[0])} height={H - M.t - M.b} fill="rgba(44,199,218,0.10)" />
      ) : null}
      {f.target ? (
        <g>
          <line x1={M.l} x2={W - M.r} y1={y(f.target)} y2={y(f.target)} stroke="#6b7684" strokeDasharray="3 4" />
          <text x={W - M.r} y={y(f.target) - 6} textAnchor="end" fill="#86919d" fontFamily="var(--mono)" fontSize="11">
            passage target {f.target}%
          </text>
        </g>
      ) : null}
      {r.fault ? (
        <g>
          <line x1={x(r.fault.onset_hours)} x2={x(r.fault.onset_hours)} y1={M.t} y2={H - M.b} stroke="var(--anom)" strokeOpacity="0.7" strokeDasharray="2 3" />
          <text x={x(r.fault.onset_hours) - 5} y={M.t + 10} textAnchor="end" fill="var(--anom)" fontFamily="var(--mono)" fontSize="11">
            fault onset {r.fault.onset_hours} h
          </text>
        </g>
      ) : null}

      <polygon points={band} fill="rgba(44,199,218,0.18)" />
      {curve ? <polyline points={curve} fill="none" stroke="#9be7f0" strokeWidth="1.4" strokeDasharray="5 4" /> : null}
      {f.t_star && f.target ? <circle cx={x(f.t_star)} cy={y(f.target)} r="4" fill="none" stroke="#9be7f0" strokeWidth="1.6" /> : null}

      <line x1={x(cur.hours)} x2={x(cur.hours)} y1={M.t} y2={H - M.b} stroke="#e9ecf0" strokeOpacity="0.35" />

      {r.visits.map((v) =>
        v.fov.map((p, i) => <circle key={`${v.visit}-${i}`} cx={x(v.hours)} cy={y(p)} r="1.8" fill="#86919d" opacity="0.8" />),
      )}
      <polyline points={line} fill="none" stroke="var(--cell)" strokeWidth="1.8" />
      {r.visits.map((v) => (
        <g key={v.visit} onClick={() => setSel(v.visit)} style={{ cursor: "pointer" }}>
          {v.quality_pass ? (
            <circle cx={x(v.hours)} cy={y(v.mean)} r={v.visit === sel ? 5.5 : 3.8} fill="var(--cell)" stroke="#0a0c0f" strokeWidth="1.5" />
          ) : (
            <rect x={x(v.hours) - 4} y={y(v.mean) - 4} width="8" height="8" fill="none" stroke="var(--reimage-l)" strokeWidth="1.6" />
          )}
          {v.flag ? (
            <path d={`M${x(v.hours)} ${y(v.mean) - 15} l5 5 -5 5 -5 -5z`} fill="var(--anom)" />
          ) : null}
        </g>
      ))}
    </svg>
  );
}

function MapView({ r, v }) {
  const [h, w] = r.frame_hw;
  const mask = { WebkitMaskImage: `url(${v.map})`, maskImage: `url(${v.map})` };
  return (
    <div className="frame" data-prob="" style={{ aspectRatio: `${w} / ${h}` }}>
      <span className="letter on-stage on-frame">A</span>
      <div className="layer layer-prob" data-l="prob" style={mask} />
      <svg className="fovbox" viewBox={`0 0 ${w} ${h}`} preserveAspectRatio="none" style={{ position: "absolute", inset: 0, width: "100%", height: "100%" }} aria-hidden="true">
        {v.fov_boxes.map(([by, bx, bh, bw], i) => (
          <g key={i}>
            <rect x={bx} y={by} width={bw} height={bh} />
            <text x={bx + 12} y={by + 44}>
              {i + 1}
            </text>
          </g>
        ))}
      </svg>
      <ScaleBar umPerPx={r.um_per_px} widthPx={w} />
    </div>
  );
}

export default function Timeline({ replays }) {
  const [name, setName] = useState(replays[0].scenario);
  const r = useMemo(() => replays.find((x) => x.scenario === name), [replays, name]);
  const [sel, setSel] = useState(r.visits.length - 1);
  const played = useRef(false);
  const box = useRef(null);
  const timer = useRef(null);

  useEffect(() => {
    setSel(r.visits.length - 1);
  }, [r]);

  useEffect(() => {
    const el = box.current;
    if (!el || played.current) return;
    const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    const io = new IntersectionObserver(
      ([e]) => {
        if (!e.isIntersecting || played.current) return;
        played.current = true;
        io.disconnect();
        if (reduce) return;
        let i = 0;
        setSel(0);
        timer.current = setInterval(() => {
          i += 1;
          if (i >= r.visits.length) {
            clearInterval(timer.current);
            return;
          }
          setSel(i);
        }, 230);
      },
      { threshold: 0.45 },
    );
    io.observe(el);
    return () => {
      io.disconnect();
      clearInterval(timer.current);
    };
  }, [r]);

  const stop = () => clearInterval(timer.current);
  const v = r.visits[sel];
  const f = r.forecast;
  const madeAt = f.made_at_visit != null ? r.visits[f.made_at_visit] : null;
  const flagged = Boolean(madeAt && madeAt.flag);
  const uncal = !(r.profile && r.profile.calibrated);
  const made = f.status === "predicted" || f.status === "suppressed_fault";
  const held = made && (uncal || flagged);
  // Since rules_v0.5 an uncalibrated setup never passages on a reading alone; the flag is then additional.
  const heldNote = uncal ? (
    <>
      {" "}
      <b>
        <Icon name="human_review" /> Passage goes to a person:
      </b>{" "}
      this imaging setup has no calibration profile, so a passage at the target goes to human review
      {flagged ? `; the anomaly check also flagged visit ${f.made_at_visit + 1}, where this forecast was made` : ""}.
    </>
  ) : flagged ? (
    <>
      {" "}
      <b>
        <Icon name="human_review" /> Passage held:
      </b>{" "}
      the anomaly check flagged visit {f.made_at_visit + 1}, where this forecast was made, so a passage goes to human review.
    </>
  ) : null;
  const onKey = (e) => {
    if (e.key === "ArrowRight" || e.key === "ArrowLeft") {
      e.preventDefault();
      stop();
      setSel((s) => Math.max(0, Math.min(r.visits.length - 1, s + (e.key === "ArrowRight" ? 1 : -1))));
    }
  };

  return (
    <div className="stage" ref={box}>
      <div className="tabs" role="tablist" aria-label="Replayed flasks">
        {replays.map((x) => (
          <button
            key={x.scenario}
            type="button"
            role="tab"
            className="tab"
            aria-selected={x.scenario === name}
            onClick={() => {
              stop();
              setName(x.scenario);
            }}
          >
            {TITLES[x.scenario][0]}
            {TITLES[x.scenario][1] ? <small>{TITLES[x.scenario][1]}</small> : null}
          </button>
        ))}
      </div>

      <div className="tl-grid">
        <div className="tl-map">
          <MapView r={r} v={v} />
          <div className="tl-read">
            <div>
              <span>Visit</span>
              <b className="num">
                {v.visit + 1} · {v.hours.toFixed(1)} h
              </b>
            </div>
            <div>
              <span>Mean of {v.fov.length} fields ± SE</span>
              <b className="num">
                {v.mean.toFixed(1)} ± {v.se.toFixed(1)}%
              </b>
            </div>
            <div>
              <span>Fields 1 · 2 · 3</span>
              <b className="num">{v.fov.map((p) => p.toFixed(1)).join(" · ")}</b>
            </div>
            <div>
              <span>Quality gate</span>
              <b data-q={String(v.quality_pass)}>
                <Icon name={v.quality_pass ? "check" : "reimage"} /> {v.quality_pass ? "Pass" : "Re-image"}
              </b>
            </div>
            <div>
              <span>Anomaly score / threshold</span>
              <b className="num">
                {v.score.toFixed(3)} / {v.threshold.toFixed(3)}
              </b>
            </div>
            <div>
              <span>Anomaly flag</span>
              <b data-flag={String(v.flag)}>
                <Icon name={v.flag ? "flag" : "clear"} /> {v.flag ? "Flagged" : "Not flagged"}
              </b>
            </div>
          </div>
        </div>

        <div className="tl-chart">
          <div className="chart-head">
            <span className="letter on-stage">B</span>
            <span>Confluency per visit, 0–{Math.round(r.visits.at(-1).hours)} h</span>
          </div>
          <Chart r={r} sel={sel} setSel={(i) => (stop(), setSel(i))} />
          <div className="visits" role="group" aria-label="Visits; arrow keys step through them" onKeyDown={onKey}>
            {r.visits.map((x) => (
              <button
                key={x.visit}
                type="button"
                aria-pressed={x.visit === sel}
                data-q={String(x.quality_pass)}
                data-flag={String(x.flag)}
                aria-label={`Visit ${x.visit + 1}, ${x.hours.toFixed(1)} hours${x.quality_pass ? "" : ", re-image"}${x.flag ? ", flagged" : ""}`}
                onClick={() => (stop(), setSel(x.visit))}
              >
                {x.visit + 1}
              </button>
            ))}
          </div>
        </div>
      </div>

      <div className="tl-foot">
        <div>
          {f.status === "predicted" ? (
            <p className={held ? "held" : ""}>
              Passage forecast ({f.model} fit at visit {f.made_at_visit + 1}, {f.made_at_hours} h): the replays’ {f.target}% passage target at <span className="num">{f.t_star} h</span>, interval{" "}
              <span className="num">
                {f.interval[0]}–{f.interval[1]} h
              </span>
              . Backtest: median error {f.backtest.median_abs_error_h} h, interval covered {f.backtest.interval_covers} (n = {f.backtest.n_sequences} sequences).
              {heldNote}
            </p>
          ) : f.status === "suppressed_fault" ? (
            <p className={held ? "held" : ""}>
              Passage forecast not shown: the growth fit made at visit {f.made_at_visit + 1} ({f.made_at_hours} h), after the simulated fault’s onset, is {f.suppressed_reason}.
              {heldNote}
            </p>
          ) : (
            <p>No passage forecast: the fit starts once the flask passes {f.cut}%, and this one did not.</p>
          )}
          {r.notes.map((n) => (
            <p key={n} style={{ marginTop: 8 }}>
              {n}
            </p>
          ))}
          <p style={{ marginTop: 8, color: "var(--stage-ink-3)" }}>
            {r.banner}. {r.caption} {r.credit}
          </p>
        </div>
        <div className="key" aria-label="Key">
          <span>
            <i style={{ background: "var(--cell)", borderRadius: "50%" }} />
            mean of {r.visits[0].fov.length} fields
          </span>
          <span>
            <i style={{ background: "rgba(44,199,218,0.35)" }} />±1 SE noise band
          </span>
          <span>
            <i style={{ border: "1.6px solid var(--reimage-l)" }} />
            quality gate failed: re-image, left out of the trend
          </span>
          <span>
            <i style={{ background: "var(--anom)", transform: "rotate(45deg) scale(0.75)" }} />
            anomaly flag
          </span>
          <span>
            <i style={{ borderTop: "1.5px dashed #9be7f0", height: 0, marginTop: 6 }} />
            growth fit and forecast interval
          </span>
          <span>
            <Icon name="info" />
            left: cell probability at the visit, fields 1–3 boxed
          </span>
        </div>
      </div>
    </div>
  );
}
