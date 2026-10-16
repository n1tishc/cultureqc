import { useEffect, useMemo, useState } from "react";
import { Action, Icon, Linked, short } from "./ui";
import { DEFAULT_SCENARIO_ID, GUIDED_SCENARIOS, scenarioIdFromSearch, scenarioUrl } from "../lib/scenarios";
import "./GuidedStage.css";

const LAYERS = [
  ["prob", "Cell probability"],
  ["contour", "Cutoff contour"],
  ["band", "Cutoff edge"],
  ["anom", "Anomaly patches"],
];

const SHORT = {
  c2c12_normal_0_20: "C2C12, sparse",
  c2c12_normal_20_40: "C2C12, mid",
  c2c12_normal_40_100: "C2C12, densest",
  c2c12_contamination_real_size: "Real-size bacteria",
  c2c12_contamination_1: "Oversized bacteria",
  evican_pc3: "EVICAN PC3",
  evican_ht29: "EVICAN HT29",
};

/* The panel's heading. The stored labels name the anomaly bank's density
   group ("20-40% bin"), which is how the console and the records file them;
   here the normal frames are named for what they show. */
export const TITLE = {
  c2c12_normal_0_20: "C2C12, normal culture, sparse",
  c2c12_normal_20_40: "C2C12, normal culture, mid density",
  c2c12_normal_40_100: "C2C12, normal culture, the densest example",
};

const DEVICE = { mps: "Apple GPU, MPS", cuda: "GPU", cpu: "CPU" };

const contourCache = new Map();

function useContour(url, retry) {
  const [result, setResult] = useState(() => ({ url, data: contourCache.get(url) || null, error: false }));
  useEffect(() => {
    let live = true;
    if (contourCache.has(url)) {
      setResult({ url, data: contourCache.get(url), error: false });
      return;
    }
    setResult({ url, data: null, error: false });
    fetch(url)
      .then((response) => {
        if (!response.ok) throw new Error("Contour unavailable");
        return response.json();
      })
      .then((j) => {
        contourCache.set(url, j);
        if (live) setResult({ url, data: j, error: false });
      })
      .catch(() => {
        if (live) setResult({ url, data: null, error: true });
      });
    return () => {
      live = false;
    };
  }, [url, retry]);
  return result.url === url ? result : { url, data: contourCache.get(url) || null, error: false };
}

export function AnomalyLayer({ ex, nested = false }) {
  const a = ex.anomaly;
  const flat = a.patches.flat();
  const lo = Math.min(...flat);
  const top = new Set(a.top.map(([r, c]) => `${r},${c}`));
  const { x, y, size, patch } = a.crop;
  return (
    <svg
      className="overlay layer-anom"
      data-l="anom"
      viewBox={`0 0 ${ex.width} ${ex.height}`}
      preserveAspectRatio="none"
      aria-hidden="true"
      {...(nested ? { x: 0, y: 0, width: ex.width, height: ex.height } : {})}
    >
      <rect x={a.tile.x} y={a.tile.y} width={a.tile.size} height={a.tile.size} fill="none" stroke="var(--anom)" strokeWidth="1.2" strokeDasharray="5 4" vectorEffect="non-scaling-stroke" />
      {a.patches.map((row, r) =>
        row.map((dist, c) => {
          const t = Math.max(0, Math.min(1.25, (dist - lo) / (a.threshold - lo)));
          const isTop = top.has(`${r},${c}`);
          return (
            <rect
              key={`${r}-${c}`}
              x={x + c * patch}
              y={y + r * patch}
              width={patch}
              height={patch}
              fill="var(--anom)"
              fillOpacity={0.04 + 0.62 * Math.pow(t / 1.25, 1.4)}
              stroke={isTop ? "#fff" : "none"}
              strokeWidth={isTop ? 1.6 : 0}
              vectorEffect="non-scaling-stroke"
            />
          );
        }),
      )}
      <rect x={x} y={y} width={size} height={size} fill="none" stroke="var(--anom)" strokeWidth="1" strokeOpacity="0.5" vectorEffect="non-scaling-stroke" />
    </svg>
  );
}

export function ScaleBar({ umPerPx, widthPx, um = 200 }) {
  if (!umPerPx) return null;
  const w = (um / umPerPx / widthPx) * 100;
  return (
    <div className="scalebar" style={{ width: `${w}%` }} aria-hidden="true">
      <b />
      <span>{um} µm</span>
    </div>
  );
}

/* The reading's 90% error band from its setup's calibration profile, drawn on the
   0–100% scale with the reading and the passage target, and which rule it meets
   (culture/rules.py, rules_v0.5). A setup with no profile has no band. */
function ErrorBand({ c, target }) {
  const p = c.profile;
  const cut = p.cutoff === 0 ? "0" : `${p.cutoff > 0 ? "+" : "−"}${Math.abs(p.cutoff).toFixed(1)}`;
  if (!c.interval) {
    return (
      <div className="band-read">
        <p>
          Profile <b className="num">{p.id}</b>: no calibration for this microscope, so the reading has no error band
          {c.pct >= target ? " and a person decides at the target." : ", and a passage at the target goes to a person."}
        </p>
      </div>
    );
  }
  const [lo, hi] = c.interval;
  const verdict =
    lo < target && hi >= target
      ? "The band includes the target, so a person decides."
      : hi < target
        ? "The whole band is below the target."
        : "The whole band clears the target.";
  return (
    <div className="band-read">
      <div className="gauge" data-kind="range" aria-hidden="true">
        <i style={{ left: `${lo}%`, width: `${hi - lo}%` }} />
        <b style={{ left: `${c.pct}%` }} />
        <u style={{ left: `calc(${target}% - 1px)` }} />
      </div>
      <div className="gauge-legend">
        <span>
          90% band {lo.toFixed(1)}–{hi.toFixed(1)}%
        </span>
        <span>target {target.toFixed(0)}%</span>
      </div>
      <p>
        Profile <b className="num">{p.id}</b>: cutoff {cut}, band ±{p.band_pp} pp, measured on held-out labelled images. {verdict}
      </p>
    </div>
  );
}

function VerifyLine({ v, rec, total, error }) {
  const state = error ? "false" : v ? String(v.ok) : "pending";
  const text = error ? `Verification unavailable: ${error}` : !v ? "Re-hashing in this browser…" : v.ok ? "Re-hashed in your browser: matches" : "Re-hashed in your browser: no match";
  return (
    <>
      <span className="verified" data-ok={state}>
        <Icon name={error || (v && !v.ok) ? "cross" : "check"} />
        {text}
      </span>
      <p className="hash" title={rec.record_hash}>
        SHA-256 {short(rec.record_hash, 10)} · record {rec.index} of {total}
      </p>
    </>
  );
}

export default function Stage({ examples, verify, liveParity, verifyError }) {
  const items = useMemo(() => [...examples.items].sort((x, y) => x.record.index - y.record.index), [examples]);
  const ids = useMemo(() => items.map((item) => item.id), [items]);
  const [id, setId] = useState(() => typeof window === "undefined" ? DEFAULT_SCENARIO_ID : scenarioIdFromSearch(window.location.search, examples.items.map((item) => item.id)));
  const [layers, setLayers] = useState({ prob: false, contour: true, band: false, anom: false });
  const [mediaError, setMediaError] = useState(null);
  const [mediaRetry, setMediaRetry] = useState(0);
  const ex = useMemo(() => items.find((e) => e.id === id) || items.find((e) => e.id === DEFAULT_SCENARIO_ID) || items[0], [items, id]);
  const contourResult = useContour(ex.contour, mediaRetry);
  const contour = contourResult.data;
  const scenario = GUIDED_SCENARIOS.find((entry) => entry.id === ex.id);
  const step = GUIDED_SCENARIOS.findIndex((entry) => entry.id === ex.id);

  useEffect(() => {
    const onPopState = () => {
      setId(scenarioIdFromSearch(window.location.search, ids));
      setLayers({ prob: false, contour: true, band: false, anom: false });
      setMediaError(null);
      setMediaRetry(0);
    };
    window.addEventListener("popstate", onPopState);
    return () => window.removeEventListener("popstate", onPopState);
  }, [ids]);

  const selectScenario = (nextId) => {
    setLayers({ prob: false, contour: true, band: false, anom: false });
    setMediaError(null);
    setMediaRetry(0);
    if (nextId === ex.id) return;
    setId(nextId);
    window.history.pushState(null, "", scenarioUrl(window.location.href, nextId, ids));
  };

  const c = ex.confluency;
  const a = ex.anomaly;
  const v = verify ? verify[ex.record.index - 1] : null;
  const maskStyle = (url) => ({ WebkitMaskImage: `url(${url})`, maskImage: `url(${url})` });
  const frameAttrs = {};
  for (const [k] of LAYERS) if (layers[k]) frameAttrs[`data-${k}`] = "";

  return (
    <div className="stage guided-stage" aria-label="Guided walkthrough of stored decisions">
      <div className="guided-announcement" aria-live="polite" aria-atomic="true">{scenario?.title || ex.label}. Stored recommendation: {ex.action.replaceAll("_", " ")}. Confluency {c.pct.toFixed(2)} percent.</div>
      <nav className="guided-nav" aria-label="Decision scenarios">
        {GUIDED_SCENARIOS.map((entry, index) => (
          <button key={entry.id} type="button" aria-current={entry.id === ex.id ? "step" : undefined} onClick={() => selectScenario(entry.id)}>
            <span>{String(index + 1).padStart(2, "0")}</span>{entry.title}
          </button>
        ))}
      </nav>
      <div className="stage-grid">
        <div className="viewer">
          <div className="frame-box">
            <div
              className="frame stage-frame"
              style={{ aspectRatio: `${ex.width} / ${ex.height}`, "--ar": ex.width / ex.height }}
              {...frameAttrs}
            >
              <img key={`${ex.id}-${mediaRetry}`} src={mediaRetry ? `${ex.image}${ex.image.includes("?") ? "&" : "?"}retry=${mediaRetry}` : ex.image} width={ex.width} height={ex.height} alt={`${ex.label}: phase-contrast frame${ex.sequence ? `, ${ex.sequence} frame ${ex.frame}` : ""}`} onError={() => setMediaError(ex.id)} onLoad={() => setMediaError(null)} />
              <div className="layer layer-prob" data-l="prob" style={maskStyle(ex.prob)} />
              <div className="layer layer-band" data-l="band" style={maskStyle(ex.band)} />
              <svg className="overlay layer-contour" data-l="contour" viewBox={contour ? `0 0 ${contour.w} ${contour.h}` : "0 0 1 1"} preserveAspectRatio="none" aria-hidden="true">
                {contour ? <path d={contour.d} /> : null}
              </svg>
              <AnomalyLayer ex={ex} />
              <ScaleBar umPerPx={ex.um_per_px} widthPx={ex.width} />
            </div>
            {(mediaError === ex.id || contourResult.error) && <div className="guided-media-error" role="status"><span>{mediaError === ex.id ? "Stored image" : "Contour layer"} could not load.</span><button type="button" onClick={() => { setMediaError(null); setMediaRetry((attempt) => attempt + 1); }}>Retry media</button></div>}
          </div>
        </div>

        <div className="rail">
          <div className="rail-head">
            <h2>{scenario?.title || ex.label}</h2>
            <p>{scenario?.specimen || ex.label} · stored analysis · shipped baseline</p>
          </div>
          <div className="guided-result">
            <div className="guided-action"><span>Stored recommendation</span><Action a={ex.action} /></div>
            <p className="guided-reason">{ex.action_reason}</p>
            <p className="guided-scope">{scenario?.scope || "Additional stored research example. An anomaly flag describes a score on the centre tile; it does not diagnose contamination. This reading has not validated an automated culture action."} Setup calibration estimates measurement error; it does not validate the recommended action.</p>
          </div>
          <div className="guided-measure">
            <div className="guided-numbers"><strong>{c.pct.toFixed(2)}%</strong><span>confluency<br />target {ex.target.toFixed(0)}%</span></div>
            {c.interval ? <div className="guided-band"><span>Setup-level 90% error estimate</span><strong>{c.interval[0].toFixed(2)}–{c.interval[1].toFixed(2)}%</strong><ErrorBand c={c} target={ex.target} /></div> : <p className="guided-no-band">No calibrated error band for this setup. The reading alone cannot clear an action.</p>}
            {scenario?.note && <p className="guided-note">{scenario.note}</p>}
          </div>
          <div className="guided-record">
            <VerifyLine v={v} rec={ex.record} total={examples.chain_order.length} error={verifyError} />
            <a href={`/records?record=${encodeURIComponent(ex.id)}#chain`}>Inspect this exact record <Icon name="passage" /></a>
          </div>
        </div>
      </div>
      <div className="guided-controls">
        <button type="button" onClick={() => selectScenario(GUIDED_SCENARIOS[step - 1].id)} disabled={step <= 0}>Back</button>
        <span>{step < 0 ? "Additional example" : `${step + 1} of ${GUIDED_SCENARIOS.length}`}</span>
        <button type="button" onClick={() => selectScenario(DEFAULT_SCENARIO_ID)}>Reset</button>
        <button type="button" onClick={() => selectScenario(GUIDED_SCENARIOS[step < 0 ? 0 : step + 1].id)} disabled={step >= GUIDED_SCENARIOS.length - 1}>Next <Icon name="passage" /></button>
      </div>
      <details className="guided-advanced"><summary>Explore analysis layers and stored details</summary>
        <div className="toolbar" role="group" aria-label="Layers the pipeline computed">
          {LAYERS.map(([key, label]) => <button key={key} type="button" className="chip" data-layer={key} aria-pressed={layers[key]} onClick={() => setLayers((state) => ({ ...state, [key]: !state[key] }))}><i />{label}</button>)}
        </div>
        <div className="guided-advanced-body">
          <p>Layer toggles annotate the stored frame above. Cellpose-SAM uses cutoff {c.profile.cutoff}; {(c.borderline_fraction * 100).toFixed(1)}% of pixels are near it. The anomaly check reads only a {a.tile.size} px centre tile. DINOv2 score {a.score.toFixed(3)}; threshold {a.threshold.toFixed(3)}; {a.flag ? "flagged" : "not flagged"}. A flag does not identify a cause.</p>
          <p>Profile {c.profile.id} ({c.profile.status}) · rules {ex.rules} · {ex.credit}. Generated {ex.generated_at} on {DEVICE[ex.device] || ex.device}. <Linked>{liveParity}</Linked></p>
          <details><summary>All seven stored examples</summary><div className="guided-explorer">{items.map((item) => <button key={item.id} type="button" aria-pressed={item.id === ex.id} onClick={() => selectScenario(item.id)}><img src={item.thumb} alt="" width="52" height="39" loading="lazy" /><span>{SHORT[item.id] || item.label}<small>{item.confluency.pct.toFixed(1)}% · {item.action.replaceAll("_", " ")}</small></span></button>)}</div></details>
        </div>
      </details>
    </div>
  );
}
