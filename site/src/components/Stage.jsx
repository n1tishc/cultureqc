import { useEffect, useMemo, useState } from "react";
import { Action, Icon, Linked, short } from "./ui";
import { DEFAULT_SCENARIO_ID, EXAMPLE_CONTEXT, GUIDED_SCENARIOS, initialLayers, layersForView, layerView, scenarioSelectionFromSearch, scenarioUrl } from "../lib/scenarios";
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

function mediaUrl(url, retry) {
  return retry ? `${url}${url.includes("?") ? "&" : "?"}retry=${retry}` : url;
}

function useImageAsset(url, retry, enabled = true) {
  const source = mediaUrl(url, retry);
  const [result, setResult] = useState(null);
  useEffect(() => {
    if (!enabled) return undefined;
    let active = true;
    const asset = new Image();
    setResult({ source, status: "loading" });
    const finish = (status) => {
      clearTimeout(timeout);
      if (active) setResult({ source, status });
    };
    const timeout = setTimeout(() => finish("error"), 15000);
    asset.onload = () => finish("ready");
    asset.onerror = () => finish("error");
    asset.src = source;
    return () => {
      active = false;
      clearTimeout(timeout);
      asset.onload = null;
      asset.onerror = null;
    };
  }, [source, enabled]);
  return { source, status: !enabled ? "disabled" : result?.source === source ? result.status : "loading" };
}

function useContour(url, retry) {
  const [result, setResult] = useState(() => ({ url, data: contourCache.get(url) || null, error: false }));
  useEffect(() => {
    let live = true;
    if (contourCache.has(url)) {
      setResult({ url, data: contourCache.get(url), error: false });
      return;
    }
    setResult({ url, data: null, error: false });
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 15000);
    fetch(mediaUrl(url, retry), { signal: controller.signal })
      .then((response) => {
        if (!response.ok) throw new Error("Contour unavailable");
        return response.json();
      })
      .then((j) => {
        if (typeof j.d !== "string" || !(j.w > 0) || !(j.h > 0)) throw new Error("Invalid contour");
        contourCache.set(url, j);
        if (live) setResult({ url, data: j, error: false });
      })
      .catch(() => {
        if (live) setResult({ url, data: null, error: true });
      })
      .finally(() => clearTimeout(timeout));
    return () => {
      live = false;
      clearTimeout(timeout);
      controller.abort();
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
    <div className="scalebar" style={{ width: `${w}%` }} role="img" aria-label={`Scale bar: ${um} micrometres`}>
      <b aria-hidden="true" />
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
      <span className="verified" data-ok={state} role="status" aria-atomic="true">
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
  const [selection, setSelection] = useState(() => scenarioSelectionFromSearch(typeof window === "undefined" ? "" : window.location.search, ids));
  const [layers, setLayers] = useState(initialLayers);
  const [mediaRetry, setMediaRetry] = useState(0);
  const ex = useMemo(() => items.find((item) => item.id === selection.id) || items.find((item) => item.id === DEFAULT_SCENARIO_ID) || items[0], [items, selection.id]);
  const imageAsset = useImageAsset(ex.image, mediaRetry);
  const probabilityAsset = useImageAsset(ex.prob, mediaRetry, layers.prob);
  const bandAsset = useImageAsset(ex.band, mediaRetry, layers.band);
  const contourResult = useContour(ex.contour, mediaRetry);
  const contour = contourResult.data;
  const scenario = EXAMPLE_CONTEXT[ex.id];
  const view = layerView(layers);

  useEffect(() => {
    const onPopState = () => {
      setSelection(scenarioSelectionFromSearch(window.location.search, ids));
      setLayers(initialLayers());
      setMediaRetry((attempt) => attempt + 1);
    };
    window.addEventListener("popstate", onPopState);
    return () => window.removeEventListener("popstate", onPopState);
  }, [ids]);

  const selectScenario = (nextId) => {
    setLayers(initialLayers());
    setMediaRetry((attempt) => attempt + 1);
    setSelection({ id: nextId, invalid: false });
    if (nextId !== ex.id || selection.invalid) {
      window.history.pushState(null, "", scenarioUrl(window.location.href, nextId, ids));
    }
  };

  const c = ex.confluency;
  const a = ex.anomaly;
  const v = verify ? verify[ex.record.index - 1] : null;
  const maskStyle = (url) => ({ WebkitMaskImage: `url(${url})`, maskImage: `url(${url})` });
  const frameAttrs = {};
  const assets = [
    ["Stored image", imageAsset.status],
    ["Cell probability layer", probabilityAsset.status],
    ["Cutoff edge layer", bandAsset.status],
    ["Cutoff contour", !layers.contour ? "disabled" : contourResult.error ? "error" : contour ? "ready" : "loading"],
  ];
  const failedAssets = assets.filter(([, status]) => status === "error").map(([label]) => label);
  const loadingAssets = assets.filter(([, status]) => status === "loading").map(([label]) => label);
  const availableLayers = { prob: probabilityAsset.status === "ready", band: bandAsset.status === "ready", contour: !!contour, anom: true };
  for (const [key] of LAYERS) {
    if (imageAsset.status === "ready" && layers[key] && availableLayers[key]) frameAttrs[`data-${key}`] = "";
  }

  return (
    <div className="stage guided-stage" aria-label="Explore a stored analysis">
      <div className="guided-announcement" aria-live="polite" aria-atomic="true">{scenario?.title || ex.label}. Stored recommendation: {ex.action.replaceAll("_", " ")}. Confluency {c.pct.toFixed(2)} percent.</div>
      {selection.invalid && <p className="guided-selection-notice" role="status">That example is unavailable. Showing the coverage example instead. <button type="button" onClick={() => selectScenario(DEFAULT_SCENARIO_ID)}>Open coverage example</button></p>}
      <div className="stage-grid">
        <div className="viewer">
          <div className="frame-box">
            <div
              className="frame stage-frame"
              style={{ aspectRatio: `${ex.width} / ${ex.height}`, "--ar": ex.width / ex.height }}
              {...frameAttrs}
            >
              <img key={imageAsset.source} src={imageAsset.source} width={ex.width} height={ex.height} alt={`${ex.label}: phase-contrast frame${ex.sequence ? `, ${ex.sequence} frame ${ex.frame}` : ""}`} />
              <div className="layer layer-prob" data-l="prob" style={maskStyle(probabilityAsset.source)} />
              <div className="layer layer-band" data-l="band" style={maskStyle(bandAsset.source)} />
              <svg className="overlay layer-contour" data-l="contour" viewBox={contour ? `0 0 ${contour.w} ${contour.h}` : "0 0 1 1"} preserveAspectRatio="none" aria-hidden="true">
                {contour ? <path d={contour.d} /> : null}
              </svg>
              <AnomalyLayer ex={ex} />
              <ScaleBar umPerPx={ex.um_per_px} widthPx={ex.width} />
            </div>
            {failedAssets.length > 0 && <div className="guided-media-error" role="status"><span>Could not load: {failedAssets.join(", ")}. The selected stored result is unchanged.</span><button type="button" onClick={() => setMediaRetry((attempt) => attempt + 1)}>Retry media</button></div>}
            {loadingAssets.length > 0 && <p className="guided-media-status" role="status">Loading stored media: {loadingAssets.join(", ")}…</p>}
          </div>
          <div className="guided-view-controls">
            <div role="group" aria-label="Image view">
              <button type="button" aria-pressed={view === "raw"} onClick={() => setLayers(layersForView("raw"))}>Raw image</button>
              <button type="button" aria-pressed={view === "segmentation"} onClick={() => setLayers(layersForView("segmentation"))}>Segmentation</button>
            </div>
            <p aria-live="polite">{view === "custom" ? "Custom layers" : view === "raw" ? "Raw image · no overlays" : "Segmentation · cyan computed cutoff contour"}{view !== "raw" && failedAssets.length > 0 ? " · media unavailable" : ""}</p>
          </div>
        </div>

        <div className="rail">
          <div className="rail-head">
            <h2>{scenario?.title || ex.label}</h2>
            <p>{scenario?.specimen || ex.label} · Research demo · stored analysis</p>
          </div>
          <div className="guided-measure">
            <div className="guided-numbers"><strong>{c.pct.toFixed(2)}%</strong><span>confluency<br />target {ex.target.toFixed(0)}%</span></div>
            {c.interval ? <div className="guided-band"><span>Setup-level 90% error estimate</span><strong>{c.interval[0].toFixed(2)}–{c.interval[1].toFixed(2)}%</strong><ErrorBand c={c} target={ex.target} /></div> : <p className="guided-no-band">No calibrated error band for this example. The reading alone cannot clear an action.</p>}
          </div>
          <div className="guided-result">
            <div className="guided-action"><span>Stored recommendation</span><Action a={ex.action} /></div>
            <p className="guided-reason">{ex.action_reason}</p>
            <p className="guided-scope">{scenario?.scope || "Additional stored research example. An anomaly flag describes a score on the centre tile; it does not diagnose contamination. This reading has not validated an automated culture action."} Setup calibration estimates measurement error; it does not validate the recommended action.</p>
          </div>
          <div className="guided-record">
            <VerifyLine v={v} rec={ex.record} total={examples.chain_order.length} error={verifyError} />
            <a href={`/records?record=${encodeURIComponent(ex.id)}#chain`}>Inspect this exact record <Icon name="passage" /></a>
          </div>
        </div>
      </div>
      <nav className="guided-nav" aria-label="Analysis tasks">
        {GUIDED_SCENARIOS.map((entry) => (
          <button key={entry.id} type="button" aria-pressed={entry.id === ex.id} onClick={() => selectScenario(entry.id)}>{entry.title}</button>
        ))}
      </nav>
      <div className="guided-controls">
        <span>{GUIDED_SCENARIOS.some((entry) => entry.id === ex.id) ? "Explore either task" : "Additional stored example"}</span>
        <button type="button" onClick={() => selectScenario(DEFAULT_SCENARIO_ID)}>Reset</button>
      </div>
      <details className="guided-advanced guided-more"><summary>More examples <span>All {items.length} stored analyses</span></summary><div className="guided-explorer">{items.map((item) => <button key={item.id} type="button" aria-pressed={item.id === ex.id} onClick={() => selectScenario(item.id)}><img src={item.thumb} alt="" width="52" height="39" loading="lazy" /><span>{SHORT[item.id] || item.label}<small>{item.confluency.pct.toFixed(1)}% · {item.action.replaceAll("_", " ")}{item.id.includes("contamination") ? " · synthetic" : ""}</small></span></button>)}</div></details>
      <details className="guided-advanced"><summary>Explore analysis layers and stored details</summary>
        <div className="toolbar" role="group" aria-label="Layers the pipeline computed">
          {LAYERS.map(([key, label]) => <button key={key} type="button" className="chip" data-layer={key} aria-pressed={layers[key]} onClick={() => setLayers((state) => ({ ...state, [key]: !state[key] }))}><i />{label}</button>)}
        </div>
        <div className="guided-advanced-body">
          {scenario?.note && <p>{scenario.note}</p>}
          <p>Layer toggles annotate the stored frame above. Cellpose-SAM uses cutoff {c.profile.cutoff}; {(c.borderline_fraction * 100).toFixed(1)}% of pixels are near it. The anomaly check reads only a {a.tile.size} px centre tile. DINOv2 score {a.score.toFixed(3)}; threshold {a.threshold.toFixed(3)}; {a.flag ? "flagged" : "not flagged"}. A flag does not identify a cause.</p>
          <p>Profile {c.profile.id} ({c.profile.status}) · rules {ex.rules} · {ex.credit}. Generated {ex.generated_at} on {DEVICE[ex.device] || ex.device}. <Linked>{liveParity}</Linked></p>
        </div>
      </details>
    </div>
  );
}
