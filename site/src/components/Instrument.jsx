import { useEffect, useState } from "react";
import Counter from "./Counter";
import { RM } from "../lib/motion";
import { sha256, canonJSON } from "../lib/hash";

const stages = [
  "Raw field",
  "Cell probability",
  "Segmentation",
  "Grad-CAM",
  "QC verdict",
];
export function RecordLink({ record, canonical }) {
  const [verification, setVerification] = useState("");
  useEffect(() => setVerification(""), [record]);
  async function verify() {
    try {
      const { record_hash, ...body } = record;
      const match =
        canonical &&
        (await sha256(canonical)) === record_hash &&
        canonJSON(JSON.parse(canonical)) === canonJSON(body);
      setVerification(
        match
          ? "Record digest verified in this browser"
          : "Record cannot be verified: missing canonical bytes or digest mismatch",
      );
    } catch {
      setVerification("Record verification failed");
    }
  }
  if (!record) return null;
  return (
    <div className="instrument-log">
      <div>
        <span className="eyebrow">INSTRUMENT LOG / SHA-256</span>
        <a href="#/audit">Verify sample chain →</a>
      </div>
      <div className="hash-link">
        <code>
          <small>PREVIOUS RECORD</small>
          {record.prev_record_hash}
          {/^0+$/.test(record.prev_record_hash) && (
            <em className="genesis-note">
              Genesis record — no predecessor
            </em>
          )}
        </code>
        <span aria-hidden="true">→</span>
        <code>
          <small>THIS RECORD</small>
          {record.record_hash}
        </code>
      </div>
      <p>
        Recorded {record.analysed_at || record.captured_at} ·{" "}
        {record.model_versions?.seg} + {record.model_versions?.qc}
      </p>
      <button type="button" className="button secondary" onClick={verify}>
        Verify this record
      </button>
      <p role="status">{verification}</p>
      <details>
        <summary>Inspect full analysis record</summary>
        <pre>{JSON.stringify(record, null, 2)}</pre>
      </details>
      <small>
        Tamper-evident research record. Hosted logs reset on restart; this is
        not a validated GMP system.
      </small>
    </div>
  );
}
export default function Instrument({
  result,
  event,
  name = "Huh7 · synthetic contamination challenge",
  demo = false,
  error,
}) {
  const [demoResult, setDemoResult] = useState(null);
  const [loadError, setLoadError] = useState("");
  const [stage, setStage] = useState(4);
  const [playing, setPlaying] = useState(false);
  const [elapsed, setElapsed] = useState(0);
  const [layers, setLayers] = useState({
    mask: true,
    heatmap: true,
    contour: false,
  });
  const [rawDims, setRawDims] = useState(null);
  useEffect(() => {
    if (!demo) return;
    const ctl = new AbortController();
    fetch("/instrument/demo.json", { signal: ctl.signal })
      .then((r) => {
        if (!r.ok) throw Error("Demo could not load. Reload to retry.");
        return r.json();
      })
      .then(setDemoResult)
      .catch((e) => {
        if (e.name !== "AbortError") setLoadError(e.message);
      });
    return () => ctl.abort();
  }, [demo]);
  useEffect(() => {
    if (!playing) return;
    if (RM.matches || stage >= 4) {
      setStage(4);
      setPlaying(false);
      return;
    }
    const t = setTimeout(() => setStage((s) => s + 1), 1100);
    return () => clearTimeout(t);
  }, [playing, stage]);
  const data = demo ? demoResult : result;
  const visuals = data?.visuals || event?.visuals || {};
  const current = demo
    ? demoResult
      ? stage
      : 0
    : data
      ? 4
      : visuals.heatmap
        ? 3
        : visuals.mask
          ? 2
          : 0;
  const [inspect, setInspect] = useState(null);
  useEffect(() => setInspect(null), [current, name]);
  const shown = inspect ?? current;
  const pct = data?.confluency_pct ?? event?.confluency_pct;
  const record = data?.record;
  const issue = error || loadError;
  const busy = !demo && !data && !issue;
  useEffect(() => {
    if (!busy) return;
    setElapsed(0);
    const start = Date.now();
    const timer = setInterval(
      () => setElapsed(Math.floor((Date.now() - start) / 1000)),
      1000,
    );
    return () => clearInterval(timer);
  }, [busy, name]);
  /* One-line result for the active step, derived from the run's own data so
     it never states a number a visitor's real upload didn't produce. */
  const stepSummary = (i) => {
    if (i !== shown) return i <= current ? "Available" : "Waiting";
    switch (i) {
      case 0:
        return rawDims ? `${rawDims.w} × ${rawDims.h} px` : "Available";
      case 1:
        return visuals.probability ? "Probability map rendered" : "Available";
      case 2:
        return pct != null ? `${pct.toFixed(1)}% confluency` : "Available";
      case 3:
        return visuals.heatmap ? "Evidence region detected" : "Available";
      case 4:
        return record
          ? record.qc_flag.replaceAll("_", " ").replace(/^./, (c) => c.toUpperCase())
          : "Available";
      default:
        return "Available";
    }
  };
  return (
    <section
      className="instrument"
      aria-label={
        demo ? "Interactive Huh7 pipeline" : `Live analysis of ${name}`
      }
    >
      <header className="instrument-head">
        <div>
          <p className="kicker">
            {demo ? "Recorded run · interactive playback" : "Live server pipeline"}
          </p>
          <h2>{name}</h2>
        </div>
        <span className="instrument-status" role="status">
          {issue
            ? "Run interrupted"
            : demo
              ? playing
                ? "Playing recorded stages"
                : data
                  ? "Ready to explore"
                  : "Loading recorded run"
              : data
                ? "Analysis complete"
                : event?.stage === "queued"
                  ? "Queued · waiting for instrument"
                  : event?.stage === "qc"
                    ? "Computing QC evidence"
                    : "Computing cell segmentation"}
        </span>
      </header>
      <ol className="pipeline-stages">
        {stages.map((label, i) => (
          <li key={label}>
            <button
              type="button"
              disabled={i > current}
              aria-pressed={shown === i}
              onClick={() => {
                setInspect(i);
                setPlaying(false);
              }}
            >
              <span>{String(i + 1).padStart(2, "0")}</span>
              {label}
              <small>{stepSummary(i)}</small>
            </button>
          </li>
        ))}
      </ol>
      <div className="instrument-body">
        <div className="instrument-image">
          {visuals.raw ? (
            <img
              key={name}
              className="raw-field layer-land"
              src={visuals.raw}
              alt="Brightfield microscopy source field"
              onLoad={(e) =>
                setRawDims({
                  w: e.target.naturalWidth,
                  h: e.target.naturalHeight,
                })
              }
            />
          ) : (
            <div className="instrument-empty">
              {issue || "Image received. Waiting for model output…"}
              <small>
                CPU inference can take a minute or longer. Results appear as
                each stage finishes.
              </small>
            </div>
          )}
          {/* Every layer that has a source stays mounted once it arrives, so
              switching steps crossfades opacity instead of popping the image
              in and out. None of these carry layer-land/cam-reveal — those
              animate opacity with fill-mode "both", which pins the property
              and permanently overrides the inline style driving the fade. */}
          {visuals.probability && (
            <img
              className="evidence-layer"
              style={{ opacity: shown === 1 ? 1 : 0 }}
              src={visuals.probability}
              alt="Cellpose cell score mapped through sigmoid, uncalibrated"
            />
          )}
          {layers.mask && visuals.mask && (
            <img
              className="evidence-layer mask-reveal"
              style={{ opacity: shown >= 2 ? 1 : 0 }}
              src={visuals.mask}
              alt="Foreground segmentation overlay"
            />
          )}
          {layers.contour && visuals.contour && (
            <img
              className="evidence-layer"
              style={{ opacity: shown >= 2 ? 1 : 0 }}
              src={visuals.contour}
              alt="Boundary of segmented foreground"
            />
          )}
          {layers.heatmap && visuals.heatmap && (
            <img
              className="evidence-layer"
              style={{ opacity: shown >= 3 ? 1 : 0 }}
              src={visuals.heatmap}
              alt="Grad-CAM activation within the classifier crop"
            />
          )}
          <span className="image-caption">
            {stages[shown]} /{" "}
            {demo
              ? "precomputed model outputs"
              : busy
                ? "receiving model outputs"
                : "model outputs"}
          </span>
        </div>
        <aside className="instrument-readout">
          <p className="eyebrow">FIELD COVERAGE</p>
          <div className="confluency-readout">
            {current >= 2 && pct != null ? (
              <>
                <Counter to={pct} runKey={name} />
                <span>%</span>
              </>
            ) : (
              <span>—</span>
            )}
          </div>
          <p>Confluency · foreground area</p>
          {busy && (
            <p className="elapsed-readout">
              Elapsed {elapsed}s · no estimated percentage
            </p>
          )}
          <fieldset>
            <legend>Evidence layers</legend>
            {[
              ["mask", "Segmentation mask", 2],
              ["heatmap", "Grad-CAM heatmap", 3],
              ["contour", "Confluency contour", 2],
            ].map(([key, label, min]) => (
              <label key={key}>
                <input
                  type="checkbox"
                  checked={layers[key]}
                  disabled={current < min || !visuals[key]}
                  onChange={(e) =>
                    setLayers((l) => ({ ...l, [key]: e.target.checked }))
                  }
                />
                {label}
              </label>
            ))}
          </fieldset>
          {current >= 3 && !visuals.heatmap && (
            <p>Grad-CAM heatmap unavailable for this run.</p>
          )}
          <div className="verdict">
            <span className="kicker">QC verdict</span>
            <strong>
              {current === 4 && record
                ? record.qc_flag.replaceAll("_", " ")
                : "Awaiting final record"}
            </strong>
            {current === 4 && record && <p>{record.qc_rationale}</p>}
          </div>
          {demo && (
            <button
              className="button primary"
              disabled={!data}
              onClick={() => {
                setInspect(null);
                setStage(playing ? 4 : 0);
                setPlaying(!playing);
              }}
            >
              {playing ? "Skip to results" : "Replay pipeline"}
            </button>
          )}
        </aside>
      </div>
      {issue && (
        <p role="alert">
          {issue} Retry the image using the upload controls below, or{" "}
          <a href="#/demo">explore the demo dataset</a> instead.
        </p>
      )}
      <p className="instrument-note">
        Cell probability: sigmoid of raw Cellpose score, not calibrated
        confidence. Green: segmented foreground. Amber: Grad-CAM activation, not
        object detections. QC uses the central 256 × 256 pixels, or resizes
        smaller images.
      </p>
      {current === 4 && (
        <RecordLink record={record} canonical={data?.record_canonical} />
      )}
    </section>
  );
}
export function NegativeResults() {
  return (
    <section className="negative-results">
      <h2>What didn’t work.</h2>
      <p>The discarded approaches matter as much as the final pipeline.</p>
      <div className="negative-grid">
        <article>
          <span>01 / VLM RATIONALE</span>
          <h3>Keep explanations grounded.</h3>
          <p>
            Qwen3-VL-8B-Instruct scored 29% on zero-shot tile classification —
            near the 25% random baseline. Strong normal-class bias;
            near-identical rationales across all classes. The deployed
            pipeline uses deterministic templates grounded in model outputs
            instead.
          </p>
          <strong>Accuracy: 29% (4-class random baseline: 25%)</strong>
          <a href="https://github.com/n1tishc/cultureqc/blob/main/culture/pipeline.py">
            Inspect the deployed decision →
          </a>
        </article>
        <article>
          <span>02 / FINE-TUNING</span>
          <h3>A plateau is still a result.</h3>
          <p>
            Cellpose-SAM fine-tuning on LIVECell showed no improvement over 60
            epochs — the dataset is likely in the pretraining corpus. The
            deployed segmentation model remains zero-shot.
          </p>
          <strong>Loss: flat across 60 epochs</strong>
          <a href="https://github.com/n1tishc/cultureqc/blob/main/docs/audit_mapping.md">
            Read the research record →
          </a>
        </article>
      </div>
    </section>
  );
}
