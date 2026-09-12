import Instrument from "./Instrument";
import { Icon } from "./Workspace";
import { useRef, useState } from "react";
import {
  ANALYSIS_API,
  LOCAL_TOOLING,
  DEFAULT_ENDPOINT,
  CAN_ANALYSE,
  MAX_FILES,
} from "../config";
import {
  ACTION_LABEL,
  FLAG_SHORT,
  FLAG_TONE,
  fmtBytes,
  pad2,
} from "../lib/labels";

const PHASE_STEP = { collect: 0, processing: 1, results: 2 };

export default function Upload({ workspace }) {
  const {
    files,
    live,
    setLive,
    error,
    prog,
    analysing,
    phase,
    analysingHash,
    endpoint,
    epField,
    setEpField,
    conn,
    connected,
    pending,
    probe,
    ingest,
    analyseBatch,
    verifyManifest,
    cancelAnalysis,
    retryFailed,
    clearAll,
    backToCollect,
  } = workspace;
  const [drag, setDrag] = useState(false);
  const fileInput = useRef(null);

  /* ── which control earns the sulphur primary ──
     It depends on what actually works right now. With nothing to analyse
     against, verifying a real SHA-256 chain over your own files in your own
     browser is the thing that works — and it is the thesis. The primary slot
     never names its own failure, and where analysis is impossible the Analyse
     button is not offered at all rather than sitting there disabled. */
  let analyseLabel = " Analyse the batch";
  let analyseDisabled = true;
  if (connected) {
    if (!files.length) analyseLabel = " Analyse the batch";
    else if (!pending) analyseLabel = " All " + files.length + " analysed";
    else {
      analyseLabel =
        " Analyse " + pending + " file" + (pending === 1 ? "" : "s");
      analyseDisabled = analysing;
    }
  } else {
    /* Warming is a wait, not a failure, and the label says which one it is. */
    analyseLabel =
      conn.s === "probing"
        ? " Warming up the models…"
        : " Analyse — service unavailable";
  }
  const primaryIsAnalyse = CAN_ANALYSE && connected;

  const done = files.filter((f) => f.result);
  const flagged = done.filter((f) => f.result.record.qc_flag !== "normal");
  const confs = done
    .map((f) => f.result.record.confluency_pct)
    .sort((a, b) => a - b);
  const actions = {};
  done.forEach((f) => {
    const a = f.result.record.recommended_action;
    actions[a] = (actions[a] || 0) + 1;
  });

  /* flagged first, then submission order */
  const order = files
    .map((f, i) => [f, i])
    .sort((a, b) => {
      const fa = a[0].result && a[0].result.record.qc_flag !== "normal" ? 0 : 1;
      const fb = b[0].result && b[0].result.record.qc_flag !== "normal" ? 0 : 1;
      return fa - fb || a[1] - b[1];
    });

  return (
    <section className="sec" id="sec-upload">
      <div className="sechead rv">
        <h2>Upload your microscopy images</h2>
        <span className="docaddr">Upload &middot; batch</span>
      </div>
      <p className="lede rv">
        Add a microscopy image or a ZIP batch, run the analysis, and review
        confluency and quality flags. Each result stays linked to its source
        image.
      </p>
      <ol className="upload-steps" aria-label="Analysis progress">
        {[
          ["Add images", "Choose files or drop a batch"],
          ["Run analysis", "Measure confluency and assess QC"],
          ["Review results", "Inspect verdicts and verify records"],
        ].map(([title, detail], i) => (
          <li
            key={title}
            aria-current={PHASE_STEP[phase] === i ? "step" : undefined}
          >
            <span>{String(i + 1).padStart(2, "0")}</span>
            <div>
              <strong>{title}</strong>
              <small>{detail}</small>
            </div>
          </li>
        ))}
      </ol>
      <p className="upload-expectation">
        <strong>Before you begin</strong> Phase-contrast / brightfield images ·
        Up to 64 MB per file. CPU analysis typically takes about a minute for
        small images; larger fields and batches take longer.
      </p>

      {!analysing && files.some((f) => f.error) && (
        <button
          className="button secondary"
          type="button"
          onClick={retryFailed}
        >
          Reset failed images for retry
        </button>
      )}
      {done.length > 0 && (
        <div className="completed-fields" aria-label="Inspect completed fields">
          {done.map((f, i) => (
            <button
              type="button"
              key={i}
              disabled={analysing}
              onClick={() => setLive({ name: f.name, result: f.result })}
            >
              Inspect {f.name}
            </button>
          ))}
        </div>
      )}
      {live && (
        <div id="live-instrument" style={{ scrollMarginTop: 80 }}>
          <Instrument {...live} />
        </div>
      )}
      {phase === "collect" && (
      <div className={"upgrid rv" + (CAN_ANALYSE ? "" : " solo")}>
        <div>
          {files.length === 0 ? (
            <>
              <label
                className="dropzone"
                id="dropzone"
                htmlFor="filein"
                data-drag={drag ? "on" : "off"}
                onDragEnter={(e) => {
                  e.preventDefault();
                  setDrag(true);
                }}
                onDragOver={(e) => {
                  e.preventDefault();
                  setDrag(true);
                }}
                onDragLeave={(e) => {
                  e.preventDefault();
                  if (!e.currentTarget.contains(e.relatedTarget)) setDrag(false);
                }}
                onDrop={(e) => {
                  e.preventDefault();
                  setDrag(false);
                  const list = [...(e.dataTransfer.files || [])];
                  if (list.length) ingest(list);
                }}
              >
                <svg
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="1.5"
                  aria-hidden="true"
                >
                  <path
                    d="M12 16V4m0 0L7.5 8.5M12 4l4.5 4.5"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  />
                  <path
                    d="M3 15v3.5A1.5 1.5 0 0 0 4.5 20h15a1.5 1.5 0 0 0 1.5-1.5V15"
                    strokeLinecap="round"
                  />
                </svg>
                <p className="dzmain">Drop images or a .zip</p>
                <p className="dzsub" id="dz-help">
                  or click to choose &middot; <b>png jpg tif bmp webp zip</b>
                  <br />
                  up to <b id="dz-cap">{MAX_FILES}</b> files &middot;{" "}
                  <span id="dz-privacy">
                    {/* The privacy line has to track reality: once an endpoint is
                        connected the bytes really do leave, and the dropzone must
                        not still promise they don't. */}
                    {connected
                      ? "analysed files are sent to the endpoint you connected"
                      : "your files stay in this browser"}
                  </span>
                </p>
                {/* The zone is a <label for=filein>: click and keyboard activation
                    are native, and the real file input carries focus and the
                    accessible name. No JS needed. */}
                <input
                  type="file"
                  id="filein"
                  disabled={analysing}
                  ref={fileInput}
                  multiple
                  aria-describedby="dz-help"
                  aria-label="Choose images or a ZIP archive to analyse"
                  accept=".png,.jpg,.jpeg,.tif,.tiff,.bmp,.webp,.zip,image/*,application/zip"
                  onChange={(e) => {
                    if (e.target.files.length) ingest([...e.target.files]);
                  }}
                />
              </label>
              <p className="foot" id="dz-error" role="alert">
                {error}
              </p>
              <p className="foot" id="data-handling">
                <strong>What happens to your files</strong> Hashing and
                manifest chaining always happen locally, in this browser.{" "}
                {CAN_ANALYSE ? (
                  <>
                    When connected, each image is also sent to{" "}
                    <code>{endpoint}</code> for confluency and QC analysis;
                    the service discards the file right after processing it
                    and keeps only the resulting record, in a log that resets
                    when the service restarts.
                  </>
                ) : (
                  "This build has no analysis endpoint configured, so nothing ever leaves your browser."
                )}
              </p>
            </>
          ) : (
            <div className="upload-preview" id="upload-preview">
              <input
                type="file"
                id="filein"
                disabled={analysing}
                ref={fileInput}
                multiple
                className="sr"
                aria-label="Choose more images or a ZIP archive to analyse"
                accept=".png,.jpg,.jpeg,.tif,.tiff,.bmp,.webp,.zip,image/*,application/zip"
                onChange={(e) => {
                  if (e.target.files.length) ingest([...e.target.files]);
                }}
              />
              <div className="stats">
                <Stat k="Files" v={String(files.length)} />
                <Stat
                  k="Total size"
                  v={fmtBytes(files.reduce((a, f) => a + f.size, 0))}
                />
                <Stat
                  cls="q"
                  k="Ready"
                  v={pending ? pending + " not yet analysed" : "All analysed"}
                />
              </div>
              <p className="foot" id="dz-error" role="alert">
                {error}
              </p>
              <div className="actions batchacts">
                {CAN_ANALYSE && (
                  <button
                    className={primaryIsAnalyse ? "cta" : "cta2"}
                    id="analyse-btn"
                    type="button"
                    disabled={analyseDisabled}
                    onClick={analyseBatch}
                  >
                    <svg
                      viewBox="0 0 24 24"
                      fill="none"
                      stroke="currentColor"
                      strokeWidth="2"
                      aria-hidden="true"
                    >
                      <path d="M6 4l14 8-14 8V4z" strokeLinejoin="round" />
                    </svg>
                    {analyseLabel}
                  </button>
                )}
                <button
                  className="cta2"
                  type="button"
                  onClick={() => fileInput.current?.click()}
                >
                  <Icon name="plus" />
                  Add more images
                </button>
                <button
                  className="cta2"
                  id="clear-btn"
                  type="button"
                  onClick={() => clearAll(fileInput)}
                >
                  Clear
                </button>
              </div>
            </div>
          )}
        </div>

        {/* Not hidden — absent, so nothing can reveal it. To a visitor with no
            analysis available this is plumbing for a machine they do not have. */}
        {CAN_ANALYSE && (
          <div className="conn" id="conn" data-s={conn.s}>
            <div className="connhead">
              <span className="conndot" aria-hidden="true"></span>
              <p className="connname" id="connname">
                {conn.name}
              </p>
            </div>
            <p className="conntext" id="conntext">
              {conn.text}
            </p>
            {/* A hosted API is not something a visitor should be retyping; only
                someone running the repo locally has another endpoint worth
                pointing at. */}
            {!(ANALYSIS_API && !LOCAL_TOOLING) && (
              <div className="connrow">
                <label className="sr" htmlFor="epinput">
                  Endpoint URL
                </label>
                <input
                  className="epinput"
                  id="epinput"
                  type="url"
                  spellCheck="false"
                  autoComplete="off"
                  value={epField}
                  onChange={(e) => setEpField(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter") {
                      e.preventDefault();
                      probe(epField.trim() || DEFAULT_ENDPOINT);
                    }
                  }}
                />
                <button
                  className="minibtn"
                  id="epgo"
                  type="button"
                  onClick={() => probe(epField.trim() || DEFAULT_ENDPOINT)}
                >
                  Connect
                </button>
              </div>
            )}
          </div>
        )}
      </div>
      )}

      {files.length > 0 && phase !== "collect" && (
        <div id="batch">
          <div className="batchhead rv">
            <h3 id="batch-title">
              {files.length === 1 ? "One file" : files.length + " files"}
            </h3>
            <span className="docaddr" id="batch-addr">
              Manifest · SHA-256 chained
            </span>
          </div>

          <div className="stats" id="batch-stats">
            <Stat k="Files" v={String(files.length)} />
            <Stat
              k="Total size"
              v={fmtBytes(files.reduce((a, f) => a + f.size, 0))}
            />
            <Stat
              k="Analysed"
              v={
                <>
                  {done.length}
                  <small>/ {files.length}</small>
                </>
              }
            />
            {done.length ? (
              <>
                <Stat
                  k="Confluency median"
                  v={
                    <>
                      {confs[Math.floor(confs.length / 2)].toFixed(1)}
                      <small>%</small>
                    </>
                  }
                />
                <Stat
                  k="Confluency range"
                  v={
                    <>
                      {confs[0].toFixed(1)}–{confs[confs.length - 1].toFixed(1)}
                      <small>%</small>
                    </>
                  }
                />
                <Stat k="Flagged" v={String(flagged.length)} />
                <Stat
                  cls="q"
                  k="Actions"
                  v={
                    Object.keys(actions).length
                      ? Object.keys(actions).map((a, i) => (
                          <span key={a}>
                            {i > 0 && <br />}
                            {(ACTION_LABEL[a] || a) + " " + actions[a]}
                          </span>
                        ))
                      : "—"
                  }
                />
              </>
            ) : (
              <Stat
                cls="q"
                k="Verdicts"
                v={connected ? "Not yet run" : "Not analysed"}
              />
            )}
          </div>

          <div className="actions batchacts">
            {CAN_ANALYSE && (
              <button
                className={primaryIsAnalyse ? "cta" : "cta2"}
                style={{ order: primaryIsAnalyse ? 0 : 1 }}
                id="analyse-btn"
                type="button"
                disabled={analyseDisabled}
                onClick={analyseBatch}
              >
                <svg
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                  aria-hidden="true"
                >
                  <path d="M6 4l14 8-14 8V4z" strokeLinejoin="round" />
                </svg>
                {analyseLabel}
              </button>
            )}
            <button
              className={primaryIsAnalyse ? "cta2" : "cta"}
              style={{ order: primaryIsAnalyse ? 1 : 0 }}
              id="verify-batch"
              type="button"
              onClick={verifyManifest}
            >
              <svg
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2.2"
                aria-hidden="true"
              >
                <path
                  d="M4 12.5l5.2 5.2L20 7"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                />
              </svg>
              Verify manifest
            </button>
            <button
              className="cta2"
              id="cancel-btn"
              type="button"
              hidden={!analysing}
              onClick={cancelAnalysis}
            >
              <svg
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                aria-hidden="true"
              >
                <path d="M6 6l12 12M18 6L6 18" strokeLinecap="round" />
              </svg>
              Stop analysing
            </button>
            <button
              className="cta2"
              id="clear-btn"
              disabled={analysing}
              type="button"
              onClick={() => clearAll(fileInput)}
            >
              Clear
            </button>
            {phase === "results" && (
              <button
                className="cta2"
                id="upload-more-btn"
                type="button"
                onClick={backToCollect}
              >
                <Icon name="plus" />
                Upload more images
              </button>
            )}
          </div>

          <div className="prog" aria-hidden="true">
            <i id="prog-bar" style={{ transform: `scaleX(${prog.bar})` }}></i>
          </div>
          <p
            className="progtext"
            id="prog-text"
            role="status"
            aria-live="polite"
          >
            {prog.text}
          </p>

          <p className="scrollnote scrollnote-hi">
            Table scrolls sideways &rarr;
          </p>
          <div
            className="scrollx manifestwrap"
            tabIndex={0}
            role="region"
            aria-label="Uploaded file manifest, scrollable"
          >
            <table className="btable">
              <thead>
                <tr>
                  <th scope="col">#</th>
                  <th scope="col">File</th>
                  <th scope="col">Pixels</th>
                  <th scope="col">Confluency</th>
                  <th scope="col">QC flag</th>
                  <th scope="col">Action</th>
                  <th scope="col">SHA-256 of file</th>
                  <th scope="col">Record</th>
                </tr>
              </thead>
              <tbody id="btbody">
                {order.map(([f, i]) => {
                  const isFlagged = !!(
                    f.result && f.result.record.qc_flag !== "normal"
                  );
                  const r = f.result && f.result.record;
                  return (
                    <tr key={f.hash + ":" + i} data-flagged={String(isFlagged)}>
                      <td className="bidx">{pad2(i + 1)}</td>
                      <td>
                        <div
                          style={{
                            display: "flex",
                            alignItems: "center",
                            gap: "10px",
                            minWidth: 0,
                          }}
                        >
                          {f.thumb ? (
                            <img className="bthumb" src={f.thumb} alt="" />
                          ) : (
                            <div
                              className="bthumb none"
                              role="img"
                              title="No preview: the browser cannot decode this format. The file was still hashed and analysed."
                              aria-label={"No preview available for " + f.name}
                            ></div>
                          )}
                          <span className="bname" title={f.name}>
                            {f.name}
                          </span>
                        </div>
                      </td>
                      <td className="mono">{f.w ? f.w + "×" + f.h : "—"}</td>
                      {f.error ? (
                        <td
                          className="mono"
                          colSpan={3}
                          style={{ color: "var(--v-red)" }}
                        >
                          {f.error}
                        </td>
                      ) : r ? (
                        <>
                          <td className="mono">
                            {r.confluency_pct.toFixed(2)}%
                          </td>
                          <td style={{ textAlign: "right" }}>
                            <span
                              className="chip"
                              data-v={FLAG_TONE[r.qc_flag] || "idle"}
                              title={
                                r.qc_confidence != null
                                  ? "confidence " + r.qc_confidence.toFixed(3)
                                  : undefined
                              }
                            >
                              {FLAG_SHORT[r.qc_flag] || r.qc_flag}
                            </span>
                          </td>
                          <td className="mono">
                            {ACTION_LABEL[r.recommended_action] ||
                              r.recommended_action}
                          </td>
                        </>
                      ) : (
                        <td
                          className="pend"
                          colSpan={3}
                          data-state={
                            f.hash === analysingHash ? "analysing" : "queued"
                          }
                        >
                          {f.hash === analysingHash
                            ? "analysing…"
                            : connected
                              ? "not yet analysed"
                              : "hashed · not analysed"}
                        </td>
                      )}
                      <td className="mono">{f.hash.slice(0, 16)}…</td>
                      <td className="mono" id={"brec-" + i}>
                        {f.recordHash ? f.recordHash.slice(0, 16) + "…" : "—"}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
          <p className="foot" id="batch-foot">
            {done.length ? (
              <>
                Verdicts came from the pipeline at <code>{endpoint}</code>.
                Every row is one line in that endpoint&rsquo;s hash-chained log.
              </>
            ) : connected ? (
              "Each row is a manifest line: the file's real SHA-256, linked to the line before it. Press Analyse to fill the verdict columns from the pipeline."
            ) : (
              <>
                Each row is a manifest line: the file&rsquo;s real SHA-256
                &mdash; the same digest <code>records.py</code> writes &mdash;
                linked to the line before it. Press Verify to recompute the
                whole chain here in your browser.{" "}
                {CAN_ANALYSE
                  ? "Connect the pipeline to fill the verdict columns as well."
                  : "The verdicts are the one thing this page will not do: the models do not run in a browser, and a guessed confluency is exactly the error the page is about."}
              </>
            )}
          </p>
        </div>
      )}
    </section>
  );
}

function Stat({ k, v, cls }) {
  return (
    <div className="stat">
      <p className="statk">{k}</p>
      <p className={"statv" + (cls ? " " + cls : "")}>{v}</p>
    </div>
  );
}
