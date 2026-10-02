import { useEffect, useMemo, useRef, useState } from "react";
import { checkCheckpoint, rewriteFrom, verifyChain } from "../lib/verify";
import { Icon, actionWord, short } from "./ui";

/* The seven stored records, re-hashed in this browser from the exact bytes
   culture/records.py hashed. Three switches, one at a time, tamper in memory
   and re-run the same check: edit one number in record 3; edit it and
   recompute every later hash; delete the last two records. Each result is also
   checked against the anchored checkpoint build_data.py made from the stored
   records (count and head hash), which catches the two a chain alone passes. */

const MODES = [
  ["edit", "Change one number in record 3"],
  ["rewrite", "Rewrite record 3 and every hash after it"],
  ["truncate", "Delete the last two records"],
];

const FIELDS = [
  ["image_hash", "SHA-256 of the image file that was read."],
  ["confluency_map_hash", "SHA-256 of Cellpose-SAM’s probability map, so the map behind the number can be checked later."],
  ["model_versions", "Segmentation, anomaly and classifier model identifiers."],
  ["config_hashes", "SHA-256 of each config in force: anomaly thresholds, calibration, detectability matrix, QC settings."],
  ["decided_by", "The rules version that chose the action."],
  ["anomaly_used_in_decision", "Whether the anomaly flag could change the action (true since rules_v0.3)."],
  ["qc_used_in_decision", "The demoted classifier: recorded, false."],
  ["reviewed_by · review_outcome", "Empty here, left for the platform’s review workflow to fill."],
  ["prev_record_hash · record_hash", "The chain: each record’s hash covers every field above plus the previous record’s hash."],
];

function tamper(canonical) {
  return canonical.replace(/"confluency_pct":(-?[\d.]+)/, (_, n) => `"confluency_pct":${(Number(n) + 10).toFixed(2)}`);
}

function Json({ obj, bad }) {
  const pre = useRef(null);
  useEffect(() => {
    const el = pre.current;
    const hit = el && el.querySelector(".bad");
    if (hit) {
      const top = hit.getBoundingClientRect().top - el.getBoundingClientRect().top + el.scrollTop;
      el.scrollTo({ top: Math.max(0, top - el.clientHeight / 2), behavior: "smooth" });
    }
  }, [bad]);
  const text = JSON.stringify(obj, null, 2);
  const out = [];
  const re = /("(?:[^"\\]|\\.)*")(\s*:)?|(-?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?)|\b(true|false|null)\b/g;
  let last = 0;
  let m;
  let i = 0;
  let key = null;
  while ((m = re.exec(text))) {
    out.push(text.slice(last, m.index));
    if (m[1] && m[2]) {
      key = m[1].slice(1, -1);
      out.push(
        <span key={i++} className="k">
          {m[1]}
        </span>,
        m[2],
      );
    } else if (m[1]) {
      out.push(
        <span key={i++} className="s">
          {m[1]}
        </span>,
      );
    } else if (m[3]) {
      out.push(
        <span key={i++} className={key === bad ? "n bad" : "n"}>
          {m[3]}
        </span>,
      );
    } else {
      out.push(
        <span key={i++} className="z">
          {m[4]}
        </span>,
      );
    }
    last = re.lastIndex;
  }
  out.push(text.slice(last));
  return (
    <pre className="json" ref={pre} tabIndex={0} aria-label="The selected record, parsed">
      {out}
    </pre>
  );
}

export default function Records({ examples }) {
  const byId = useMemo(() => Object.fromEntries(examples.items.map((e) => [e.id, e])), [examples]);
  const chain = useMemo(() => examples.chain_order.map((id) => byId[id]), [examples, byId]);
  const cp = examples.checkpoint;
  const n = chain.length;
  const [mode, setMode] = useState(null);
  const [sel, setSel] = useState(2);
  const [view, setView] = useState(null);

  useEffect(() => {
    let live = true;
    (async () => {
      const base = chain.map((e) => e.record);
      let recs = base;
      if (mode === "edit") recs = base.map((r, i) => (i === 2 ? { ...r, canonical: tamper(r.canonical) } : r));
      if (mode === "rewrite") recs = await rewriteFrom(base, 2, tamper);
      if (mode === "truncate") recs = base.slice(0, n - 2);
      const res = await verifyChain(recs);
      if (live) setView({ mode, recs, res, anchor: checkCheckpoint(res, cp) });
    })();
    return () => {
      live = false;
    };
  }, [chain, mode, cp, n]);

  const ready = view && view.mode === mode;
  const recs = ready ? view.recs : chain.map((e) => e.record);
  const res = ready ? view.res : null;
  const nOk = res ? res.filter((r) => r.ok).length : null;
  const chainOk = res ? nOk === res.length : null;
  const anchorOk = res ? chainOk && view.anchor.ok : null;
  const shown = Math.min(sel, recs.length - 1);
  const obj = JSON.parse(recs[shown].canonical);
  obj.record_hash = recs[shown].record_hash;

  const pick = (m) => {
    setMode(m);
    setSel(m === "truncate" ? n - 3 : 2);
  };

  let msg = "Re-hashing…";
  if (res && mode === "edit")
    msg = `Confluency in record 3 raised by 10 points: ${n - nOk} of ${n} records now fail — record 3’s own hash, and record 4’s link to it. Records 1–2 are untouched.`;
  else if (res && mode === "rewrite")
    msg = `Record 3 raised by 10 points, then its hash and every later hash recomputed: all ${nOk} records verify, so the chain alone passes. Against the checkpoint it fails: record ${n} now hashes to ${short(res[n - 1].computed, 8)}, not the checkpoint’s head ${short(cp.head_hash, 8)}.`;
  else if (res && mode === "truncate")
    msg = `Records ${n - 1} and ${n} deleted: the ${nOk} left all verify, so the chain alone passes. Against the checkpoint it fails: ${res.length} records where it counted ${cp.count}.`;
  else if (res)
    msg = `All ${nOk} of ${n} records re-hash to their stored SHA-256 and link to the one before, and the chain matches the checkpoint: ${cp.count} records, head ${short(cp.head_hash, 8)}.`;

  return (
    <>
      <div className="chain" role="group" aria-label="The record chain">
        {chain.map((e, i) => {
          const gone = i >= recs.length;
          const r = res && !gone ? res[i] : null;
          const ok = gone ? "deleted" : r ? String(r.ok) : "pending";
          const rehashed = !gone && recs[i].record_hash !== e.record.record_hash;
          return (
            <button
              key={e.id}
              type="button"
              className="link"
              data-ok={ok}
              aria-pressed={!gone && i === shown}
              disabled={gone}
              onClick={() => setSel(i)}
            >
              <span className="n">#{i + 1}</span>
              <b>{e.label}</b>
              <span className="h">
                {gone ? "—" : rehashed ? <b className="changed">{short(recs[i].record_hash, 8)}</b> : short(recs[i].record_hash, 8)}
              </span>
              <span className="h">
                {(() => {
                  const act = actionWord(e.action).toLowerCase();
                  const now = gone ? e.confluency.pct : JSON.parse(recs[i].canonical).confluency_pct;
                  return now !== e.confluency.pct ? (
                    <>
                      <b className="changed">
                        {e.confluency.pct.toFixed(1)} → {now.toFixed(1)}%
                      </b>
                      <br />
                      {act}
                    </>
                  ) : (
                    `${e.confluency.pct.toFixed(1)}% · ${act}`
                  );
                })()}
              </span>
              <span className="st" data-ok={ok}>
                <Icon name={gone || (r && !r.ok) ? "cross" : "check"} />
                {gone ? "deleted" : !r ? "checking" : r.ok ? "verified" : !r.hashOk ? "hash mismatch" : "link broken"}
              </span>
            </button>
          );
        })}
      </div>

      <div className="tamper">
        <div className="switches" role="group" aria-label="Tamper with the chain, one way at a time">
          {MODES.map(([m, label], i) => (
            <div key={m} style={{ display: "contents" }}>
              <label className="switch">
                <input type="checkbox" checked={mode === m} onChange={(ev) => pick(ev.target.checked ? m : null)} />
                {label}
              </label>
              {i === 0 ? (
                <p className="tamper-limit">
                  A chain alone can’t detect a full rewrite or a deleted tail; an anchored checkpoint can — try it below. The checkpoint here (record count and head hash, <code>culture.records.checkpoint</code>) was made from the stored records when this page was built and ships with it. In deployment it is stored outside the log, in the platform’s audit trail or WORM storage (<code>docs/audit_mapping.md</code>).
                </p>
              ) : null}
            </div>
          ))}
        </div>
        <div className="verdicts" aria-live="polite">
          <span data-ok={res ? String(chainOk) : "pending"}>
            <Icon name={res && !chainOk ? "cross" : "check"} /> Chain alone: {res ? (chainOk ? "passes" : "fails") : "…"}
          </span>
          <span data-ok={res ? String(anchorOk) : "pending"}>
            <Icon name={res && !anchorOk ? "cross" : "check"} /> Against the anchored checkpoint: {res ? (anchorOk ? "passes" : "fails") : "…"}
          </span>
          <p>{msg}</p>
        </div>
      </div>

      <div className="rec-grid">
        <Json obj={obj} bad={(mode === "edit" || mode === "rewrite") && shown === 2 ? "confluency_pct" : null} />
        <div>
          <dl className="fields">
            {FIELDS.map(([k, d]) => (
              <div key={k} style={{ display: "contents" }}>
                <dt>{k}</dt>
                <dd>{d}</dd>
              </div>
            ))}
          </dl>
        </div>
      </div>

      <div className="scope">
        <b>Where this sits for GMP.</b> The chain catches an edited, inserted or reordered record and carries its provenance: image, map, configs and anomaly bank by hash; models and rules by name and version. It is designed to attach to an existing Part 11 audit trail, which is also where its checkpoint belongs, and is not Part 11 compliant on its own. Electronic signatures, access control and the review
        workflow belong to the platform; <code>reviewed_by</code> and <code>review_outcome</code> are there for it to fill. Field-by-field mapping: <code>docs/audit_mapping.md</code>.
      </div>
    </>
  );
}
