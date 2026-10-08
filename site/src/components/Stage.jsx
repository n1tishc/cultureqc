import { useEffect, useMemo, useState } from "react";
import { Action, Icon, actionGloss, actionWord, short } from "./ui";

/* The first viewport: one real frame, the layers the pipeline computed for it,
   and its stored readings. Hovering or focusing a reading lights the layer it
   was measured on; the record's hash is recomputed in this browser. */

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
const TITLE = {
  c2c12_normal_0_20: "C2C12, normal culture, sparse",
  c2c12_normal_20_40: "C2C12, normal culture, mid density",
  c2c12_normal_40_100: "C2C12, normal culture, the densest example",
};

const DEVICE = { mps: "Apple GPU, MPS", cuda: "GPU", cpu: "CPU" };

const contourCache = new Map();

function useContour(url) {
  const [d, setD] = useState(contourCache.get(url) || null);
  useEffect(() => {
    let live = true;
    if (contourCache.has(url)) {
      setD(contourCache.get(url));
      return;
    }
    setD(null);
    fetch(url)
      .then((r) => r.json())
      .then((j) => {
        contourCache.set(url, j);
        if (live) setD(j);
      })
      .catch(() => {});
    return () => {
      live = false;
    };
  }, [url]);
  return d;
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

function Gauge({ value, mark, max, kind, left, right }) {
  const w = Math.max(0, Math.min(1, value / max));
  const m = Math.max(0, Math.min(1, mark / max)) * 100;
  return (
    <>
      <div className="gauge" data-kind={kind} aria-hidden="true">
        <i style={{ transform: `scaleX(${w})` }} />
        <u style={{ left: `calc(${m}% - 1px)` }} />
      </div>
      <div className="gauge-legend">
        <span>{left}</span>
        <span>{right}</span>
      </div>
    </>
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

function Reading({ link, setSolo, children }) {
  const on = () => link && setSolo(link);
  const off = () => setSolo(null);
  return (
    <div
      className="reading"
      data-link={link || undefined}
      tabIndex={link ? 0 : undefined}
      onMouseEnter={on}
      onMouseLeave={off}
      onFocus={on}
      onBlur={off}
    >
      {children}
    </div>
  );
}

function VerifyLine({ v, rec, total }) {
  const state = v ? String(v.ok) : "pending";
  const text = !v ? "Re-hashing in this browser…" : v.ok ? "Re-hashed in your browser: matches" : "Re-hashed in your browser: no match";
  return (
    <>
      <span className="verified" data-ok={state}>
        <Icon name={v && !v.ok ? "cross" : "check"} />
        {text}
      </span>
      <p className="hash" title={rec.record_hash}>
        SHA-256 {short(rec.record_hash, 10)} · record {rec.index} of {total}
      </p>
    </>
  );
}

export default function Stage({ examples, verify, liveParity }) {
  // The strip follows the record chain's order; the panel opens on the first stored example.
  const items = useMemo(() => [...examples.items].sort((x, y) => x.record.index - y.record.index), [examples]);
  const [id, setId] = useState(examples.items[0].id);
  const [layers, setLayers] = useState({ prob: false, contour: true, band: false, anom: false });
  const [solo, setSolo] = useState(null);
  const ex = useMemo(() => items.find((e) => e.id === id), [items, id]);
  const contour = useContour(ex.contour);

  const c = ex.confluency;
  const a = ex.anomaly;
  const v = verify ? verify[ex.record.index - 1] : null;
  const anomMax = Math.max(a.threshold * 1.6, a.score * 1.12);
  const maskStyle = (url) => ({ WebkitMaskImage: `url(${url})`, maskImage: `url(${url})` });
  const frameAttrs = {};
  for (const [k] of LAYERS) if (layers[k]) frameAttrs[`data-${k}`] = "";
  if (solo) frameAttrs["data-solo"] = solo;

  return (
    <div className="stage" aria-label="A stored analysis, shown layer by layer">
      <div className="stage-grid">
        <div className="viewer">
          <div className="toolbar" role="group" aria-label="Layers the pipeline computed">
            <span className="letter on-stage">A</span>
            <span className="toolbar-label">Layers</span>
            {LAYERS.map(([k, label]) => (
              <button
                key={k}
                type="button"
                className="chip"
                data-layer={k}
                aria-pressed={layers[k]}
                onClick={() => setLayers((s) => ({ ...s, [k]: !s[k] }))}
              >
                <i />
                {label}
              </button>
            ))}
          </div>
          <div className="frame-box">
            <div
              className="frame"
              style={{ aspectRatio: `${ex.width} / ${ex.height}`, width: `min(100%, calc(max(300px, 100vh - 352px) * ${ex.width / ex.height}))` }}
              {...frameAttrs}
            >
              <img src={ex.image} width={ex.width} height={ex.height} alt={`${ex.label}: phase-contrast frame${ex.sequence ? `, ${ex.sequence} frame ${ex.frame}` : ""}`} />
              <div className="layer layer-prob" data-l="prob" style={maskStyle(ex.prob)} />
              <div className="layer layer-band" data-l="band" style={maskStyle(ex.band)} />
              <svg className="overlay layer-contour" data-l="contour" viewBox={contour ? `0 0 ${contour.w} ${contour.h}` : "0 0 1 1"} preserveAspectRatio="none" aria-hidden="true">
                {contour ? <path d={contour.d} /> : null}
              </svg>
              <AnomalyLayer ex={ex} />
              <ScaleBar umPerPx={ex.um_per_px} widthPx={ex.width} />
            </div>
          </div>
        </div>

        <div className="rail">
          <div className="rail-head">
            <h2>{TITLE[ex.id] || ex.label}</h2>
          </div>

          <Reading link="contour" setSolo={setSolo}>
            <div className="reading-top">
              <span>Confluency, above this setup’s cutoff</span>
              <span className="src">Cellpose-SAM</span>
            </div>
            <div className="big-row">
              <div className="big num">
                {c.pct.toFixed(1)}
                <small>%</small>
              </div>
              <p>
                target <b className="num">{ex.target.toFixed(0)}%</b>
                <br />
                the console’s default
              </p>
            </div>
            <ErrorBand c={c} target={ex.target} />
            <div
              className="sub"
              data-link="band"
              tabIndex={0}
              title={c.ambiguity_tooltip}
              onMouseEnter={() => setSolo("band")}
              onMouseLeave={() => setSolo("contour")}
              onFocus={() => setSolo("band")}
            >
              <p>
                <b className="num">{(c.borderline_fraction * 100).toFixed(1)}%</b> of pixels sit close to the cutoff, where a small change in it would flip them: the hatched “Cutoff edge” layer.
              </p>
            </div>
          </Reading>

          <Reading link="anom" setSolo={setSolo}>
            <div className="reading-top">
              <span>Anomaly check · DINOv2</span>
              <span className="flagword" data-flag={String(a.flag)}>
                <Icon name={a.flag ? "flag" : "clear"} />
                {a.flag ? "Flagged" : "Not flagged"}
              </span>
            </div>
            <Gauge value={a.score} mark={a.threshold} max={anomMax} kind="anom" left={`score ${a.score.toFixed(3)}`} right={`threshold ${a.threshold.toFixed(3)}`} />
            <p>
              Reads only the dashed {a.tile.size} px centre tile of the frame, against healthy frames at {a.bin.replace("-", "–")}% confluency; the score is set by its {a.top.length} outlined patches.
              {ex.kind === "evican" ? " The anomaly banks hold only C2C12 frames, so on other cell types the flag is uncalibrated." : null}
            </p>
          </Reading>

          <Reading>
            <div className="reading-top">
              <span>Recommended action</span>
              <span className="src">{ex.rules}</span>
            </div>
            <div className="action-row">
              <Action a={ex.action} />
              <span className="gloss">{actionGloss(ex.action)}</span>
            </div>
            <p>{ex.action_reason}</p>
          </Reading>

          <Reading>
            <div className="reading-top">
              <span>Record</span>
              <a className="src" href="#records">
                verify the chain <Icon name="down" />
              </a>
            </div>
            <VerifyLine v={v} rec={ex.record} total={examples.chain_order.length} />
          </Reading>
        </div>
      </div>

      <div className="strip" role="group" aria-label="Stored examples">
        {items.map((e) => (
          <button key={e.id} type="button" aria-pressed={e.id === id} onClick={() => setId(e.id)} title={e.label}>
            <img src={e.thumb} alt="" width="52" height="39" loading="lazy" />
            <span style={{ minWidth: 0 }}>
              <b>{SHORT[e.id] || e.label}</b>
              <small>
                {e.confluency.pct.toFixed(1)}% · {actionWord(e.action).toLowerCase()}
              </small>
            </span>
          </button>
        ))}
      </div>
      <div className="stage-note">
        <p>
          Hover a reading to light the layer it came from. {ex.label}. {ex.credit}.{ex.sequence ? ` Held-out ${ex.sequence}, frame ${ex.frame}.` : ""} Precomputed with the console’s own code ({DEVICE[ex.device] || ex.device}, {ex.generated_at}). {liveParity}
        </p>
      </div>
    </div>
  );
}
