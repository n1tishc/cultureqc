import { useEffect, useMemo, useRef, useState } from "react";
import { verifyChain } from "../lib/verify";
import { Icon, actionWord, short } from "./ui";

/* The seven stored records, re-hashed in this browser from the exact bytes
   culture/records.py hashed. The switch edits one number in record 3 in
   memory and re-runs the same check. */

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
    if (hit) el.scrollTo({ top: Math.max(0, hit.offsetTop - el.clientHeight / 2), behavior: "smooth" });
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
  const [broken, setBroken] = useState(false);
  const [sel, setSel] = useState(2);
  const [res, setRes] = useState(null);

  const recs = useMemo(
    () => chain.map((e, i) => ({ ...e.record, canonical: broken && i === 2 ? tamper(e.record.canonical) : e.record.canonical })),
    [chain, broken],
  );

  useEffect(() => {
    let live = true;
    setRes(null);
    verifyChain(recs).then((r) => live && setRes(r));
    return () => {
      live = false;
    };
  }, [recs]);

  const obj = JSON.parse(recs[sel].canonical);
  obj.record_hash = recs[sel].record_hash;
  const nOk = res ? res.filter((r) => r.ok).length : null;

  return (
    <>
      <div className="chain" role="group" aria-label="The record chain">
        {chain.map((e, i) => {
          const r = res ? res[i] : null;
          const ok = r ? String(r.ok) : "pending";
          return (
            <button key={e.id} type="button" className="link" data-ok={ok} aria-pressed={i === sel} onClick={() => setSel(i)}>
              <span className="n">#{i + 1}</span>
              <b>{e.label}</b>
              <span className="h">{short(recs[i].record_hash, 8)}</span>
              <span className="h">
                {(() => {
                  const now = JSON.parse(recs[i].canonical).confluency_pct;
                  return now !== e.confluency.pct ? (
                    <b className="changed">
                      {e.confluency.pct.toFixed(1)} → {now.toFixed(1)}%
                    </b>
                  ) : (
                    `${e.confluency.pct.toFixed(1)}%`
                  );
                })()}{" "}
                · {actionWord(e.action).toLowerCase()}
              </span>
              <span className="st" data-ok={ok}>
                <Icon name={r && !r.ok ? "cross" : "check"} />
                {!r ? "checking" : r.ok ? "verified" : !r.hashOk ? "hash mismatch" : "link broken"}
              </span>
            </button>
          );
        })}
      </div>

      <div className="tamper">
        <label className="switch">
          <input type="checkbox" checked={broken} onChange={(e) => (setBroken(e.target.checked), setSel(2))} />
          Change one number in record 3
        </label>
        <span aria-live="polite">
          {!res
            ? "Re-hashing…"
            : broken
              ? `Confluency in record 3 raised by 10 points: ${7 - nOk} of 7 records now fail — record 3’s own hash, and record 4’s link to it. Records 1–2 are untouched.`
              : `All ${nOk} of 7 records re-hash to their stored SHA-256 and link to the one before.`}
        </span>
      </div>

      <div className="rec-grid">
        <Json obj={obj} bad={broken && sel === 2 ? "confluency_pct" : null} />
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
        <b>Where this sits for GMP.</b> The chain is tamper-evident and carries its provenance: image, map, models, configs and rules, each by hash. It is designed to attach to an existing Part 11 audit trail and is not Part 11 compliant on its own. Electronic signatures, access control and the review
        workflow belong to the platform; <code>reviewed_by</code> and <code>review_outcome</code> are there for it to fill. Field-by-field mapping: <code>docs/audit_mapping.md</code>.
      </div>
    </>
  );
}
