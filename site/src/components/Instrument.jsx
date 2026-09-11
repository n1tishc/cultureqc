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
  return (
    <section
      className="instrument"
      aria-label={
        demo ? "Interactive Huh7 pipeline" : `Live analysis of ${name}`
      }
    >
      <header className="instrument-head">
        <div>
          <p className="eyebrow">
            {demo
              ? "RECORDED RUN / INTERACTIVE PLAYBACK"
              : "LIVE SERVER PIPELINE"}
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
              <small>{i <= current ? "Available" : "Waiting"}</small>
            </button>
          </li>
        ))}
      </ol>
      <div className="instrument-body">
        <div className="instrument-image">
          {visuals.raw ? (
            <img
              className="raw-field"
              src={visuals.raw}
              alt="Brightfield microscopy source field"
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
          {shown === 1 && visuals.probability && (
            <img
              className="evidence-layer"
              src={visuals.probability}
              alt="Cellpose cell score mapped through sigmoid, uncalibrated"
            />
          )}
          {shown >= 2 && layers.mask && visuals.mask && (
            <img
              className="evidence-layer mask-reveal"
              src={visuals.mask}
              alt="Foreground segmentation overlay"
            />
          )}
          {shown >= 2 && layers.contour && visuals.contour && (
            <img
              className="evidence-layer"
              src={visuals.contour}
              alt="Boundary of segmented foreground"
            />
          )}
          {shown >= 3 && layers.heatmap && visuals.heatmap && (
            <img
              className="evidence-layer cam-reveal"
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
            <span className="eyebrow">QC VERDICT</span>
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
      <p className="eyebrow">RESEARCH NOTEBOOK / NEGATIVE RESULTS</p>
      <h2>What didn’t work.</h2>
      <p>The discarded approaches matter as much as the final pipeline.</p>
      <div className="negative-grid">
        <article>
          <span>01 / VLM RATIONALE</span>
          <h3>Keep explanations grounded.</h3>
          <p>
            The deployed pipeline disables VLM generation and uses templates
            grounded in model outputs. The VLM failure experiment is referenced,
            but its evaluation numbers are not available in this checkout.
          </p>
          <strong>Failure rate: not reported</strong>
          <a href="https://github.com/n1tishc/cultureqc/blob/main/culture/pipeline.py">
            Inspect the deployed decision →
          </a>
        </article>
        <article>
          <span>02 / FINE-TUNING</span>
          <h3>A plateau is still a result.</h3>
          <p>
            Fine-tuning is documented as a negative result in the audit mapping.
            Its training curve and before/after metrics are not included here;
            the deployed segmentation model remains zero-shot.
          </p>
          <strong>Plateau metric: not reported</strong>
          <a href="https://github.com/n1tishc/cultureqc/blob/main/docs/audit_mapping.md">
            Read the research record →
          </a>
        </article>
      </div>
    </section>
  );
}
