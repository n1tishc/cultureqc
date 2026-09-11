import { useCallback, useEffect, useRef, useState } from "react";
import { readAnalysis } from "../lib/analysisStream";
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
import { pad2 } from "../lib/labels";

const IMG_RE = /\.(png|jpe?g|tiff?|bmp|webp)$/i;
const DECODABLE = /\.(png|jpe?g|bmp|webp)$/i;

/* A field that goes quiet for this long — no bytes at all, not even a
   heartbeat — is treated as stalled, not slow. The server heartbeats every
   10s once it starts responding (deploy/hf-space/api.py), so this leaves
   generous margin for jitter and for the pre-first-byte wait, without ever
   capping a run that is genuinely still producing stages. */
const IDLE_TIMEOUT_MS = 45000;
const IDLE_MESSAGE =
  "No response from the analysis service for a while — it may be stuck.";

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

/* Owns the upload/analysis state at the App level so it survives the Upload
   route unmounting on navigation (App itself never unmounts) and so the
   session's analysed records can be read from the Audit route too. */
export default function useUploadWorkspace() {
  const [files, setFiles] = useState([]);
  const [live, setLive] = useState(null);
  const [error, setError] = useState("");
  const [prog, setProg] = useState({
    bar: 0,
    text: "Manifest built — not yet analysed",
  });
  const [analysing, setAnalysing] = useState(false);
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
  const inFlight = useRef(null);

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
              The connected pipeline is warm. Add your images, then select
              Analyse — each image is sent to <code>{base}</code> for
              confluency and QC scoring; hashing and manifesting always happen
              here in your browser.
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

  /* Stream one field at a time and re-chain completed outcomes after each field.
     Every request runs under an idle timer that any received byte — including a
     heartbeat — resets. A field that stalls before its first byte or between
     stages is aborted and reported as a visible, retryable error instead of
     spinning forever (the demo-killer this exists to fix). */
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
        const ctl = new AbortController();
        inFlight.current = ctl;
        let idleTimer;
        const bump = () => {
          clearTimeout(idleTimer);
          idleTimer = setTimeout(
            () => ctl.abort(new DOMException(IDLE_MESSAGE, "AbortError")),
            IDLE_TIMEOUT_MS,
          );
        };
        bump(); // clock starts before the request is even sent
        try {
          const fd = new FormData();
          fd.append("image", f.file, f.name);
          fd.append("cell_line", "unknown");
          fd.append("target_confluency", "80");
          fd.append("stream", "true");
          const r = await fetch(endpoint + "/analyze", {
            method: "POST",
            body: fd,
            signal: ctl.signal,
          });
          bump(); // headers arrived; reset for the body stream
          const j = await readAnalysis(
            r,
            (event) =>
              setLive((previous) => ({
                name: f.name,
                event: {
                  ...previous?.event,
                  ...event,
                  visuals: { ...previous?.event?.visuals, ...event.visuals },
                },
              })),
            bump,
          );
          clearTimeout(idleTimer);
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
          clearTimeout(idleTimer);
          /* A user-initiated stop is not a failure of this field — it is left
             exactly as it was (not yet analysed), so it is picked up again the
             next time Analyse runs rather than parked behind a raw
             AbortException in the manifest. */
          if (!cancelled.current) {
            const message =
              e.name === "AbortError" ? IDLE_MESSAGE : String(e.message || e);
            outcomes.set(f, { error: message.slice(0, 160) });
            setLive({ name: f.name, error: message });
          }
        } finally {
          inFlight.current = null;
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

  /* Used to only flip a flag the loop checked between images — if the current
     request had already stalled, there was no next check to reach. Aborting
     the in-flight request makes the button work even while a field is stuck,
     which is why it now reads "Stop analysing" rather than promising to
     finish the field in progress. */
  function cancelAnalysis() {
    cancelled.current = true;
    inFlight.current?.abort();
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

  function retryFailed() {
    setFiles((list) => list.map((f) => ({ ...f, error: null })));
    setLive(null);
  }

  function clearAll(fileInput) {
    setFiles([]);
    setLive(null);
    setError("");
    setProg({ bar: 0, text: "Manifest built — not yet analysed" });
    if (fileInput?.current) fileInput.current.value = "";
  }

  return {
    files,
    live,
    setLive,
    error,
    prog,
    analysing,
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
    ANALYSIS_API,
    LOCAL_TOOLING,
    DEFAULT_ENDPOINT,
  };
}
