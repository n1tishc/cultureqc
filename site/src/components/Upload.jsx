import Instrument from "./Instrument";
import { readAnalysis } from "../lib/analysisStream";
import { useCallback, useEffect, useRef, useState } from "react";
import {
  ANALYSIS_API,
  CAN_ANALYSE,
  DEFAULT_ENDPOINT,
  LOCAL_TOOLING,
  MAX_BYTES,
  MAX_FILES,
  START_ENDPOINT,
} from "../config";
import { GENESIS, canonJSON, sha256, sha256Bytes } from "../lib/hash";
import { readZip } from "../lib/zip";
import {
  ACTION_LABEL,
  FLAG_SHORT,
  FLAG_TONE,
  fmtBytes,
  pad2,
} from "../lib/labels";

const IMG_RE = /\.(png|jpe?g|tiff?|bmp|webp)$/i;
const DECODABLE = /\.(png|jpe?g|bmp|webp)$/i;

/* One hash chain across the whole batch, built in the browser. Returns a new
   array — every worker's result is folded in before this runs, so nothing here
   is mutating a record another async task still holds. */
async function rechain(list) {
  let prev = GENESIS;
  const out = [];
  for (const r of list) {
    const body = {
      schema_version: "0.2-ingest",
      image_ref: r.name,
      image_hash: r.hash,
      bytes: r.size,
      pixels: r.w && r.h ? r.w + "x" + r.h : null,
      confluency_pct: r.result ? r.result.record.confluency_pct : null,
      qc_flag: r.result ? r.result.record.qc_flag : null,
      recommended_action: r.result ? r.result.record.recommended_action : null,
      prev_record_hash: prev,
    };
    const canonical = canonJSON(body);
    const recordHash = await sha256(canonical);
    out.push({ ...r, canonical, recordHash, prevHash: prev });
    prev = recordHash;
  }
  return out;
}

export default function Upload() {
  const [files, setFiles] = useState([]);
  const [live, setLive] = useState(null);
  const [error, setError] = useState("");
  const [prog, setProg] = useState({
    bar: 0,
    text: "Manifest built — not yet analysed",
  });
  const [analysing, setAnalysing] = useState(false);
  const [drag, setDrag] = useState(false);
  const [endpoint, setEndpoint] = useState(START_ENDPOINT);
  const [epField, setEpField] = useState(START_ENDPOINT);
  const [conn, setConn] = useState({
    s: "probing",
    name: "Looking for the pipeline…",
    text: (
      <>
        Checking <code>{START_ENDPOINT}</code>
      </>
    ),
  });
  const cancelled = useRef(false);
  const warmTimer = useRef(0);
  const fileInput = useRef(null);

  const connected = conn.s === "on";
  const pending = files.filter((f) => !f.result && !f.error).length;

  /* ── the pipeline connection ──
     The hosted service sleeps when idle and reloads both models on the next
     request, so "reachable" and "ready" are genuinely different states and the
     page says which one it is in. Warming is not an error and is not written as
     one: it resolves on its own, so the page keeps asking rather than making the
     visitor press anything. */
  const probe = useCallback(async (url, opts = {}) => {
    const { quiet, tries = 0 } = opts;
    const base = url.replace(/\/$/, "");
    clearTimeout(warmTimer.current);
    if (!quiet)
      setConn({
        s: "probing",
        name: "Looking for the pipeline…",
        text: (
          <>
            Checking <code>{base}</code>
          </>
        ),
      });
    try {
      const ctl = new AbortController();
      /* A sleeping host wakes on the request itself, and that first one can take
         most of a minute to answer — so the timeout has to be longer than a
         liveness check would need, or the wake is aborted before it lands. */
      const to = setTimeout(() => ctl.abort(), 30000);
      const r = await fetch(base + "/health", { signal: ctl.signal });
      clearTimeout(to);
      const j = await r.json();
      if (j.status !== "ok")
        throw new Error("service replied but is not ready");
      setEndpoint(base);
      if (j.models_loaded) {
        setConn({
          s: "on",
          name: "Analysis ready",
          text: (
            <>
              The models are ready. Add your images, then select Analyse to
              measure confluency and review culture quality.
            </>
          ),
        });
      } else if (j.error) {
        setConn({
          s: "off",
          name: "Analysis unavailable",
          text: "The service is up but its models did not load. Files are still hashed and manifested in your browser.",
        });
      } else {
        setConn({
          s: "probing",
          name: "Warming up the models…",
          text: "The service loads Cellpose-SAM and the QC classifier on wake, which takes about a minute. Your files are being hashed meanwhile.",
        });
        warmTimer.current = setTimeout(
          () => probe(base, { quiet: true }),
          5000,
        );
      }
    } catch {
      /* A hosted service that has gone to sleep is woken by the request that
         fails, so the first failure means "not up yet" far more often than it
         means "gone". Retrying twice before saying anything final is the
         difference between a visitor seeing the service work and a visitor being
         told it is unavailable while it boots behind them. A local endpoint gets
         no retries: if it is not listening, it is not listening. */
      if (!LOCAL_TOOLING && tries < 2) {
        setConn({
          s: "probing",
          name: "Waking the analysis service…",
          text: "It sleeps when idle and takes about a minute to come back. Your files are being hashed meanwhile.",
        });
        warmTimer.current = setTimeout(
          () => probe(base, { quiet: true, tries: tries + 1 }),
          15000,
        );
        return;
      }
      setConn({
        s: "off",
        name: "Analysis unavailable",
        text: LOCAL_TOOLING ? (
          <>
            Files are hashed and manifested in your browser. For verdicts too,
            run <code>python deploy/hf-space/api.py</code> and press Connect.
          </>
        ) : (
          "Files are hashed and manifested in your browser, and the manifest still verifies. Verdicts are unavailable until the service is back."
        ),
      });
    }
  }, []);

  useEffect(() => {
    if (CAN_ANALYSE) probe(START_ENDPOINT);
    return () => clearTimeout(warmTimer.current);
  }, [probe]);

  /* ── ingest ── */
  async function ingest(list) {
    if (analysing) return;
    setError("");
    let incoming = [];
    try {
      for (const f of list) {
        if (/\.zip$/i.test(f.name) || f.type === "application/zip") {
          incoming = incoming.concat(await readZip(f));
        } else if (IMG_RE.test(f.name)) {
          incoming.push(f);
        }
      }
    } catch (e) {
      setError("Could not read that file: " + e.message);
      return;
    }
    if (!incoming.length) {
      setError(
        "No usable images there. Accepted: png, jpg, tif, bmp, webp, or a .zip containing them.",
      );
      return;
    }
    const room = MAX_FILES - files.length;
    if (incoming.length > room) {
      setError(
        "Kept the first " +
          room +
          " files — this page caps a batch at " +
          MAX_FILES +
          ".",
      );
      incoming = incoming.slice(0, room);
    }

    setProg((p) => ({
      ...p,
      text:
        "Hashing " +
        incoming.length +
        " file" +
        (incoming.length === 1 ? "" : "s") +
        "…",
    }));

    const added = [];
    for (const f of incoming) {
      if (f.size > MAX_BYTES) continue;
      const buf = await f.arrayBuffer();
      const rec = {
        name: f.name,
        size: f.size,
        file: f,
        hash: await sha256Bytes(buf),
        w: null,
        h: null,
        thumb: null,
        result: null,
        error: null,
      };
      if (DECODABLE.test(f.name)) {
        try {
          const bmp = await createImageBitmap(new Blob([buf]));
          rec.w = bmp.width;
          rec.h = bmp.height;
          const side = 76;
          const c = document.createElement("canvas");
          c.width = side;
          c.height = side;
          const g = c.getContext("2d");
          const s = Math.max(side / bmp.width, side / bmp.height);
          g.drawImage(
            bmp,
            (side - bmp.width * s) / 2,
            (side - bmp.height * s) / 2,
            bmp.width * s,
            bmp.height * s,
          );
          rec.thumb = c.toDataURL("image/webp", 0.7);
          c.width = Math.round(
            bmp.width * Math.min(1, 1024 / Math.max(bmp.width, bmp.height)),
          );
          c.height = Math.round(
            bmp.height * Math.min(1, 1024 / Math.max(bmp.width, bmp.height)),
          );
          g.drawImage(bmp, 0, 0, c.width, c.height);
          rec.preview = c.toDataURL("image/png");
          bmp.close();
        } catch {
          /* undecodable in this browser; the hash still stands */
        }
      }
      added.push(rec);
    }

    const next = await rechain(files.concat(added));
    setFiles(next);
    const p = next.filter((f) => !f.result && !f.error).length;
    setProg({
      bar: 0,
      text: p
        ? "Manifest built — " +
          p +
          " file" +
          (p === 1 ? "" : "s") +
          " not yet analysed"
        : "Manifest built",
    });
  }

  /* Stream one field at a time and re-chain completed outcomes after each field. */
  async function analyseBatch() {
    if (analysing || !connected) return;
    setAnalysing(true);
    cancelled.current = false;

    const todo = files.filter((f) => !f.result && !f.error);
    const queue = todo.slice();
    const outcomes = new Map();
    let done = 0;
    const tick = () =>
      setProg({
        bar: done / Math.max(todo.length, 1),
        text:
          "Analysed " +
          done +
          " of " +
          todo.length +
          (cancelled.current ? " — cancelled" : "…"),
      });
    tick();

    const worker = async () => {
      while (queue.length && !cancelled.current) {
        const f = queue.shift();
        setLive({
          name: f.name,
          event: { stage: "queued", visuals: { raw: f.preview } },
        });
        if (done === 0)
          requestAnimationFrame(() => {
            document
              .getElementById("live-instrument")
              ?.scrollIntoView({ block: "start", behavior: "instant" });
          });
        try {
          const fd = new FormData();
          fd.append("image", f.file, f.name);
          fd.append("cell_line", "unknown");
          fd.append("target_confluency", "80");
          fd.append("stream", "true");
          /* Cellpose-SAM on CPU is tens of seconds per field, and a sleeping
             Space adds a cold boot on top. No timeout here beyond the abort the
             model is computing. Stop after current image skips pending files. */
          const r = await fetch(endpoint + "/analyze", {
            method: "POST",
            body: fd,
          });
          const j = await readAnalysis(r, (event) =>
            setLive((previous) => ({
              name: f.name,
              event: {
                ...previous?.event,
                ...event,
                visuals: { ...previous?.event?.visuals, ...event.visuals },
              },
            })),
          );
          if (j.record?.image_hash !== f.hash)
            throw new Error(
              "Analysis response does not match the uploaded image",
            );
          if (j.record_canonical) {
            const { record_hash, ...body } = j.record;
            if (
              (await sha256(j.record_canonical)) !== record_hash ||
              canonJSON(JSON.parse(j.record_canonical)) !== canonJSON(body)
            )
              throw new Error("Analysis record failed integrity verification");
          }
          outcomes.set(f, { result: j });
          setLive({ name: f.name, result: j });
        } catch (e) {
          outcomes.set(f, { error: String(e.message || e).slice(0, 160) });
          setLive({ name: f.name, error: String(e.message || e) });
        }
        done++;
        const partial = files.map((item) =>
          outcomes.has(item) ? { ...item, ...outcomes.get(item) } : item,
        );
        setFiles(await rechain(partial));
        tick();
      }
    };
    // The server serializes inference; submit sequentially so stages belong to one field.
    await worker();

    const merged = files.map((f) =>
      outcomes.has(f) ? { ...f, ...outcomes.get(f) } : f,
    );
    const next = await rechain(merged);
    setFiles(next);
    const ok = next.filter((f) => f.result).length;
    setProg({
      bar: 1,
      text: cancelled.current
        ? "Cancelled — " + ok + " of " + next.length + " analysed"
        : ok +
          " of " +
          next.length +
          " analysed · manifest re-chained with the verdicts",
    });
    setAnalysing(false);
  }

  async function verifyManifest() {
    if (!files.length) return;
    setProg((p) => ({ ...p, text: "Recomputing the manifest chain…" }));
    let prev = GENESIS;
    let bad = -1;
    for (let i = 0; i < files.length; i++) {
      const digest = await sha256(files[i].canonical);
      const rec = JSON.parse(files[i].canonical);
      if (digest !== files[i].recordHash || rec.prev_record_hash !== prev)
        if (bad < 0) bad = i;
      prev = digest;
    }
    setProg((p) => ({
      ...p,
      text:
        bad < 0
          ? "Manifest intact — " +
            files.length +
            " records re-hashed in your browser"
          : "Manifest broken at record " + pad2(bad + 1),
    }));
  }

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
            aria-current={
              (analysing ? 1 : done.length ? 2 : files.length ? 1 : 0) === i
                ? "step"
                : undefined
            }
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
          onClick={() => {
            setFiles((list) => list.map((f) => ({ ...f, error: null })));
            setLive(null);
          }}
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
      <div className={"upgrid rv" + (CAN_ANALYSE ? "" : " solo")}>
        <div>
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

      {files.length > 0 && (
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
              onClick={() => {
                cancelled.current = true;
              }}
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
              Stop after current image
            </button>
            <button
              className="cta2"
              id="clear-btn"
              disabled={analysing}
              type="button"
              onClick={() => {
                setFiles([]);
                setLive(null);
                setError("");
                setProg({ bar: 0, text: "Manifest built — not yet analysed" });
                if (fileInput.current) fileInput.current.value = "";
              }}
            >
              Clear
            </button>
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
                        <td className="pend" colSpan={3}>
                          {connected
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
